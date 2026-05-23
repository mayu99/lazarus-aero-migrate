"""Wrong Python translation of twice.cob: forgets the COBOL zero-padding.

Prints the bare integer (e.g. "20" instead of "00020"), so the differential
oracle MUST flag it as non-equivalent. This is the demo's red-state proof.
"""
import sys


def main() -> None:
    raw = sys.stdin.readline().strip()
    n = int(float(raw)) if raw else 0
    print(n * 2)


if __name__ == "__main__":
    main()
