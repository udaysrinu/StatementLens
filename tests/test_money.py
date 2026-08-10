"""Money value object — exactness and formatting."""
from decimal import Decimal

from statementlens.domain.money import Money


def test_of_is_exact_no_float_drift():
    # 0.1 + 0.2 must equal 0.3 exactly in paise
    assert (Money.of("0.1") + Money.of("0.2")) == Money.of("0.3")
    assert Money.of("0.1").minor == 10


def test_arithmetic_and_sign():
    a, b = Money.of(100), Money.of(30)
    assert (a - b).minor == 7000
    assert (-b).minor == -3000
    assert Money.of(0).is_zero and Money.of(-1).is_negative


def test_currency_mismatch_raises():
    try:
        Money(100, "INR") + Money(100, "USD")
    except ValueError as e:
        assert "currency" in str(e)
    else:
        raise AssertionError("expected currency mismatch")


def test_indian_lakh_grouping():
    assert Money.of(123456.78).format() == "₹1,23,456.78"
    assert Money.of(-4500).format() == "-₹4,500.00"
    assert Money.of(50).format() == "₹50.00"


def test_major_is_decimal():
    assert Money(13394 * 100).major == Decimal("13394.00")
