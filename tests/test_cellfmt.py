"""TDD: format-aware rendering of numeric cells preserves significant zeros."""
import pytest

from trans_processor.cellfmt import render_cell


@pytest.mark.parametrize("value,fmt_id,fmt_code,expected", [
    # trailing decimals preserved
    ("20", 43, "#,##0.00", "20.00"),
    ("20.5", 164, "0.00", "20.50"),
    ("12.5", 164, "0.00", "12.50"),
    # leading zeros preserved
    ("1200", 164, "000000", "001200"),
    ("123", 164, "0000", "0123"),
    # combined leading + trailing
    ("12.5", 164, "0000.00", "0012.50"),
    # accounting/custom format with padding + decimals
    ("20", 43, r'_-* #,##0.00_-;\-* #,##0.00_-;_-* "-"??_-;_-@_-', "20.00"),
    # currency: locale token stripped, 2-decimal format preserved
    ("20", 164, "[$$-409]#,##0.00", "20.00"),
])
def test_numeric_formats_preserve_zeros(value, fmt_id, fmt_code, expected):
    assert render_cell(value, fmt_code, fmt_id) == expected


@pytest.mark.parametrize("value,fmt_id,fmt_code", [
    ("46262", 14, None),        # builtin date -> raw serial
    ("46262", 15, "d-mmm-yy"),  # builtin date -> raw serial
    ("20", 0, "General"),       # General -> raw
    ("20", 0, None),            # id 0 -> raw
    ("20.5", 0, "General"),     # General keeps as-is
])
def test_date_and_general_return_raw(value, fmt_id, fmt_code):
    assert render_cell(value, fmt_code, fmt_id) == value


@pytest.mark.parametrize("value,fmt_id,fmt_code", [
    ("20", 999, "0.00E+00"),           # scientific -> fall back to raw
    ("20", 999, "0%"),                 # percent -> fall back to raw
    ("20", 999, "# ?/?"),              # fraction -> fall back to raw
])
def test_unparseable_formats_fall_back_to_raw(value, fmt_id, fmt_code):
    # Must never corrupt the value; worst case returns it unchanged.
    assert render_cell(value, fmt_code, fmt_id) == value


def test_non_numeric_value_returned_unchanged():
    assert render_cell("E5HAT20RDHF", "0.00", 164) == "E5HAT20RDHF"
