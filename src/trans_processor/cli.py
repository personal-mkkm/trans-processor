"""Command-line entry point: deduction-list .xlsx -> Deskbank CSV.

Fail-fast: any bad input prints a precise message and exits non-zero *before*
writing an output file (no partial/garbage output).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from .deskbank_csv import write
from .errors import InputError
from .model import Config
from .reader import read_workbook
from .transform import transform


def _resolve_input(raw: str) -> Path:
    p = Path(raw)
    if p.is_dir():
        xlsx = sorted(f for f in p.glob("*.xlsx") if not f.name.startswith("~$"))
        if not xlsx:
            raise InputError(f"Input folder '{p}'", "no .xlsx file found",
                             "put the monthly Deduction list.xlsx in this folder")
        if len(xlsx) > 1:
            names = ", ".join(f.name for f in xlsx)
            raise InputError(f"Input folder '{p}'", f"more than one .xlsx found ({names})",
                             "keep only the current month's file in the folder")
        return xlsx[0]
    if not p.exists():
        raise InputError(f"Input '{p}'", "file not found",
                         "check the file name and location")
    return p


def _resolve_output(raw: str, due_date: str) -> Path:
    p = Path(raw)
    if p.is_dir() or p.suffix.lower() != ".csv":
        # Timestamp keeps each run's file distinct so previous ones are never overwritten.
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        p.mkdir(parents=True, exist_ok=True)
        return p / f"deskbank_payment_{due_date}_{stamp}.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def run(args) -> int:
    in_path = _resolve_input(args.input)
    meta, records = read_workbook(in_path)
    if not records:
        raise InputError(f"'{in_path.name}'", "no deduction rows found",
                         "add at least one beneficiary row under the header")

    config = Config(transaction_code=args.transaction_code, mts_source=args.mts_source)
    result = transform(meta, records, config)

    out_path = _resolve_output(args.output, result.header.due_date)
    write(result, out_path)

    total = sum(int(d.amount_cents) for d in result.details)
    print(f"OK: wrote {len(result.details)} payment(s), total ${total/100:,.2f}")
    print(f"    due date {result.header.due_date}  ->  {out_path}")
    for w in result.warnings:
        print(f"WARNING: {w}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="trans-processor",
        description="Convert the monthly deduction list into a Westpac Deskbank CSV payment file.",
    )
    parser.add_argument("--input", default="input",
                        help="input .xlsx file, or a folder containing one (default: input)")
    parser.add_argument("--output", default="output",
                        help="output .csv file, or a folder to write into (default: output)")
    parser.add_argument("--transaction-code", default="50",
                        help="Deskbank transaction code: 50=Payment (default), 52=Payroll")
    parser.add_argument("--mts-source", default="DC",
                        help="Deskbank MTS source (default: DC)")
    args = parser.parse_args(argv)

    try:
        return run(args)
    except InputError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
