"""TDD: account parsing and Excel-date conversion helpers."""
import pytest

from trans_processor.accounts import parse_account, excel_serial_to_ddmmyy
from trans_processor.errors import InputError


def test_parse_full_account_with_suffix():
    acct = parse_account("98-7654-1234567-001")
    assert acct.bank == "98"
    assert acct.branch == "7654"
    assert acct.account == "01234567"   # padded to 8
    assert acct.suffix == "0001"        # padded to 4


def test_parse_account_without_suffix_defaults_to_zero():
    acct = parse_account("12-3456-7654321")
    assert acct.bank == "12"
    assert acct.branch == "3456"
    assert acct.account == "07654321"
    assert acct.suffix == "0000"


def test_parse_account_two_digit_suffix_left_padded():
    # NZ suffixes are often 2 digits; pad to 4.
    acct = parse_account("98-7654-1234567-25")
    assert acct.suffix == "0025"


def test_parse_account_strips_whitespace():
    acct = parse_account("  98-7654-1234567-001  ")
    assert acct.account == "01234567"


def test_parse_account_wrong_part_count_raises():
    with pytest.raises(InputError) as e:
        parse_account("98-7654")
    msg = str(e.value)
    assert "98-7654" in msg
    assert "Bank-Branch-Account" in msg


def test_parse_account_non_numeric_raises():
    with pytest.raises(InputError) as e:
        parse_account("98-7654-ABC4567-001")
    assert "ABC4567" in str(e.value)


def test_parse_account_overlong_account_raises():
    with pytest.raises(InputError) as e:
        parse_account("98-7654-012345678-001")   # 9-digit account
    assert "exceeds 8" in str(e.value)


def test_excel_serial_to_ddmmyy():
    # 46262 -> 28 Aug 2026 in the 1900 date system (epoch 1899-12-30).
    assert excel_serial_to_ddmmyy(46262) == "280826"


def test_excel_serial_accepts_numeric_string():
    assert excel_serial_to_ddmmyy("46262") == "280826"


def test_excel_serial_invalid_raises():
    with pytest.raises(InputError) as e:
        excel_serial_to_ddmmyy("not-a-date")
    assert "not-a-date" in str(e.value)
