# trans-processor

Transforms the monthly **NZ transport-scheme deduction list** (`.xlsx`) into a Westpac
**Business Online "Deskbank" CSV** payment-import file.

- **Non-technical users:** see [`docs/HOW-TO-RUN.md`](docs/HOW-TO-RUN.md) — drop the file
  in `input/`, double-click `run.bat` (Windows) or `run.command` (Mac), collect the file
  from `output/`.
- **Design:** see [`docs/deskbank-csv-plan.md`](docs/deskbank-csv-plan.md).
- **Why Python / lean deps / TDD (rationale):** see
  [`docs/architecture-decisions.md`](docs/architecture-decisions.md).

## What it does
Reads `Date of Payment`, `From account`, and each beneficiary row, then writes one
Deskbank **Header ('A')** record + one **Detail ('D')** record per deduction:
`Date of Payment` → due date `DDMMYY`; dollar amounts → cents; accounts parsed into
`Bank/Branch/Account/Suffix`. Fails fast with a precise message on bad input, writing no
partial file.

## Requirements
- Python **3.11+** (latest stable recommended). **No third-party runtime dependencies.**
- Dev/test: `pytest` (`pip install -e ".[dev]"`).

## Usage
```bash
# folders (default): reads the single .xlsx in input/, writes to output/
python -m trans_processor.cli --input input --output output

# explicit files
python -m trans_processor.cli --input "Deduction list.xlsx" --output payment.csv

# options
--transaction-code 50   # 50=Payment (default), 52=Payroll
--mts-source DC         # Deskbank MTS source (default DC)
```

## Tests
```bash
pytest
```
Built test-first (TDD). A byte-exact golden file (`tests/fixtures/expected.csv`) anchors
the output format; every fail-fast error path is covered.

## Open items (pending confirmation)
- Transaction code `50` vs `52` (payroll) — default `50`, override with `--transaction-code`.
- MTS Source `DC` assumed for payments.
