"""Domain model: config, parsed input, and output records."""
from __future__ import annotations

from dataclasses import dataclass, field

# Deskbank field max lengths (guide pp.5-6).
NAME_MAX = 20
PARTICULARS_MAX = 12
ANALYSIS_MAX = 12
REFERENCE_MAX = 12


@dataclass(frozen=True)
class Config:
    transaction_code: str = "50"   # 50=Payment, 52=Payroll
    mts_source: str = "DC"         # DC=payment credit


@dataclass
class PaymentMeta:
    """Header-level data read from the top of the deduction list."""
    payment_date: str      # raw Date of Payment cell (Excel serial or text)
    from_account: str      # raw From account string (payer/funding account)


@dataclass
class DeductionRecord:
    """One beneficiary payment row from the deduction list."""
    row: int               # 1-based source row number (for error messages)
    beneficiary: str
    bank_details: str      # raw payee account string
    code: str              # -> analysis code
    particulars: str
    reference: str
    amount: str            # raw amount cell (dollars)


@dataclass
class HeaderRecord:
    seq: str
    orig_bank: str
    orig_branch: str
    customer_name: str
    customer_number: str
    description: str
    due_date: str          # DDMMYY


@dataclass
class DetailRecord:
    seq: str
    payee_bank: str
    payee_branch: str
    payee_account: str
    payee_suffix: str
    transaction_code: str
    mts_source: str
    amount_cents: str
    payee_name: str
    particulars: str
    analysis_code: str
    reference: str
    payer_bank: str
    payer_branch: str
    payer_account: str
    payer_suffix: str
    payer_name: str


@dataclass
class TransformResult:
    header: HeaderRecord
    details: list[DetailRecord]
    warnings: list[str] = field(default_factory=list)
