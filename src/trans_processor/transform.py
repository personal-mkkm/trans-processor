"""Assemble Deskbank header + detail records from parsed deduction input."""
from __future__ import annotations

from .accounts import parse_account, excel_serial_to_ddmmyy
from .model import (
    ANALYSIS_MAX,
    Config,
    DeductionRecord,
    DetailRecord,
    HeaderRecord,
    NAME_MAX,
    PARTICULARS_MAX,
    PaymentMeta,
    REFERENCE_MAX,
    TransformResult,
)
from .validate import clean_text, dollars_to_cents


def transform(meta: PaymentMeta, records: list[DeductionRecord],
              config: Config) -> TransformResult:
    """Build one Header ('A') + one Detail ('D') per deduction row.

    Raises InputError on any bad value (fail-fast, before any file is written);
    truncations are collected as warnings.
    """
    warnings: list[str] = []

    payer = parse_account(meta.from_account, location="From account")
    due_date = excel_serial_to_ddmmyy(meta.payment_date, location="Date of Payment")

    header = HeaderRecord(
        seq="000001",
        orig_bank=payer.bank,
        orig_branch=payer.branch,
        customer_name="",       # optional, not in input
        customer_number="",     # not currently used
        description="",         # optional, not in input
        due_date=due_date,
    )

    details: list[DetailRecord] = []
    for i, rec in enumerate(records, start=1):
        loc = f"Row {rec.row} ({rec.code})" if rec.code else f"Row {rec.row}"
        payee = parse_account(rec.bank_details, location=f"{loc} Bank Details")
        amount_cents = dollars_to_cents(rec.amount, location=loc)

        payee_name, w = clean_text(rec.beneficiary, max_len=NAME_MAX,
                                   field="Payee name", location=loc)
        warnings += w
        particulars, w = clean_text(rec.particulars, max_len=PARTICULARS_MAX,
                                    field="Particulars", location=loc)
        warnings += w
        analysis, w = clean_text(rec.code, max_len=ANALYSIS_MAX,
                                 field="Analysis code", location=loc)
        warnings += w
        reference, w = clean_text(rec.reference, max_len=REFERENCE_MAX,
                                  field="Reference", location=loc)
        warnings += w

        details.append(DetailRecord(
            seq=f"{i:06d}",
            payee_bank=payee.bank,
            payee_branch=payee.branch,
            payee_account=payee.account,
            payee_suffix=payee.suffix,
            transaction_code=config.transaction_code,
            mts_source=config.mts_source,
            amount_cents=str(amount_cents),
            payee_name=payee_name,
            particulars=particulars,
            analysis_code=analysis,
            reference=reference,
            payer_bank=payer.bank,
            payer_branch=payer.branch,
            payer_account=payer.account,
            payer_suffix=payer.suffix,
            payer_name="",          # optional, not in input
        ))

    return TransformResult(header=header, details=details, warnings=warnings)
