"""Reference Python translation of payroll.cob — the known-good demo baseline.

This is what LAZARUS aims to produce. It is byte-for-byte equivalent to the
original COBOL (see src/sample/golden_io.json), and it documents the one subtle
trap that the differential oracle exists to catch:

    COBOL `COMPUTE WS-TAX ROUNDED = WS-GROSS-PAY * 0.225` rounds HALF-UP.
    Python's built-in round() / float arithmetic rounds half-to-even (banker's),
    so a naive translation produces the WRONG net pay on half-cent ties
    (e.g. gross 1.00 -> banker's 0.78 vs COBOL's correct 0.77).

We use decimal.Decimal with ROUND_HALF_UP to match the mainframe exactly.

Business rule recovered from the COBOL:
    net = gross - round_half_up(gross * 0.225, 2 decimals)
Output format mirrors COBOL `DISPLAY` of a PIC 9(7)V99 field:
    7 integer digits + 2 decimals, zero-padded, unsigned, trailing newline.
"""
from __future__ import annotations

import sys
from decimal import Decimal, ROUND_HALF_UP

TAX_RATE = Decimal("0.225")  # PIC V999 VALUE 0.225
CENT = Decimal("0.01")


def net_pay(gross: Decimal) -> Decimal:
    """net = gross - ROUNDED(gross * tax_rate). ROUNDED is COBOL half-up."""
    tax = (gross * TAX_RATE).quantize(CENT, rounding=ROUND_HALF_UP)
    return gross - tax


def format_pic_9_7v99(value: Decimal) -> str:
    """Render like COBOL DISPLAY of PIC 9(7)V99.

    GnuCOBOL shows the implied decimal point, so captured output is e.g.
    '0000775.00': 7 zero-padded integer digits, a literal '.', then 2 decimals.
    PIC 9 fields are unsigned, so we display the absolute value.
    """
    cents = value.quantize(CENT, rounding=ROUND_HALF_UP)
    int_part = int(abs(cents))
    frac_part = int((abs(cents) - int_part) * 100)
    return f"{int_part:07d}.{frac_part:02d}"


def main() -> None:
    raw = sys.stdin.readline().strip()
    # FUNCTION NUMVAL: parse the numeric value out of the input string.
    gross = Decimal(raw) if raw else Decimal(0)
    print(format_pic_9_7v99(net_pay(gross)))


if __name__ == "__main__":
    main()
