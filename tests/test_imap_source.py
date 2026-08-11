"""Checks for the IMAP source, using a fake IMAP connection — no network, no real mailbox.

The properties that matter: the mailbox is opened READ-ONLY (an app password grants full access, so
the adapter must never be able to modify anything), bank mail is distinguished from noise, and login
failures produce a message that names the actual fix.
"""

from email.message import EmailMessage

from statementlens.adapters.sources.imap_source import (
    ImapCredentials, ImapStatementSource, KNOWN_HOSTS,
)


def _msg(subject: str, sender: str, attachments=(("statement.pdf", b"%PDF-1.4 x"),)) -> bytes:
    m = EmailMessage()
    m["Subject"] = subject
    m["From"] = sender
    m.set_content("Your statement is attached.")
    for name, payload in attachments:
        m.add_attachment(payload, maintype="application", subtype="pdf", filename=name)
    return m.as_bytes()


class FakeImap:
    """Minimal imaplib stand-in that records how it was used."""

    def __init__(self, messages):
        self._messages = messages          # {uid: raw_bytes}
        self.selected_readonly = None
        self.write_calls = []

    def select(self, mailbox, readonly=False):
        self.selected_readonly = readonly
        return "OK", [b"1"]

    def search(self, charset, query):
        return "OK", [b" ".join(str(u).encode() for u in sorted(self._messages))]

    def fetch(self, uid, spec):
        raw = self._messages.get(int(uid))
        return ("OK", [(b"1 (RFC822 {%d}" % len(raw), raw)]) if raw else ("NO", [])

    # any of these being called is a bug — we must never mutate the user's mailbox
    def store(self, *a, **k):
        self.write_calls.append(("store", a))
        raise AssertionError("adapter must not write to the mailbox")

    def expunge(self):
        self.write_calls.append(("expunge", ()))
        raise AssertionError("adapter must not expunge")

    def close(self):
        pass

    def logout(self):
        pass


def test_fetches_pdf_attachments_from_bank_mail():
    fake = FakeImap({1: _msg("Your HDFC Bank account statement", "alerts@hdfcbank.net")})
    got = ImapStatementSource(connection=fake).fetch()
    assert len(got) == 1
    assert got[0].source_name == "statement.pdf"
    assert got[0].data.startswith(b"%PDF")


def test_mailbox_is_opened_read_only():
    """An app password grants full mailbox access, so the server must enforce read-only."""
    fake = FakeImap({1: _msg("SBI statement", "no-reply@sbi.co.in")})
    ImapStatementSource(connection=fake).fetch()
    assert fake.selected_readonly is True
    assert fake.write_calls == []


def test_non_bank_mail_with_a_pdf_is_ignored():
    fake = FakeImap({1: _msg("Party invitation", "friend@example.com",
                             (("invite.pdf", b"%PDF-1.4 y"),))})
    assert ImapStatementSource(connection=fake).fetch() == []


def test_messages_without_pdfs_are_skipped():
    fake = FakeImap({1: _msg("HDFC Bank statement", "alerts@hdfcbank.net", ())})
    assert ImapStatementSource(connection=fake).fetch() == []


def test_limit_is_respected():
    msgs = {i: _msg(f"ICICI Bank statement {i}", "statements@icicibank.com") for i in range(1, 6)}
    assert len(ImapStatementSource(connection=FakeImap(msgs)).fetch(limit=2)) == 2


def test_newest_messages_come_first():
    msgs = {i: _msg(f"Axis Bank statement {i}", "estatement@axisbank.com") for i in (1, 2, 3)}
    got = ImapStatementSource(connection=FakeImap(msgs)).fetch(limit=1)
    assert got[0].source_id == "3"          # highest UID = newest


def test_check_reports_a_connected_status():
    fake = FakeImap({1: _msg("Kotak statement", "estatement@kotak.com")})
    assert "connected" in ImapStatementSource(connection=fake).check()


def test_host_is_guessed_from_the_address():
    assert ImapCredentials.guess_host("someone@gmail.com") == KNOWN_HOSTS["gmail.com"]
    assert ImapCredentials.guess_host("a@outlook.com") == KNOWN_HOSTS["outlook.com"]
    # unknown domains get a conventional guess rather than an error
    assert ImapCredentials.guess_host("a@mycompany.co") == "imap.mycompany.co"


def test_app_password_spaces_are_stripped():
    # Google displays app passwords in four-character groups; users paste them verbatim
    c = ImapCredentials("a@gmail.com", "abcd efgh ijkl mnop")
    assert c.app_password == "abcdefghijklmnop"


def test_address_must_be_an_email():
    try:
        ImapCredentials("not-an-address", "x")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_login_errors_name_the_actual_fix():
    from statementlens.adapters.sources.imap_source import _friendly_login_error
    assert "APP PASSWORD" in _friendly_login_error(
        "[AUTHENTICATIONFAILED] Application-specific password required")
    assert "IMAP is turned off" in _friendly_login_error("IMAP access is disabled for this user")


def test_credentials_or_connection_is_required():
    try:
        ImapStatementSource()
    except ValueError:
        return
    raise AssertionError("expected ValueError")
