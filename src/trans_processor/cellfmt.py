"""Render a numeric xlsx cell the way Excel displays it, preserving significant
leading/trailing zeros — but only for the simple numeric formats used by identifier
columns. Anything unusual (dates, General, scientific, percent, fractions) falls back
to the raw stored value, so a value is never corrupted.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

# Builtin numFmtId ranges that mean date/time (ECMA-376). For these we keep the raw
# serial — the caller may still need it as a number (e.g. Date of Payment).
_DATE_TIME_IDS = set(range(14, 23)) | {45, 46, 47} | {27, 28, 29, 30, 31, 36,
                                                       50, 51, 52, 53, 54, 55, 56, 57, 58}

# Tokens we strip from a format section before reading digit placeholders.
_BRACKETS = re.compile(r"\[[^\]]*\]")      # [$$-409], [Red], [>100] ...
_QUOTED = re.compile(r'"[^"]*"')            # literal text
_ESCAPED = re.compile(r"\\.")              # escaped single char
_SPACER = re.compile(r"[_*].")             # _x spacing / *x fill (2 chars each)


def _is_numeric(value: str) -> bool:
    try:
        Decimal(str(value))
        return True
    except (InvalidOperation, ValueError):
        return False


def render_cell(value: str, fmt_code, num_fmt_id) -> str:
    """Return ``value`` rendered per its number format, or unchanged if not applicable."""
    if not _is_numeric(value):
        return value
    if num_fmt_id in _DATE_TIME_IDS:
        return value
    if not fmt_code or fmt_code.strip().lower() == "general":
        return value

    section = fmt_code.split(";", 1)[0]

    # Date/time letters (outside quotes/brackets) -> treat as date, keep raw.
    stripped_for_dt = _QUOTED.sub("", _BRACKETS.sub("", section))
    if re.search(r"[dmhys]", stripped_for_dt, re.IGNORECASE):
        return value

    # Remove decoration, leaving only digit placeholders / separators.
    cleaned = _SPACER.sub("", _ESCAPED.sub("", _QUOTED.sub("", _BRACKETS.sub("", section))))

    # Formats we deliberately don't handle numerically -> keep raw.
    if any(ch in cleaned for ch in ("%", "E", "e", "/")):
        return value

    cleaned = cleaned.replace(",", "")
    if "." in cleaned:
        int_part, frac_part = cleaned.split(".", 1)
    else:
        int_part, frac_part = cleaned, ""

    int_pad = int_part.count("0")
    decimals = frac_part.count("0")
    if int_pad == 0 and decimals == 0 and "#" not in cleaned:
        return value  # no digit placeholders found

    amount = Decimal(str(value))
    quantized = amount.quantize(Decimal(1).scaleb(-decimals)) if decimals else \
        amount.quantize(Decimal(1))
    sign = "-" if quantized < 0 else ""
    digits = f"{abs(quantized):.{decimals}f}"
    whole, _, frac = digits.partition(".")
    whole = whole.rjust(int_pad, "0")
    out = whole + (("." + frac) if decimals else "")
    return sign + out
