#!/usr/bin/env bash
# Build a Linux x86-64 GnuCOBOL binary of payroll.cob for the STRETCH oracle path:
# mount this binary into the Managed Agents sandbox via base_environment and run it
# there with NO apt/root needed (the sandbox is Ubuntu x86-64; see RESEARCH §1).
#
# WHY a script (not a checked-in binary): the dev machine that captured golden_io.json
# is arm64 macOS — its `cobc` output is a Mach-O arm64 binary that will NOT run in the
# Linux sandbox. The portable binary must be built ON Linux x86-64. Run this on a Linux
# host, or via Docker from any host (Docker path below), then commit the produced
# `payroll_linux_x86_64` under src/sample/.
#
# Usage:
#   ./build_payroll_binary.sh            # build natively (must be Linux x86-64 w/ cobc)
#   ./build_payroll_binary.sh --docker   # build via Docker (works from macOS/arm64 too)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/payroll.cob"
OUT="$HERE/payroll_linux_x86_64"

build_native() {
  command -v cobc >/dev/null || { echo "ERROR: cobc not found on PATH"; exit 1; }
  # -x: executable; -static: prefer static libcob so the binary needs no libcob.so at
  # runtime in the sandbox. (On glibc Linux this still links libc dynamically, which is
  # present in the Ubuntu sandbox; for a fully static build use a musl toolchain.)
  cobc -x -static -O2 -o "$OUT" "$SRC"
  echo "built: $OUT"
  file "$OUT" || true
}

build_docker() {
  command -v docker >/dev/null || { echo "ERROR: docker not found"; exit 1; }
  docker run --rm --platform linux/amd64 -v "$HERE:/work" -w /work ubuntu:24.04 bash -c '
    set -euo pipefail
    apt-get update -qq && apt-get install -y -qq gnucobol >/dev/null
    cobc -x -static -O2 -o payroll_linux_x86_64 payroll.cob
    cobc --version | head -1
    file payroll_linux_x86_64 || true
  '
  echo "built via docker: $OUT"
}

case "${1:-}" in
  --docker) build_docker ;;
  *)        build_native ;;
esac

echo
echo "Next: sanity-check the binary reproduces golden_io.json, then commit it:"
echo "  python3 - <<'PY'"
echo "  import json, subprocess, pathlib"
echo "  g = json.loads(pathlib.Path('golden_io.json').read_text())"
echo "  for c in g['cases']:"
echo "      out = subprocess.run(['./payroll_linux_x86_64'], input=c['input'],"
echo "                           capture_output=True, text=True, check=True).stdout"
echo "      assert out == c['cobol'], (c['input'], out, c['cobol'])"
echo "  print('binary reproduces golden_io.json:', len(g['cases']), 'cases OK')"
echo "  PY"
