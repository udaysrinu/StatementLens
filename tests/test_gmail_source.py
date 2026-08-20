"""Checks for the Gmail source's paging. No network — a fake `service` stands in for the API.

The bug these exist for: Gmail's messages.list() returns at most `maxResults` messages, NEWEST FIRST,
and silently drops the rest. There is no error and no flag — a truncated history is indistinguishable
from a short one. On a real mailbox the query matched 111 messages against a limit of 100, so the
oldest 11 were never fetched and the account looked like it began in May 2023 when statements existed
back to Sep 2022. Backfilling recovered 8 months and 555 transactions.
"""

from statementlens.adapters.sources.gmail_source import GmailStatementSource


class _FakeMessages:
    """Pages a fixed id list the way Gmail does, honouring maxResults and pageToken."""

    def __init__(self, ids):
        self._ids = ids
        self.pages_served = 0

    def list(self, userId, q, maxResults, pageToken=None):
        start = int(pageToken or 0)
        end = min(len(self._ids), start + maxResults)
        body = {"messages": [{"id": i} for i in self._ids[start:end]]}
        if end < len(self._ids):
            body["nextPageToken"] = str(end)
        self.pages_served += 1
        return _Exec(body)

    def get(self, userId, id, format):          # no attachments: fetch() just collects ids
        return _Exec({"payload": {}})

    def attachments(self):
        return self


class _Exec:
    def __init__(self, body):
        self._body = body

    def execute(self):
        return self._body


class _FakeUsers:
    def __init__(self, msgs):
        self._msgs = msgs

    def messages(self):
        return self._msgs


class _FakeService:
    def __init__(self, ids):
        self.msgs = _FakeMessages(ids)

    def users(self):
        return _FakeUsers(self.msgs)


def _source(ids):
    return GmailStatementSource(service=_FakeService(ids))


def test_the_default_limit_covers_a_real_mailbox():
    """The regression, stated as the number that caused it.

    The old default was 100 and one real mailbox matched 111 statement emails, so the oldest 11 were
    dropped. The default must comfortably exceed years of monthly statements across several banks.
    """
    from statementlens.adapters.sources.gmail_source import DEFAULT_LIMIT
    assert DEFAULT_LIMIT >= 500, f"default limit {DEFAULT_LIMIT} can truncate a multi-year mailbox"

    svc = _FakeService([f"m{i}" for i in range(111)])
    src = GmailStatementSource(service=svc)
    src.fetch()                                    # no explicit limit: the default must reach all 111
    assert not src.truncated, "111 messages must not be truncated by the default"


def test_paging_follows_next_page_token():
    """A mailbox larger than one page must produce more than one request.

    _MAX_PAGE is Gmail's ceiling, so anything above it has to be paged rather than asked for at once.
    """
    from statementlens.adapters.sources.gmail_source import _MAX_PAGE
    svc = _FakeService([f"m{i}" for i in range(_MAX_PAGE + 40)])
    src = GmailStatementSource(service=svc)
    src.fetch(limit=_MAX_PAGE + 200)
    assert svc.msgs.pages_served >= 2, "fetch() never asked for a second page"
    assert not src.truncated


def test_hitting_the_cap_is_reported_not_silent():
    """The actual defect was SILENCE: a truncated history looks exactly like a short one.

    When the cap is reached and more messages remain, `truncated` must be set so the caller can say so
    instead of quietly returning a shorter ledger.
    """
    svc = _FakeService([f"m{i}" for i in range(300)])
    src = GmailStatementSource(service=svc)
    src.fetch(limit=100)
    assert src.truncated, "stopped early with more messages available and said nothing"


def test_a_short_mailbox_stops_without_a_second_call():
    # no nextPageToken -> no extra round trip, and nothing to warn about
    svc = _FakeService([f"m{i}" for i in range(7)])
    src = GmailStatementSource(service=svc)
    src.fetch(limit=100)
    assert svc.msgs.pages_served == 1 and not src.truncated


def test_an_empty_mailbox_is_not_an_error():
    svc = _FakeService([])
    src = GmailStatementSource(service=svc)
    assert src.fetch(limit=100) == [] and not src.truncated
