"""Statement-PDF passwords from the rule a bank states in its email: inboxkit's, re-exported.

inboxkit also knows the PAN-only rule (brokers, CAS); it applies only when a `pan` hint is passed.
"""
from inboxkit.passwords import candidates, derive, parse_rule  # noqa: F401
