"""Read the monthly deduction-list .xlsx using only the standard library.

Two layers:
- ``read_workbook(path)`` loads the first worksheet into a grid and delegates to
- ``parse_grid(grid)`` — a pure function that locates the labels/header and builds
  the domain objects, raising :class:`InputError` on anything missing.
"""
from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET

from .cellfmt import render_cell
from .errors import InputError
from .model import DeductionRecord, PaymentMeta

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
_DOCREL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def _col_to_num(ref: str) -> int:
    letters = "".join(c for c in ref if c.isalpha())
    n = 0
    for c in letters:
        n = n * 26 + (ord(c.upper()) - 64)
    return n


# Builtin numeric number-format codes we may need to honour (ECMA-376). Date/time
# builtins are handled inside cellfmt.render_cell, so they need no code here.
_BUILTIN_FMTS = {
    1: "0", 2: "0.00", 3: "#,##0", 4: "#,##0.00",
    9: "0%", 10: "0.00%", 11: "0.00E+00",
    37: "#,##0;(#,##0)", 38: "#,##0;[Red](#,##0)",
    39: "#,##0.00;(#,##0.00)", 40: "#,##0.00;[Red](#,##0.00)",
    43: r"_-* #,##0.00_-;\-* #,##0.00_-;_-* \"-\"??_-;_-@_-",
    44: r"_-* #,##0.00_-;\-* #,##0.00_-;_-* \"-\"??_-;_-@_-",
}


def _load_styles(z: zipfile.ZipFile):
    """Return (xf_index -> numFmtId list, numFmtId -> format code)."""
    fmt_codes = dict(_BUILTIN_FMTS)
    xf_fmt_ids: list[int] = []
    if "xl/styles.xml" not in z.namelist():
        return xf_fmt_ids, fmt_codes
    styles = ET.fromstring(z.read("xl/styles.xml"))
    numfmts = styles.find(_q(_MAIN, "numFmts"))
    if numfmts is not None:
        for nf in numfmts.findall(_q(_MAIN, "numFmt")):
            fmt_codes[int(nf.get("numFmtId"))] = nf.get("formatCode")
    cellxfs = styles.find(_q(_MAIN, "cellXfs"))
    if cellxfs is not None:
        for xf in cellxfs.findall(_q(_MAIN, "xf")):
            xf_fmt_ids.append(int(xf.get("numFmtId", "0")))
    return xf_fmt_ids, fmt_codes


