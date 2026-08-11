"""TDD: read the deduction-list xlsx into PaymentMeta + records."""
from pathlib import Path

import pytest

from trans_processor.reader import read_workbook, parse_grid
from trans_processor.errors import InputError

SAMPLE = Path(__file__).parent / "fixtures" / "sample.xlsx"
NUMERIC_REF = Path(__file__).parent / "fixtures" / "numeric_ref.xlsx"


# ---- happy path against the real workbook -----------------------------------

def test_reads_payment_meta():
    meta, _ = read_workbook(SAMPLE)
    assert meta.payment_date == "46262"
    assert meta.from_account == "12-3456-7654321"


def test_reads_five_records():
    _, records = read_workbook(SAMPLE)
    assert len(records) == 5


def test_first_and_last_record_fields():
    _, records = read_workbook(SAMPLE)
    first = records[0]
    assert first.row == 4
    assert first.beneficiary == "Extraordinary Pay Ltd"
    assert first.bank_details == "98-7654-1234567-001"
    assert first.code == "LORBAR015"
    assert first.particulars == "E5HAT20RDHF"
    assert first.reference == ""
    assert first.amount == "20"

    last = records[-1]
    assert last.code == "YATPAR001"
    assert last.amount == "40"


def test_record_rows_are_spreadsheet_rows():
    _, records = read_workbook(SAMPLE)
    assert [r.row for r in records] == [4, 5, 6, 7, 8]


# ---- parse_grid unit tests (hand-built grids) --------------------------------

def _good_grid():
    # {rownum: {colnum: value}}; leading blank column A tolerated.
    return {
        1: {2: "Date of Payment", 3: "46262"},
        2: {2: "From account", 3: "12-3456-7654321"},
        3: {2: "Beneficiary", 3: "Bank Details", 4: "Code",
            5: "Particulars", 6: "Reference", 7: "Amount"},
        4: {2: "Acme Ltd", 3: "98-7654-1234567-001", 4: "AAA111",
            5: "PART", 6: "", 7: "20"},
    }


def test_parse_grid_happy():
    meta, records = parse_grid(_good_grid())
    assert meta.from_account == "12-3456-7654321"
    assert records[0].beneficiary == "Acme Ltd"
    assert records[0].row == 4


# ---- format-aware zero preservation -----------------------------------------

def test_numeric_reference_preserves_zeros_end_to_end():
    _, records = read_workbook(NUMERIC_REF)
    # F4 = 12.5 formatted 0000.00 -> "0012.50"; F5 = 100 formatted 000000 -> "000100"
    assert records[0].reference == "0012.50"
    assert records[1].reference == "000100"
    # amount still read raw (unchanged) for cents conversion
    assert records[0].amount == "20"


def test_parse_grid_uses_display_for_text_fields():
    grid = _good_grid()
    grid[4][6] = "12.5"          # Reference cell holds a bare number
    display = {(4, 6): "0012.50"}  # what Excel would show
    _, records = parse_grid(grid, display)
    assert records[0].reference == "0012.50"


def test_parse_grid_display_not_applied_to_amount():
    grid = _good_grid()
    display = {(4, 7): "20.00"}   # even if provided, amount uses raw
    _, records = parse_grid(grid, display)
    assert records[0].amount == "20"


def test_missing_from_account_raises():
    grid = _good_grid()
    del grid[2]
    with pytest.raises(InputError) as e:
        parse_grid(grid)
    assert "From account" in str(e.value)


def test_missing_header_row_raises():
    grid = _good_grid()
    del grid[3]
    with pytest.raises(InputError) as e:
        parse_grid(grid)
    assert "Beneficiary" in str(e.value)


def test_missing_amount_column_raises():
    grid = _good_grid()
    del grid[3][7]   # drop the Amount header
    with pytest.raises(InputError) as e:
        parse_grid(grid)
    assert "Amount" in str(e.value)
