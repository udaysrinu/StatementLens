"""Loans, deposits and pensions are POSITIONS, not transactions: inboxkit's parser, re-exported.

Shared with Netfolio so both read the same documents with the same self-checking code. Ingest still
uses it here to SKIP such documents: booked as transactions they would count every EMI twice.
"""
from inboxkit.positions import (PositionParseError, is_bob_loan, is_fd_advice,  # noqa: F401
                                is_nps_statement, parse_bob_loan, parse_fd_advice,
                                parse_nps_statement, parse_position)