def _first_sheet_path(z: zipfile.ZipFile) -> str:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    sheet = wb.find(_q(_MAIN, "sheets")).find(_q(_MAIN, "sheet"))
    rid = sheet.get(_q(_DOCREL, "id"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    for rel in rels.findall(_q(_RELS, "Relationship")):
        if rel.get("Id") == rid:
            target = rel.get("Target")
            return target if target.startswith("xl/") else f"xl/{target}"
    return "xl/worksheets/sheet1.xml"


def _load_grid(path):
    """Return (grid, display) for the first worksheet.

    ``grid``    = {row: {col: raw_cell_text}} — numbers as stored (unformatted).
    ``display`` = {(row, col): shown_text} for numeric cells whose number format
                  adds significant zeros (used to preserve them in text columns).
    """
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(_q(_MAIN, "si")):
                shared.append("".join(t.text or "" for t in si.iter(_q(_MAIN, "t"))))

        xf_fmt_ids, fmt_codes = _load_styles(z)
        sheet = ET.fromstring(z.read(_first_sheet_path(z)))
        data = sheet.find(_q(_MAIN, "sheetData"))
        grid: dict[int, dict[int, str]] = {}
        display: dict[tuple[int, int], str] = {}
        for row in data.findall(_q(_MAIN, "row")):
            rownum = int(row.get("r"))
            cells: dict[int, str] = {}
            for c in row.findall(_q(_MAIN, "c")):
                t = c.get("t")
                v = c.find(_q(_MAIN, "v"))
                inline = c.find(_q(_MAIN, "is"))
                col = _col_to_num(c.get("r"))
                if t == "s" and v is not None:
                    val = shared[int(v.text)]
                elif t == "inlineStr" and inline is not None:
                    val = "".join(x.text or "" for x in inline.iter(_q(_MAIN, "t")))
                elif v is not None:
                    val = v.text or ""
                    # numeric cell: compute the displayed value (zeros preserved)
                    s = c.get("s")
                    fmt_id = xf_fmt_ids[int(s)] if s is not None and int(s) < len(xf_fmt_ids) else 0
                    shown = render_cell(val, fmt_codes.get(fmt_id), fmt_id)
                    if shown != val:
                        display[(rownum, col)] = shown
                else:
                    val = ""
                cells[col] = val
            if cells:
                grid[rownum] = cells
    return grid, display


def read_workbook(path):
    """Read an .xlsx deduction list into (PaymentMeta, list[DeductionRecord])."""
    grid, display = _load_grid(path)
    return parse_grid(grid, display)


# ---- pure parsing ------------------------------------------------------------

_HEADER_ALIASES = {
    "beneficiary": "beneficiary",
    "bank details": "bank_details",
    "code": "code",
    "particulars": "particulars",
    "reference": "reference",
    "amount": "amount",
}
_REQUIRED_HEADERS = ("beneficiary", "bank_details", "amount")


def _label_value(grid, label: str):
    """Return the cell immediately to the right of a label cell, or None."""
    target = label.strip().lower()
    for rownum, cells in grid.items():
        for col, val in cells.items():
            if str(val).strip().lower() == target:
                return str(cells.get(col + 1, "")).strip()
    return None


def parse_grid(grid: dict[int, dict[int, str]], display=None):
    display = display or {}
    payment_date = _label_value(grid, "Date of Payment")
    if not payment_date:
        raise InputError(
            "Deduction list",
            "'Date of Payment' not found",
            "add it near the top with the date in the cell to its right",
        )
    from_account = _label_value(grid, "From account")
    if not from_account:
        raise InputError(
            "Deduction list",
            "'From account' not found",
            "add it as e.g. 12-3456-7654321 in the cell to its right",
        )

    # Locate the table header row (the one containing 'Beneficiary').
    header_row = None
    for rownum in sorted(grid):
        if any(str(v).strip().lower() == "beneficiary" for v in grid[rownum].values()):
            header_row = rownum
            break
    if header_row is None:
        raise InputError(
            "Deduction list",
            "table header row with 'Beneficiary' not found",
            "add a header row: Beneficiary | Bank Details | Code | Particulars | Reference | Amount",
        )

    col_of: dict[str, int] = {}
    for col, val in grid[header_row].items():
        key = _HEADER_ALIASES.get(str(val).strip().lower())
        if key:
            col_of[key] = col
    for needed in _REQUIRED_HEADERS:
        if needed not in col_of:
            label = "Bank Details" if needed == "bank_details" else needed.capitalize()
            raise InputError(
                "Deduction list",
                f"'{label}' column not found in the header row",
                "add the missing column header",
            )

    records: list[DeductionRecord] = []
    for rownum in sorted(r for r in grid if r > header_row):
        cells = grid[rownum]

        def cell(field: str, use_display: bool = True) -> str:
            col = col_of.get(field)
            if not col:
                return ""
            if use_display and (rownum, col) in display:
                return str(display[(rownum, col)]).strip()
            return str(cells.get(col, "")).strip()

        beneficiary = cell("beneficiary")
        bank_details = cell("bank_details")
        amount = cell("amount", use_display=False)   # raw -> cents; never reformat
        if not (beneficiary or bank_details or amount):
            break  # first fully-empty row ends the table

        records.append(DeductionRecord(
            row=rownum,
            beneficiary=beneficiary,
            bank_details=bank_details,
            code=cell("code"),
            particulars=cell("particulars"),
            reference=cell("reference"),
            amount=amount,
        ))
    return PaymentMeta(payment_date=payment_date, from_account=from_account), records
