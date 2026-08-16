"""Checks for refresh + the sync log. The point of this code is that failures are VISIBLE."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from statementlens.usecases.ingest import IngestResult
from statementlens.usecases.refresh import RefreshStatements, SyncLog

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


def _log(tmp) -> SyncLog:
    return SyncLog(str(Path(tmp) / "sync.json"))


def test_successful_refresh_is_recorded_with_counts():
    with tempfile.TemporaryDirectory() as tmp:
        log = _log(tmp)
        r = RefreshStatements(lambda: IngestResult(statements=1, inserted=5), log)
        a = r.run(now=NOW)
        assert a.ok and a.inserted == 5
        assert log.last_success()["inserted"] == 5


def test_provider_exception_is_recorded_as_a_failure_not_silence():
    # the whole reason this module exists: a broken connector must not look like "nothing new"
    with tempfile.TemporaryDirectory() as tmp:
        log = _log(tmp)

        def boom():
            raise RuntimeError("invalid_grant: token expired")

        a = RefreshStatements(boom, log).run(now=NOW)
        assert not a.ok
        assert "reconnect" in a.reason.lower()
        assert log.status(now=NOW)["healthy"] is False


def test_network_errors_get_a_calm_message():
    with tempfile.TemporaryDirectory() as tmp:
        def boom():
            raise OSError("Could not resolve host")
        a = RefreshStatements(boom, _log(tmp)).run(now=NOW)
        assert "internet" in a.reason.lower()


def test_empty_but_working_run_is_healthy():
    # no new statements this month is NOT a failure
    with tempfile.TemporaryDirectory() as tmp:
        log = _log(tmp)
        a = RefreshStatements(lambda: IngestResult(), log).run(now=NOW)
        assert a.ok and a.inserted == 0
        assert log.status(now=NOW)["healthy"] is True


def test_a_run_that_imported_data_is_healthy_even_with_unreadable_files():
    """A real sync read 2,991 transactions and still reported "never synced".

    Five of the PDFs in the mailbox were an application form, a KFS and two MITC documents — the
    regulatory paperwork a bank sends with a card. They hold no transactions by design, so
    `failed > 0` was permanent, `ok` was permanently False, `last_success` stayed null forever, and
    the banner read "never synced" on a working setup. A stale warning that is always on is a stale
    warning nobody reads.
    """
    with tempfile.TemporaryDirectory() as tmp:
        log = _log(tmp)
        res = IngestResult(statements=1, inserted=2, failed=5)
        a = RefreshStatements(lambda: res, log).run(now=NOW)
        assert a.ok, "importing data is a success even when other files were not statements"
        assert log.last_success() is not None
        assert log.status(now=NOW)["label"] != "never synced"
        assert not log.status(now=NOW)["stale"]
        # A successful run says NOTHING about skipped files. On a real mailbox 61 of them are MITC/KFS
        # regulatory paperwork with no transactions by design, so they are skipped on every sync
        # forever; announcing a permanent condition every time turns the status line into wallpaper,
        # and this is the same line that must be believed when it reports staleness.
        assert a.reason == "", f"a healthy sync must not editorialise, got {a.reason!r}"
        # but the count and the per-file explanations are still RECORDED, just not announced
        assert a.failed == 5


def test_a_run_that_read_nothing_at_all_is_still_a_failure():
    """The other side of the same coin: if NOTHING landed, failures must stay loud."""
    with tempfile.TemporaryDirectory() as tmp:
        log = _log(tmp)
        a = RefreshStatements(lambda: IngestResult(failed=3), log).run(now=NOW)
        assert not a.ok and "could not be read" in a.reason
        assert log.status(now=NOW)["stale"]


def test_status_carries_the_per_file_skip_reasons():
    # a bare count invites "which files, and is my data missing?" — the UI needs the explanations
    with tempfile.TemporaryDirectory() as tmp:
        log = _log(tmp)
        res = IngestResult(statements=1, inserted=1, failed=1,
                           skipped=[{"message": "RetailMITC.pdf has no transactions"}])
        RefreshStatements(lambda: res, log).run(now=NOW)
        assert log.status(now=NOW)["skipped_reasons"] == ["RetailMITC.pdf has no transactions"]


def test_min_interval_prevents_hammering_the_provider():
    with tempfile.TemporaryDirectory() as tmp:
        log = _log(tmp)
        calls = []

        def ingest():
            calls.append(1)
            return IngestResult(inserted=1)

        r = RefreshStatements(ingest, log, min_interval=timedelta(minutes=30))
        r.run(now=NOW)
        r.run(now=NOW + timedelta(minutes=5))            # too soon -> skipped
        assert len(calls) == 1
        r.run(now=NOW + timedelta(minutes=31))           # past the interval -> runs
        assert len(calls) == 2


def test_force_overrides_the_interval():
    with tempfile.TemporaryDirectory() as tmp:
        calls = []
        r = RefreshStatements(lambda: (calls.append(1), IngestResult(inserted=1))[1], _log(tmp))
        r.run(now=NOW)
        r.run(now=NOW + timedelta(seconds=5), force=True)
        assert len(calls) == 2


def test_status_reports_freshness_in_plain_language():
    with tempfile.TemporaryDirectory() as tmp:
        log = _log(tmp)
        RefreshStatements(lambda: IngestResult(inserted=1), log).run(now=NOW)
        s = log.status(now=NOW + timedelta(minutes=36))
        assert s["label"] == "updated 36 mins ago"
        assert s["age_minutes"] == 36 and not s["stale"]


def test_never_synced_is_reported_as_stale():
    with tempfile.TemporaryDirectory() as tmp:
        s = _log(tmp).status(now=NOW)
        assert s["label"] == "never synced" and s["stale"] is True


def test_long_gap_is_flagged_stale():
    with tempfile.TemporaryDirectory() as tmp:
        log = _log(tmp)
        RefreshStatements(lambda: IngestResult(inserted=1), log).run(now=NOW)
        s = log.status(now=NOW + timedelta(days=10))
        assert s["stale"] is True and "10 days ago" in s["label"]


def test_failed_attempt_does_not_claim_a_recent_success():
    # regression: status() reported "updated just now" off the failed ATTEMPT's timestamp
    with tempfile.TemporaryDirectory() as tmp:
        log = _log(tmp)

        def boom():
            raise RuntimeError("invalid_grant")

        RefreshStatements(boom, log).run(now=NOW)
        s = log.status(now=NOW)
        assert s["label"] == "never synced"
        assert s["healthy"] is False and s["stale"] is True


def test_unhealthy_is_always_stale_even_if_a_success_was_recent():
    with tempfile.TemporaryDirectory() as tmp:
        log = _log(tmp)
        r = RefreshStatements(lambda: IngestResult(inserted=1), log, min_interval=timedelta(0))
        r.run(now=NOW)                                   # success
        RefreshStatements(lambda: (_ for _ in ()).throw(RuntimeError("invalid_grant")),
                          log, min_interval=timedelta(0)).run(now=NOW + timedelta(minutes=1))
        s = log.status(now=NOW + timedelta(minutes=1))
        assert s["healthy"] is False and s["stale"] is True


def test_not_configured_message_beats_the_expired_permission_message():
    # telling someone to reconnect an account they never connected sends them in circles
    with tempfile.TemporaryDirectory() as tmp:
        def boom():
            raise RuntimeError("Gmail isn't set up in this build. Save Desktop OAuth credentials…")
        a = RefreshStatements(boom, _log(tmp)).run(now=NOW)
        assert "isn't set up" in a.reason
        assert "reconnect" not in a.reason.lower()


def test_each_database_gets_its_own_sync_log():
    # regression: with_name() gave every db in a folder the SAME log file
    from statementlens.app import App
    with tempfile.TemporaryDirectory() as tmp:
        a = App(db_path=str(Path(tmp) / "a.db"))
        b = App(db_path=str(Path(tmp) / "b.db"))
        assert a.sync_log.path != b.sync_log.path


def test_log_is_trimmed_and_survives_a_corrupt_file():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "sync.json"
        p.write_text("{ not json", encoding="utf-8")
        log = SyncLog(str(p), keep=3)
        assert log.last() is None                        # corrupt file must not crash the app
        r = RefreshStatements(lambda: IngestResult(inserted=1), log,
                              min_interval=timedelta(0))
        for i in range(5):
            r.run(now=NOW + timedelta(hours=i))
        import json
        assert len(json.loads(p.read_text())) == 3
