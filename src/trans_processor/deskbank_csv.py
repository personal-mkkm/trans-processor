"""Render Deskbank CSV payment-import rows (Business Online guide pp.4-6).

CSV layout mirrors the fixed-length field order but without zero/blank padding.
Records end with CRLF. Text fields never contain commas or quotes (enforced by
validation), so fields are joined literally. A trailing blank 'spare' field keeps
the positional layout faithful to the fixed-length spec.
"""
from __future__ import annotations

from .model import DetailRecord, HeaderRecord, TransformResult

CRLF = "\r\n"


def _header_fields(h: HeaderRecord) -> list[str]:
    return [
        "A",
        h.seq,
        h.orig_bank,
        h.orig_branch,
        h.customer_name,
        h.customer_number,
        h.description,
        h.due_date,
        "",  # spare
    ]


def _detail_fields(d: DetailRecord) -> list[str]:
    return [
        "D",
        d.seq,
        d.payee_bank,
        d.payee_branch,
        d.payee_account,
        d.payee_suffix,
        d.transaction_code,
        d.mts_source,
        d.amount_cents,
        d.payee_name,
        d.particulars,
        d.analysis_code,
        d.reference,
        d.payer_bank,
        d.payer_branch,
        d.payer_account,
        d.payer_suffix,
        d.payer_name,
        "",  # spare
    ]


def render(result: TransformResult) -> str:
    """Return the full Deskbank CSV text (CRLF-terminated records)."""
    rows = [_header_fields(result.header)]
    rows += [_detail_fields(d) for d in result.details]
    return "".join(",".join(fields) + CRLF for fields in rows)


def write(result: TransformResult, path) -> None:
    """Write the rendered CSV to ``path`` as ASCII with CRLF endings."""
    with open(path, "w", encoding="ascii", newline="") as fh:
        fh.write(render(result))
