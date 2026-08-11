"""NZ bank-account parsing and Excel-serial date conversion."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .errors import InputError

ACCOUNT_WIDTH = 8
SUFFIX_WIDTH = 4
# Excel 1900 date system, corrected for the fictitious 1900-02-29: serial 1 == 1899-12-31,
# and day 0 is 1899-12-30. So date = 1899-12-30 + serial days (for serial >= 61).
_EXCEL_EPOCH = date(1899, 12, 30)


@dataclass(frozen=True)
class Account:
    bank: str      # 2 digits
    branch: str    # 4 digits
    account: str   # 8 digits, left zero-padded
    suffix: str    # 4 digits, left zero-padded


def parse_account(raw: str, *, location: str = "Account") -> Account:
    """Parse ``Bank-Branch-Account[-Suffix]`` into a zero-padded Account.

    Missing suffix defaults to ``0000``. Raises InputError with guidance on any
    malformed value.
    """
    value = (raw or "").strip()
    parts = value.split("-")
    if len(parts) == 3:
        parts = parts + ["0"]  # default suffix
    if len(parts) != 4:
        raise InputError(
            location,
            f"'{value}' has {len(parts)} part(s), expected Bank-Branch-Account-Suffix",
            "e.g. 98-7654-1234567-001",
        )

    bank, branch, account, suffix = (p.strip() for p in parts)
    for name, part in (("Bank", bank), ("Branch", branch),
                       ("Account", account), ("Suffix", suffix)):
        if not part.isdigit():
            raise InputError(
                location,
                f"{name} '{part}' is not numeric",
                "use digits only, e.g. 98-7654-1234567-001",
            )

    if len(account) > ACCOUNT_WIDTH:
        raise InputError(
            location,
            f"Account '{account}' exceeds {ACCOUNT_WIDTH} digits",
            "check the account number",
        )
    if len(suffix) > SUFFIX_WIDTH:
        raise InputError(
            location,
            f"Suffix '{suffix}' exceeds {SUFFIX_WIDTH} digits",
            "check the account suffix",
        )

    return Account(
        bank=bank,
        branch=branch,
        account=account.rjust(ACCOUNT_WIDTH, "0"),
        suffix=suffix.rjust(SUFFIX_WIDTH, "0"),
    )


def excel_serial_to_ddmmyy(serial, *, location: str = "Date of Payment") -> str:
    """Convert an Excel date serial number to ``DDMMYY``."""
    try:
        n = int(serial)
    except (TypeError, ValueError):
        raise InputError(
            location,
            f"'{serial}' is not a valid Excel date",
            "enter a real date cell in the deduction list",
        )
    d = _EXCEL_EPOCH + timedelta(days=n)
    return d.strftime("%d%m%y")
