"""Refresh — keep the ledger current without the user doing anything.

Two things matter more than the scheduling mechanics:

1. **A failed refresh must be visible.** If Gmail auth silently expires, "no new transactions" and
   "we haven't been able to look for three weeks" render identically — and the user keeps trusting a
   stale dashboard. Every attempt is recorded with its outcome, and the UI shows the last successful
   sync time, the way CRED shows "updated 36 mins ago".
2. **Refresh must be safe to run repeatedly.** Content-hash dedup already guarantees that, so the
   only real risk is hammering a provider. A minimum interval handles it.

Scheduling is left to the platform (app launch, or `launchd`/Task Scheduler) rather than a resident
daemon — a background process that must be installed, updated and debugged is a poor trade for a
local app that gets opened anyway.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Don't re-hit a provider more often than this, however often refresh() is called.
DEFAULT_MIN_INTERVAL = timedelta(minutes=30)


@dataclass
class SyncAttempt:
    """One refresh attempt. `ok` False with a reason is the whole point of this record."""
    started_at: str
    ok: bool
    inserted: int = 0
    duplicate: int = 0
    statements: int = 0
    failed: int = 0
    reason: str = ""            # why it failed, in plain language
    duration_ms: int = 0
    skipped_reasons: List[str] = field(default_factory=list)


class SyncLog:
    """Append-only JSON record of refresh attempts, next to the database.

    Deliberately a file and not a table: it must be writable even when the DB is the thing that
    broke, and it is the first thing to read when a user says "my dashboard looks old".
    """

    def __init__(self, path: Optional[str] = None, keep: int = 50):
        self.path = Path(path or (Path.home() / ".statementlens" / "sync_log.json"))
        self._keep = keep

    def _read(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []

    def append(self, attempt: SyncAttempt) -> None:
        entries = self._read()
        entries.append(asdict(attempt))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(entries[-self._keep:], indent=1), encoding="utf-8")

    def last(self) -> Optional[Dict[str, Any]]:
        entries = self._read()
        return entries[-1] if entries else None

    def last_success(self) -> Optional[Dict[str, Any]]:
        for e in reversed(self._read()):
            if e.get("ok"):
                return e
        return None

    def status(self, *, now: Optional[datetime] = None) -> Dict[str, Any]:
        """What the UI needs to show freshness honestly."""
        now = now or datetime.now(timezone.utc)
        last, ok = self.last(), self.last_success()
        out: Dict[str, Any] = {
            "last_attempt": last.get("started_at") if last else None,
            "last_success": ok.get("started_at") if ok else None,
            "healthy": bool(last and last.get("ok")),
            "reason": (last or {}).get("reason", ""),
            # the per-file explanations, so the UI can answer "which files?" instead of showing a
            # bare count the user cannot act on
            "skipped_reasons": (last or {}).get("skipped_reasons", []),
        }
        if ok:
            age = now - _parse(ok["started_at"])
            out["age_minutes"] = int(age.total_seconds() // 60)
            # the label always describes the last SUCCESS, never a failed attempt — otherwise a
            # broken connector reads as "updated just now"
            out["label"] = _humanize(age)
            # a refresh that has not succeeded in over a week is stale enough to warn about
            out["stale"] = age > timedelta(days=8) or not out["healthy"]
        else:
            out["label"] = "never synced"
            out["stale"] = True
        return out


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _humanize(age: timedelta) -> str:
    mins = int(age.total_seconds() // 60)
    if mins < 1:
        return "updated just now"
    if mins < 60:
        return f"updated {mins} min{'s' if mins != 1 else ''} ago"
    hours = mins // 60
    if hours < 24:
        return f"updated {hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    return f"updated {days} day{'s' if days != 1 else ''} ago"


class RefreshStatements:
    """Runs an ingest and records the outcome. `ingest` is any callable returning an IngestResult."""

    def __init__(self, ingest, log: Optional[SyncLog] = None,
                 min_interval: timedelta = DEFAULT_MIN_INTERVAL):
        self._ingest = ingest
        self._log = log or SyncLog()
        self._min_interval = min_interval

    def run(self, *, force: bool = False, now: Optional[datetime] = None) -> SyncAttempt:
        now = now or datetime.now(timezone.utc)
        last = self._log.last()
        if not force and last:
            since = now - _parse(last["started_at"])
            if since < self._min_interval:
                return SyncAttempt(started_at=now.isoformat(), ok=bool(last.get("ok")),
                                   reason=f"skipped: last attempt {int(since.total_seconds())}s ago")

        t0 = time.monotonic()
        try:
            r = self._ingest()
        except Exception as e:
            # never let a provider error look like "nothing new"
            attempt = SyncAttempt(started_at=now.isoformat(), ok=False,
                                  reason=_friendly(e),
                                  duration_ms=int((time.monotonic() - t0) * 1000))
            self._log.append(attempt)
            return attempt

        # A run that read SOMETHING is a successful run. Requiring zero failures made a sync that
        # imported 2,991 transactions report "never synced", because five of the PDFs in the mailbox
        # were an application form, a KFS and two MITC documents — regulatory paperwork banks send
        # with a card, which contains no transactions by design and never will. Unreadable files are
        # worth reporting, but they are not a failed sync, and a permanent "never synced" on a
        # working setup teaches the user to ignore the one banner that matters.
        read_something = r.statements > 0 or r.inserted > 0 or r.duplicate > 0
        ok = read_something or r.failed == 0
        if r.failed and read_something:
            reason = f"imported fine · {r.failed} file(s) weren't statements"
        elif r.failed:
            reason = f"{r.failed} statement(s) could not be read"
        else:
            reason = ""
        attempt = SyncAttempt(
            started_at=now.isoformat(),
            ok=ok,
            inserted=r.inserted, duplicate=r.duplicate, statements=r.statements, failed=r.failed,
            reason=reason,
            duration_ms=int((time.monotonic() - t0) * 1000),
            skipped_reasons=[s.get("message", "") for s in getattr(r, "skipped", [])][:5])
        self._log.append(attempt)
        return attempt


def _friendly(e: Exception) -> str:
    """Turn an exception into something a non-developer can act on.

    Order matters: "not configured" must be checked BEFORE the expired-permission patterns, because
    the not-configured message also contains words like "credentials" and telling someone to
    reconnect an account they never connected sends them in circles.
    """
    msg = str(e)
    low = msg.lower()
    if ("isn't set up" in low or "not set up" in low or "client secret" in low
            or "isn't configured" in low or "not configured" in low):
        return "Gmail isn't set up in this build. Import PDFs from a folder instead."
    if "invalid_grant" in low or "expired" in low or "revoked" in low or "refresh token" in low:
        return "Gmail needs reconnecting — its permission expired. Open setup and connect again."
    if ("network" in low or "resolve" in low or "connection" in low or "timed out" in low
            or "unreachable" in low):
        return "Could not reach the internet. We'll try again next time."
    if "credentials" in low or "token" in low:
        return "Gmail sign-in failed. Open setup and connect again."
    return f"{type(e).__name__}: {msg}"
