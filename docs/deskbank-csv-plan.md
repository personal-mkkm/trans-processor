# Deduction List → Westpac Deskbank CSV — Design

## Context
The NZ Extraordinary Public Transport Scheme collects payroll deductions and remits them
to external beneficiaries. Payroll produces a monthly **Deduction list** (`.xlsx`);
Westpac **Business Online** cannot ingest that format. This tool transforms it into a
**Deskbank CSV** payment-import file, uploadable directly to Business Online — removing
manual re-keying and its error/operational risk. The accounts are New Zealand format
(`Bank-Branch-Account-Suffix`), matching the Westpac Deskbank layout.

## Input file format & assumptions
The tool reads a single-sheet `.xlsx` (the **first worksheet**). The reader locates data
by label/header text, not by fixed cell addresses, so a leading blank column (or the table
starting a few columns in) is tolerated.

**Expected content:**
- **`Date of Payment`** — a cell containing this label, with the payment date in the cell
  **immediately to its right**. Must be a real Excel **date** (stored as a serial number),
  → becomes the Deskbank due date `DDMMYY`.
- **`From account`** — a cell with this label, with the funding/payer account to its right,
  as `Bank-Branch-Account[-Suffix]` (e.g. `12-3456-7654321`).
- **Table header row** — the row containing the cell **`Beneficiary`** is detected as the
  header. Columns are matched by header name (case-insensitive):

  | Header | Required | Maps to |
  |---|---|---|
  | `Beneficiary` | yes | payee name |
  | `Bank Details` | yes | payee account `Bank-Branch-Account-Suffix` |
  | `Amount` | yes | dollars → cents |
  | `Code` | no | analysis code |
  | `Particulars` | no | particulars |
  | `Reference` | no | reference |

- **Detail rows** follow the header row. Reading **stops at the first fully-empty row**
  (Beneficiary + Bank Details + Amount all blank). One output detail record per row; rows
  are never aggregated.

**Value assumptions / rules:**
- **Amount** — a positive number in **dollars**, ≤ 2 decimal places (`20`, `20.50`).
  Converted to integer cents; `0`/negative/non-numeric/>2dp → fail-fast error.
- **Accounts** — digits split on `-`; account left-zero-padded to 8, suffix to 4; a
  missing suffix defaults to `0000`; account > 8 or suffix > 4 digits → error.
- **Text fields** (Beneficiary/Particulars/Code/Reference) — **no commas or quotes**
  (Business Online rejects them) → error. Over-length values are truncated (name 20;
  particulars/code/reference 12) with a **warning**, not an error.
- **Number formatting** — numeric cells in identifier columns are read as **Excel displays
  them**, so leading/trailing zeros in a Code/Reference are preserved (see ADR-9).
- **Missing** `Date of Payment`, `From account`, the header row, or any required column
  → fail-fast error naming what to add.

## Input → Output mapping
Input sheet has `Date of Payment` (Excel serial), `From account`, then a table:
`Beneficiary | Bank Details | Code | Particulars | Reference | Amount`.

Output = one Deskbank **Header ('A')** + one **Detail ('D')** per deduction row.

| Deskbank field | Source / rule |
|---|---|
| Header due date | `Date of Payment` serial → `DDMMYY` (46262 → `280826`) |
| Header originating bank/branch | from `From account` (`12`/`3456`) |
| Header customer name / description | blank (optional, not in input) |
| Detail payee account | parse `Bank Details` → `Bank/Branch/Account(8)/Suffix(4)` |
| Detail transaction code | config, default `50` |
| Detail MTS source | `DC` |
| Detail amount | dollars → **cents** (`20` → `2000`) |
| Detail payee name | `Beneficiary` (≤20, truncate+warn) |
| Detail particulars / analysis code / reference | `Particulars` / `Code` / `Reference` (≤12) |
| Detail payer account | `From account` → `12/3456/07654321/0000` |
| Detail payer name | blank (optional) |

Rules: accounts split on `-`, account left-zero-padded to 8, suffix to 4, missing suffix
⇒ `0000`. CSV is positional (a trailing blank *spare* field is kept); records end CRLF;
**no commas or quotes** allowed in text fields. Optional fields absent from input are
emitted blank. Rows are never aggregated — one detail per row.

## Architecture (zero runtime deps, stdlib only)
```
src/trans_processor/
  reader.py        stdlib xlsx (zipfile + xml.etree) → PaymentMeta + [DeductionRecord]
  cellfmt.py       render numeric cells as Excel shows them (preserves leading/trailing
                   zeros in identifier columns like Code/Reference; amount stays raw→cents)
  accounts.py      parse_account(), excel_serial_to_ddmmyy()
  validate.py      dollars_to_cents() (Decimal, exact), clean_text() (comma/quote/trunc)
  transform.py     meta + records + Config → HeaderRecord + [DetailRecord] (+warnings)
  deskbank_csv.py  render()/write() — field order, CRLF, ASCII
  cli.py           argparse; fail-fast, no partial output
  model.py, errors.py
```

## Fail-fast contract
Any bad value raises `InputError` (`<location>: <problem> -> <fix>`) and stops **before**
a file is written. Truncation is a non-fatal warning. See `cli.py` / `validate.py`.

## Testing
TDD, `pytest`. Byte-exact golden file `tests/fixtures/expected.csv` anchors the format;
every error path asserts the exact guidance text. Run: `pytest`.

## Outstanding questions
1. Transaction code `50` (Payment) vs `52` (payroll) — default `50`, `--transaction-code`.
2. MTS Source `DC` assumed for payments.
