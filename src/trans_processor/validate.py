"""Field validation: amount -> cents, and text-field cleaning.

All problems raise :class:`InputError` with a precise, actionable message.
Truncation is non-fatal and returned as a warning string.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .errors import InputError

_CENTS = Decimal("0.01")


def dollars_to_cents(raw, *, location: str) -> int:
    """Convert a dollar amount to integer cents, exactly (no float rounding)."""
    text = str(raw).strip()
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError):
        raise InputError(
            location,
            f"Amount '{raw}' is not a number",
            "enter a positive dollar value, e.g. 35 or 35.00",
        )

    if amount != amount.quantize(_CENTS):
        raise InputError(
            location,
            f"Amount '{raw}' has more than 2 decimal places",
            "use whole cents, e.g. 35 or 35.50",
        )
    if amount <= 0:
        raise InputError(
            location,
            f"Amount {raw} must be greater than 0",
            "remove the row or set a positive amount",
        )
    return int((amount * 100).to_integral_value())


def clean_text(raw, *, max_len: int, field: str, location: str):
    """Validate/normalise a text field. Returns ``(value, warnings)``.

    Rejects commas and quotes (Business Online treats them as invalid). Truncates
    to ``max_len`` and records a warning rather than failing.
    """
    if raw is None:
        return "", []
    value = str(raw)
    if "," in value:
        raise InputError(
            location,
            f"{field} '{value}' contains a comma (not allowed by Business Online)",
            "remove commas and quotes",
        )
    if '"' in value or "'" in value:
        raise InputError(
            location,
            f"{field} '{value}' contains a quote (not allowed by Business Online)",
            "remove commas and quotes",
        )
    warnings: list[str] = []
    if len(value) > max_len:
        truncated = value[:max_len]
        warnings.append(
            f"{location}: {field} '{value}' truncated to {max_len} chars '{truncated}'"
        )
        value = truncated
    return value, warnings
