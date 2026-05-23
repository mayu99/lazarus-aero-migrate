"""Correct Python translation of twice.cob: byte-for-byte equivalent output.

TWICE.COB displays a PIC 9(5) field: zero-padded to 5 digits, then a newline.
"""
import sys


def main() -> None:
    raw = sys.stdin.readline().strip()
    n = int(float(raw)) if raw else 0
    print(f"{n * 2:05d}")


if __name__ == "__main__":
    main()
