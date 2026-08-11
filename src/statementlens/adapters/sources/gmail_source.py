"""GmailStatementSource — fetch statement-PDF attachments from Gmail (StatementSource port).

Read-only Gmail (scope gmail.readonly). It only READS: it returns RawStatement documents (bytes +
provenance); it never writes anything. Google libraries are imported lazily so the package imports
without them (install the [gmail] extra to use this adapter).

Setup (one-time, by the user): a Google Cloud project with the Gmail API enabled and OAuth *Desktop*
credentials at ~/.statementlens/gmail_client_secret.json. First fetch opens a browser consent and
caches a token at ~/.statementlens/gmail_token.json.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DEFAULT_QUERY = (
    'has:attachment filename:pdf newer_than:5y '
    'subject:(statement OR "e-statement" OR "account statement" OR "credit card" OR bill) '
    'from:(sbi OR hdfcbank OR icicibank OR axisbank OR sbicard OR onecard OR idfcfirstbank '
    'OR kotak OR amex OR citibank OR hsbc OR rblbank OR yesbank OR scapia OR federal)')


@dataclass
class _RawStatement:
    source_id: str
    source_name: str
    data: bytes


def _cfg(name: str, override: Optional[str], env: str) -> Path:
    return Path(override or os.getenv(env) or (Path.home() / ".statementlens" / name))


class GmailStatementSource:
    """Fetches statement PDFs from Gmail. `service` is injectable for testing (no creds needed)."""

    def __init__(self, service=None, query: Optional[str] = None,
                 client_secret_path: Optional[str] = None, token_path: Optional[str] = None):
        self._service = service
        self._query = query or DEFAULT_QUERY
        self._secret = _cfg("gmail_client_secret.json", client_secret_path,
                            "STATEMENTLENS_GMAIL_SECRET")
        self._token = _cfg("gmail_token.json", token_path, "STATEMENTLENS_GMAIL_TOKEN")

    # -- port method -------------------------------------------------------
    def fetch(self, limit: int = 100) -> List["_RawStatement"]:
        svc = self._service or self._authorize()
        resp = svc.users().messages().list(userId="me", q=self._query, maxResults=limit).execute()
        out: List[_RawStatement] = []
        for m in resp.get("messages", []):
            for att in self._pdf_attachments(svc, m["id"]):
                data = self._download(svc, m["id"], att["attachment_id"])
                out.append(_RawStatement(m["id"], att["filename"], data))
        return out

    # -- helpers -----------------------------------------------------------
    def _pdf_attachments(self, svc, msg_id: str) -> List[dict]:
        full = svc.users().messages().get(userId="me", id=msg_id, format="full").execute()
        found: List[dict] = []

        def walk(part):
            body = part.get("body", {}) or {}
            fn = part.get("filename", "")
            if fn.lower().endswith(".pdf") and body.get("attachmentId"):
                found.append({"filename": fn, "attachment_id": body["attachmentId"]})
            for c in part.get("parts", []) or []:
                walk(c)

        walk(full.get("payload", {}) or {})
        return found

    def _download(self, svc, msg_id: str, attachment_id: str) -> bytes:
        att = svc.users().messages().attachments().get(
            userId="me", messageId=msg_id, id=attachment_id).execute()
        return base64.urlsafe_b64decode(att["data"].encode("utf-8"))

    def _client_config(self) -> Optional[dict]:
        """OAuth client config: the user's own file if present, else the app's bundled client.

        Shipping the client id/secret is the normal pattern for *installed* apps — the "secret"
        cannot be kept confidential in a distributed binary, which is why the loopback flow does not
        rely on it for security. Bundling it is what makes onboarding one click instead of "go create
        a Google Cloud project".
        """
        import json
        if self._secret.exists():
            return json.loads(self._secret.read_text(encoding="utf-8"))
        from .bundled_client import bundled_client_config
        return bundled_client_config()

    def _authorize(self):
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Gmail libraries missing — pip install 'statementlens[gmail]'") from e
        creds = None
        if self._token.exists():
            creds = Credentials.from_authorized_user_file(str(self._token), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                config = self._client_config()
                if config is None:
                    raise RuntimeError(
                        "Gmail isn't set up in this build. Either ship a bundled OAuth client "
                        f"(see bundled_client.py) or save Desktop OAuth credentials at {self._secret}. "
                        "You can import statements from a folder instead — no Google setup needed.")
                creds = InstalledAppFlow.from_client_config(
                    config, SCOPES).run_local_server(
                        port=0, open_browser=True,
                        authorization_prompt_message="",
                        success_message="Connected. You can close this tab and return to StatementLens.")
            self._token.parent.mkdir(parents=True, exist_ok=True)
            self._token.write_text(creds.to_json(), encoding="utf-8")
        return build("gmail", "v1", credentials=creds, cache_discovery=False)
