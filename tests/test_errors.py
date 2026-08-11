"""TDD: validation helpers produce fail-fast, actionable errors."""
import pytest

from trans_processor.validate import dollars_to_cents, clean_text
from trans_processor.errors import InputError


# ---- amount -> cents ---------------------------------------------------------

@pytest.mark.parametrize("raw,cents", [
    ("20", 2000),
    ("20.00", 2000),
    ("35.5", 3550),
    (25, 2500),
    (30.0, 3000),
    (" 40 ", 4000),
])
def test_amount_cases(raw, cents):
    assert dollars_to_cents(raw, location="Row 4") == cents


def test_amount_non_numeric_raises_with_guidance():
    with pytest.raises(InputError) as e:
        dollars_to_cents("twenty", location="Row 6 (KELROS045)")
    msg = str(e.value)
    assert "Row 6 (KELROS045)" in msg
    assert "twenty" in msg
    assert "positive" in msg.lower()


def test_amount_zero_raises():
    with pytest.raises(InputError) as e:
        dollars_to_cents("0", location="Row 5")
    assert "greater than 0" in str(e.value)


def test_amount_negative_raises():
    with pytest.raises(InputError) as e:
        dollars_to_cents("-5", location="Row 5")
    assert "greater than 0" in str(e.value)


def test_amount_too_many_decimals_raises():
    with pytest.raises(InputError) as e:
        dollars_to_cents("20.001", location="Row 4")
    assert "20.001" in str(e.value)


def test_amount_no_float_rounding_error():
    # 0.1 + 0.2 style: 70.10 must be exactly 7010 cents.
    assert dollars_to_cents("70.10", location="Row 4") == 7010
    assert dollars_to_cents(70.10, location="Row 4") == 7010


# ---- text fields -------------------------------------------------------------

def test_clean_text_passthrough():
    value, warns = clean_text("Extraordinary Pay", max_len=20, field="Payee name",
                              location="Row 3")
    assert value == "Extraordinary Pay"
    assert warns == []


def test_clean_text_comma_raises():
    with pytest.raises(InputError) as e:
        clean_text("E5,HAT", max_len=12, field="Particulars", location="Row 4")
    msg = str(e.value)
    assert "comma" in msg.lower()
    assert "Row 4" in msg


def test_clean_text_quote_raises():
    with pytest.raises(InputError) as e:
        clean_text('AB"CD', max_len=12, field="Particulars", location="Row 4")
    assert "quote" in str(e.value).lower()


def test_clean_text_truncates_with_warning():
    value, warns = clean_text("Extraordinary Pay Limited", max_len=20,
                              field="Payee name", location="Row 3")
    assert value == "Extraordinary Pay Li"   # 20 chars
    assert len(warns) == 1
    assert "truncated to 20" in warns[0]
    assert "Row 3" in warns[0]


def test_clean_text_none_becomes_blank():
    value, warns = clean_text(None, max_len=12, field="Reference", location="Row 3")
    assert value == ""
    assert warns == []
