#!/usr/bin/env bash
# Re-capture the REAL GnuCOBOL golden output for the demo samples and verify the
# shipped golden_io.json files match. This is the HONESTY-BAR tool: the golden
# bytes MUST be real cobc output, never hand-written. Run it to (a) regenerate the
# golden from a live compile, and (b) confirm the committed golden + reference
# Python still agree with real cobc.
#
# Requires GnuCOBOL (`cobc`) on PATH. On a box without it, install:
#   macOS:  brew install gnucobol      Debian/Ubuntu: apt-get install -y gnucobol
#
# Usage:
#   ./build_samples.sh            # verify committed golden matches live cobc (read-only check)
#   ./build_samples.sh --write    # ALSO rewrite the *_golden_io.json from live cobc
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
WRITE="${1:-}"

command -v cobc >/dev/null || { echo "ERROR: cobc (GnuCOBOL) not found on PATH"; exit 1; }
PY="$REPO/.venv/bin/python"; [ -x "$PY" ] || PY="$(command -v python3)"

cobc --version | head -1

# (module basename, golden json basename)
SAMPLES=("payroll:golden_io.json" "interest:interest_golden_io.json")

tmpd="$(mktemp -d)"; trap 'rm -rf "$tmpd"' EXIT
fail=0

for pair in "${SAMPLES[@]}"; do
  mod="${pair%%:*}"; golden="${pair##*:}"
  echo "── $mod.cob → $golden ──"
  cobc -x -o "$tmpd/$mod" "$HERE/$mod.cob"

  # Re-run every input from the committed golden through the FRESHLY compiled binary,
  # and compare to the committed cobol bytes (freshness/honesty check).
  "$PY" - "$HERE/$golden" "$tmpd/$mod" "$HERE/${mod}.py" "$WRITE" <<'PYEOF'
import json, subprocess, sys
golden_path, binary, py_path, write = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
doc = json.load(open(golden_path))
stale = []
for case in doc["cases"]:
    live = subprocess.run([binary], input=case["input"], capture_output=True, text=True, check=True).stdout
    if write == "--write":
        case["cobol"] = live
    elif live != case["cobol"]:
        stale.append((case["input"], case["cobol"], live))
# also confirm the reference Python matches live cobc byte-for-byte
pydiv = []
for case in doc["cases"]:
    pyout = subprocess.run([sys.executable, py_path], input=case["input"],
                           capture_output=True, text=True, check=True).stdout
    if pyout != case["cobol"]:
        pydiv.append((case["input"], case["cobol"], pyout))
if write == "--write":
    json.dump(doc, open(golden_path, "w"), indent=2); open(golden_path, "a").write("\n")
    print(f"  rewrote {golden_path} from live cobc ({len(doc['cases'])} cases)")
if stale:
    print(f"  STALE: {len(stale)} committed golden byte(s) differ from live cobc:")
    for i, c, l in stale: print(f"    IN={i!r} committed={c!r} live={l!r}")
    sys.exit(2)
if pydiv:
    print(f"  REFERENCE PY DIVERGES on {len(pydiv)} case(s):")
    for i, c, p in pydiv: print(f"    IN={i!r} cobol={c!r} py={p!r}")
    sys.exit(3)
print(f"  OK: committed golden == live cobc, and reference {py_path.split('/')[-1]} matches ({len(doc['cases'])} cases)")
PYEOF
done

echo "DONE — golden bytes are real GnuCOBOL output and the reference Python matches."
