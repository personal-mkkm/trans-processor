# Architecture Decision Record

Lightweight ADRs for `trans-processor`. Each entry: the decision, why, what we rejected,
and the trade-off we accepted. Ordered roughly by when it was made.

---

## ADR-1 — Standalone Python CLI (not an Excel macro workbook)

**Decision.** Build the transformer as a standalone Python command-line tool.

**Context.** The requirements brief offered two options: (1, "preferred") a macro-enabled
Excel workbook (`.xlsm`) with a "Generate Payment File" button; (2) a standalone utility
(Power Automate / VBA / Python). The tool runs monthly; beneficiary rows and amounts
change each run; payment correctness matters.

**Why Python CLI.**
- **Version control & review.** Source is plain text — diffable, reviewable, testable in
  CI. VBA locked inside an `.xlsm` is effectively a binary blob; changes are invisible in
  a diff and hard to audit for a payments process.
- **Testability.** A CLI supports true automated tests, including a **byte-exact golden
  file** for the bank output. Macro testing is manual and fragile.
- **No Excel/Office dependency.** Runs anywhere Python runs; not tied to a machine's Excel
  version, macro-security policy, or 32/64-bit VBA quirks.
- **Determinism.** The bank file format is strict (fixed field order, CRLF, cents). Code
  gives precise control over bytes; spreadsheet formulas/exports do not.

**Rejected.** `.xlsm` macro (poor versioning/testing, Office-bound); Power Automate
Desktop (licensing + orchestration overhead for a small monthly transform).

**Trade-off accepted.** Payroll staff must run a program rather than click a button in a
familiar workbook. Mitigated by **double-click launchers** (`run.bat` / `run.command`) and
a plain-English [HOW-TO-RUN](HOW-TO-RUN.md), so they never touch a terminal. A thin UI can
follow in a later phase if wanted.

---

## ADR-2 — Zero runtime dependencies (standard library only)

**Decision.** Read `.xlsx` with the standard library (`zipfile` + `xml.etree`), write with
`csv`. No `openpyxl`, `pandas`, or other third-party runtime packages.

**Why.**
- **Deployment on locked-down machines.** Payroll/finance PCs often can't `pip install`
  (no internet, restricted rights). "Install Python, done" is a far easier ask than
  "install Python + provision a package index + install dependencies".
- **Supply-chain surface.** A payments tool with zero third-party runtime code has nothing
  to audit, pin, or patch for CVEs. Fewer moving parts = fewer failure modes.
- **Longevity.** The stdlib doesn't churn; a dependency-free tool still runs years later
  without a dependency-resolution archaeology exercise.
- **The task is small.** An `.xlsx` is a zip of XML; the sheet we read is simple and flat.
  A full spreadsheet library would be far more capability than needed.

**Rejected.** `openpyxl`/`pandas` — convenient, but each adds install friction, a
supply-chain surface, and version drift for little gain on a flat single-sheet read.

**Trade-off accepted.** We wrote a small, focused xlsx reader (`reader.py` + `cellfmt.py`)
instead of importing one. It handles exactly the shapes this input uses and falls back to
raw values on anything unusual. That code is covered by tests and is the deliberate cost of
zero dependencies.

---

## ADR-3 — Test-Driven Development with a byte-exact golden file

**Decision.** Build strictly test-first (red → green → refactor); anchor the output format
with a byte-exact golden CSV; cover every fail-fast error path.

**Why.** The output is consumed by a bank — a wrong byte, missing field, or bad line
ending can cause a rejected upload or, worse, a wrong payment. TDD plus a golden file makes
the exact bytes a regression-locked contract, and forces each validation rule to be
specified as an executable example before it's implemented.

**Trade-off accepted.** Slightly more up-front test code; repaid immediately by confidence
that later changes (e.g. zero-preservation) don't silently alter the bank file — proven
when that feature landed with the golden file still byte-identical.

---

## ADR-4 — Testing with `pytest` (dev-only); latest stable Python

**Decision.** `pytest` as the sole **dev** dependency; target the latest stable Python
(`requires-python >=3.11`).

**Why.** The zero-dependency rule is about the **runtime** shipped to payroll machines;
the developer's toolchain can be richer. `pytest` gives clear assertion diffs (valuable for
byte-exact comparisons) and low-ceremony tests. Targeting current Python keeps modern
syntax/stdlib available and avoids EOL versions; local install/upgrade is acceptable for
the maintainer.

**Trade-off accepted.** A one-time `pip install pytest` for developers (not for end users).

---

## ADR-5 — Configuration via CLI flags (not a config file)

**Decision.** The two variable settings — `--transaction-code` (default `50`) and
`--mts-source` (default `DC`) — are command-line flags with baked-in defaults. No TOML/INI
config file.

**Why.** Only two knobs exist and both have safe defaults, so the launcher needs no
arguments at all. A config file would add a parser, a file to locate/validate, and another
thing for a non-technical user to get wrong — for no benefit at this size. (It also sidesteps
needing `tomllib`/a TOML parser entirely.)

**Trade-off accepted.** If many more settings appear later, revisit with a config file.

---

## ADR-6 — Output format: Deskbank CSV (of the three Business Online import formats)

**Decision.** Emit **Deskbank CSV** (payment import), not Deskbank fixed-length (180-char)
or QuickPay/PC1.

**Why.** All three are valid Business Online payment-import formats. CSV shares the
fixed-length field order but drops rigid zero/blank padding, so it's the simplest to
generate and verify, and the guide explicitly suggests producing it from spreadsheet data.
Fixed-length and PC1 remain available if the bank later requires them — the record model is
already in the right field order, so a new writer is a small addition.

**Trade-off accepted.** CSV forbids commas/quotes in text fields; enforced by validation
with a clear error.

---

## ADR-7 — Fail-fast validation with actionable, located error messages

**Decision.** Any bad input raises `InputError` and stops **before** any file is written;
the message is `<location>: <what's wrong> -> <how to fix>`, naming the row and offending
value. Truncation (e.g. a name over 20 chars) is a non-fatal warning.

**Why.** The users are non-technical and the stakes are financial. A precise, self-service
message ("Row 6 (KELROS045): Amount 'twenty' is not a number -> enter a positive dollar
value") lets them fix the spreadsheet without engineering help, and "no partial file" means
a run never yields a half-valid file that could be uploaded by mistake.

---

## ADR-8 — Target the New Zealand Deskbank layout

**Decision.** Target the NZ Westpac Deskbank layout.

**Why.** The scheme is a New Zealand one and the account data uses the NZ
`Bank-Branch-Account-Suffix` structure, which maps directly onto the Deskbank record
fields. Building to that layout represents the accounts faithfully.

---

## ADR-9 — Preserve significant zeros from the spreadsheet

**Decision.** Render numeric cells in identifier columns (Code/Particulars/Reference) as
Excel *displays* them, honouring the cell's number format to keep leading/trailing zeros;
the amount stays raw and is converted to cents.

**Why.** Excel stores `000100` or `12.50` as the numbers `100` / `12.5`; naively reading
the stored value drops zeros the user intended, corrupting a reference/code. Reading the
*displayed* value preserves intent. Amount is exempt because the bank field is cents, where
those zeros are represented differently.

---

## ADR-10 — Timestamped output filenames

**Decision.** When writing into a folder, name files
`deskbank_payment_<DDMMYY>_<YYYYMMDD-HHMMSS>.csv`.

**Why.** Monthly (and re-)runs must not silently overwrite a previously generated file that
may already have been uploaded or archived. The timestamp guarantees a distinct file per
run; an explicit `--output name.csv` still honours the exact name when the caller wants one.
