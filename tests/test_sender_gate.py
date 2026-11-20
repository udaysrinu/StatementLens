"""Statements are read only from senders Gmail's own server vouches for. Synthetic mail, no network.

A lookalike sender ("statements@sbi-statements.co") matches the bank-name query, so without the gate its
PDF would be parsed and its made-up transactions counted. The verdicts below mirror real headers: the
genuine one is the shape SBI's older address actually produces (DMARC passes on the parent domain).
"""
import base64
import tempfile
from pathlib import Path

from statementlens.adapters.sources.gmail_source import GmailStatementSource, trusted_org
from statementlens.usecases.ingest import IngestResult, IngestStatements
from statementlens.usecases.refresh import RefreshStatements, SyncLog

GENUINE = ("SBI <cbssbi.cas@alerts.sbi.co.in>",
           "mx.google.com; dkim=pass header.i=@alerts.sbi.co.in header.s=nc header.b=abc; spf=pass "
           "(google.com: domain of x@alerts.sbi.co.in designates 192.0.2.1 as permitted sender) "
           "smtp.mailfrom=x@alerts.sbi.co.in; dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=sbi.co.in")
LOOKALIKE = ("SBI <statements@sbi-statements.co>",
             "mx.google.com; dkim=pass header.i=@sbi-statements.co header.s=s1 header.b=abc; "
             "dmarc=pass (p=NONE) header.from=sbi-statements.co")
SPOOFED = ("SBI <alerts@sbi.co.in>",
           "mx.google.com; dkim=none; spf=fail smtp.mailfrom=x@evil.example; dmarc=fail (p=REJECT) header.from=sbi.co.in")


class _Exec:
    def __init__(self, body): self._b = body
    def execute(self, **_): return self._b


class _Gmail:
    """Just enough of the Gmail API for inboxkit's fetch: one PDF per message."""
    def __init__(self, mails): self._m = mails          # {id: (From, Authentication-Results)}
    def users(self): return self
    def messages(self): return self
    def attachments(self): return self

    def list(self, userId, q, maxResults, pageToken=None):
        return _Exec({"messages": [{"id": i} for i in self._m]})

    def get(self, userId, id=None, format=None, messageId=None):
        if messageId is not None:                       # attachments().get
            return _Exec({"data": base64.urlsafe_b64encode(b"%PDF-1.4 demo").decode()})
        frm, auth = self._m[id]
        return _Exec({"labelIds": ["INBOX"], "payload": {
            "headers": [{"name": "Authentication-Results", "value": auth}, {"name": "From", "value": frm},
                        {"name": "Date", "value": "Mon, 2 Nov 2026 10:00:00 +0530"},
                        {"name": "Subject", "value": "Your e-statement"}],
            "parts": [{"filename": f"{id}.pdf", "body": {"attachmentId": "a1"}}]}})


def test_only_a_proven_sender_is_read_and_the_rest_are_listed_with_why():
    src = GmailStatementSource(service=_Gmail({"genuine": GENUINE, "lookalike": LOOKALIKE, "spoofed": SPOOFED}))
    got = src.fetch()
    assert [d.filename for d in got] == ["genuine.pdf"]
    why = {r["source"]: r["message"] for r in src.refused}
    assert "not on the trusted list" in why["lookalike.pdf"] and "sbi-statements.co" in why["lookalike.pdf"]
    assert "failed the check that it really came from sbi.co.in" in why["spoofed.pdf"]


def test_the_trusted_list_matches_on_a_dot_boundary_only():
    assert trusted_org("x <a@alerts.sbi.co.in>") == "sbi.co.in"
    assert trusted_org("a@sbi.co.in.evil.com") is None          # the suffix trick
    assert trusted_org("a@evilsbi.co.in") is None               # no dot boundary
    assert trusted_org("") is None


def test_a_refused_statement_reaches_the_sync_record_the_page_shows():
    class Src:
        refused = [{"source": "x.pdf", "problem": "untrusted_sender", "message": "x.pdf: not read", "detail": ""}]
        def fetch(self, limit=100): return []

    ing = IngestStatements(source=Src(), decryptor=None, extractor=None, parser_registry=None,
                           categorizer=None, repository=None)
    r = ing.run(account="x", hints={})
    assert isinstance(r, IngestResult) and r.skipped[-1]["problem"] == "untrusted_sender"
    with tempfile.TemporaryDirectory() as tmp:
        log = SyncLog(str(Path(tmp) / "sync.json"))
        RefreshStatements(lambda: r, log=log).run(force=True)
        assert log.status()["refused"] == ["x.pdf: not read"]
