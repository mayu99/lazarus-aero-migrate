"""Reference Python translation of interest.cob — the known-good demo baseline.

Byte-for-byte equivalent to the original COBOL (see src/sample/interest_golden_io.json).
It documents the subtle trap this second sample exists to catch — and it's the OPPOSITE
of payroll.cob's:

    COBOL `COMPUTE WS-INTEREST = WS-PRINCIPAL * 0.0375` has NO `ROUNDED`, so it
    TRUNCATES the product to the field's 2 decimals (drops the rest, never rounds).
    A naive Python translation using round() rounds half-up/half-even and produces
    too-large interest on any input whose raw 3rd+ decimal would round up
    (e.g. principal 13.33 -> COBOL 0.49 vs round() 0.50).

We use decimal.Decimal with ROUND_DOWN (truncation) to match the mainframe exactly.

Business rule recovered from the COBOL:
    interest = truncate_to_cents(principal * 0.0375)   # truncation, NOT rounding
Output format mirrors COBOL `DISPLAY` of a PIC 9(7)V99 field:
    7 integer digits + 2 decimals, zero-padded, unsigned, trailing newline.
"""
from __future__ import annotations

import sys
from decimal import Decimal, ROUND_DOWN

RATE = Decimal("0.0375")  # PIC V9999 VALUE 0.0375
CENT = Decimal("0.01")


def interest(principal: Decimal) -> Decimal:
    """interest = principal * rate, TRUNCATED to cents (COBOL has no ROUNDED here)."""
    return (principal * RATE).quantize(CENT, rounding=ROUND_DOWN)


def format_pic_9_7v99(value: Decimal) -> str:
    """Render like COBOL DISPLAY of PIC 9(7)V99.

    GnuCOBOL shows the implied decimal point, so captured output is e.g.
    '0000037.50': 7 zero-padded integer digits, a literal '.', then 2 decimals.
    PIC 9 fields are unsigned, so we display the absolute value. We TRUNCATE here too
    (ROUND_DOWN) so the formatter never silently re-rounds an already-truncated value.
    """
    cents = value.quantize(CENT, rounding=ROUND_DOWN)
    int_part = int(abs(cents))
    frac_part = int((abs(cents) - int_part) * 100)
    return f"{int_part:07d}.{frac_part:02d}"


def main() -> None:
    raw = sys.stdin.readline().strip()
    # FUNCTION NUMVAL: parse the numeric value out of the input string.
    principal = Decimal(raw) if raw else Decimal(0)
    print(format_pic_9_7v99(interest(principal)))


if __name__ == "__main__":
    main()
