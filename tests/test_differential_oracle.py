"""Tests for the LAZARUS differential oracle harness.

The oracle is the judge-proofing core: it proves migrated Python is equivalent
to the ORIGINAL COBOL by running real GnuCOBOL and diffing byte-for-byte. These
tests exercise the harness with tiny local fixtures (no network) and the golden
fallback path used when GnuCOBOL is unavailable on stage.

Subprocess-backed tests are marked `requires_cobc` and skip cleanly when cobc is
absent; the golden-fallback and pure-logic tests always run.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import requires_cobc

import differential_oracle as oracle


# --------------------------------------------------------------------------
# compile_cobol / run_binary  (real GnuCOBOL, tiny fixture)
# --------------------------------------------------------------------------
@requires_cobc
def test_compile_cobol_produces_runnable_binary(fixtures_dir, tmp_path):
    binary = oracle.compile_cobol(str(fixtures_dir / "twice.cob"), str(tmp_path / "dbl"))
    assert Path(binary).exists()
    assert oracle.run_binary(binary, "10\n") == "00020\n"


@requires_cobc
def test_compile_cobol_raises_on_bad_source(tmp_path):
    bad = tmp_path / "bad.cob"
    bad.write_text("this is not cobol at all\n")
    with pytest.raises(Exception):
        oracle.compile_cobol(str(bad), str(tmp_path / "out"))


# --------------------------------------------------------------------------
# run_python  (real interpreter, tiny fixture)
# --------------------------------------------------------------------------
def test_run_python_correct_translation_matches_padding(fixtures_dir):
    out = oracle.run_python(str(fixtures_dir / "twice_correct.py"), "10\n")
    assert out == "00020\n"


def test_run_python_wrong_translation_differs(fixtures_dir):
    out = oracle.run_python(str(fixtures_dir / "twice_wrong.py"), "10\n")
    assert out == "20\n"  # missing COBOL zero-padding


# --------------------------------------------------------------------------
# differential_test  (full COBOL-vs-Python diff)
# --------------------------------------------------------------------------
@requires_cobc
def test_differential_test_all_match_for_correct_translation(fixtures_dir):
    results = oracle.differential_test(
        str(fixtures_dir / "twice.cob"),
        str(fixtures_dir / "twice_correct.py"),
        ["1\n", "10\n", "999\n"],
    )
    assert len(results) == 3
    assert all(r["match"] for r in results)
    # each record carries the fields the UI diff viewer renders
    for r in results:
        assert set(r) >= {"input", "cobol", "python", "match"}


@requires_cobc
def test_differential_test_flags_mismatch_for_wrong_translation(fixtures_dir):
    results = oracle.differential_test(
        str(fixtures_dir / "twice.cob"),
        str(fixtures_dir / "twice_wrong.py"),
        ["10\n"],
    )
    assert results[0]["match"] is False
    assert results[0]["cobol"] == "00020\n"
    assert results[0]["python"] == "20\n"


# --------------------------------------------------------------------------
# load_golden_fallback  (pre-captured COBOL I/O pairs)
# --------------------------------------------------------------------------
def test_load_golden_fallback_returns_pairs(tmp_path):
    p = tmp_path / "golden.json"
    p.write_text(json.dumps({"cases": [{"input": "1\n", "cobol": "00002\n"}]}))
    data = oracle.load_golden_fallback(str(p))
    assert data["cases"][0]["cobol"] == "00002\n"


def test_load_golden_fallback_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        oracle.load_golden_fallback("/nonexistent/golden_io.json")


def test_shipped_golden_io_is_wellformed(repo_root):
    """The real demo fallback must parse and carry input/cobol pairs."""
    data = oracle.load_golden_fallback(str(repo_root / "src/sample/golden_io.json"))
    assert data["cases"], "golden_io.json has no cases"
    for case in data["cases"]:
        assert "input" in case and "cobol" in case
        assert case["cobol"], "captured COBOL output must be non-empty"


# --------------------------------------------------------------------------
# C5 — explicit comparison normalization (document the exact byte contract)
# --------------------------------------------------------------------------
def test_normalize_default_is_identity_preserving_trailing_newline():
    """Default comparison is strict byte-for-byte: trailing newline preserved."""
    assert oracle.normalize("0000775.00\n") == "0000775.00\n"


def test_normalize_can_strip_trailing_newline_when_asked():
    """Documented opt-in: strip the trailing newline on BOTH sides if a caller wants
    to ignore line-ending differences. Must be explicit, never silent."""
    assert oracle.normalize("0000775.00\n", strip_newline=True) == "0000775.00"
    assert oracle.normalize("0000775.00", strip_newline=True) == "0000775.00"


def test_differential_test_golden_respects_strip_newline(fixtures_dir, tmp_path):
    """A Python translation missing ONLY the trailing newline matches under
    strip_newline=True but FAILS under the default strict compare (C5: the rule is
    explicit and the demo can choose strict)."""
    golden = tmp_path / "golden.json"
    golden.write_text(json.dumps({"cases": [{"input": "10\n", "cobol": "00020\n"}]}))
    no_nl = tmp_path / "no_newline.py"
    no_nl.write_text("import sys\n"
                     "n=int(float(sys.stdin.readline().strip()))\n"
                     "sys.stdout.write(f'{n*2:05d}')\n")  # no trailing newline
    strict = oracle.differential_test_golden(str(no_nl), str(golden))
    assert strict[0]["match"] is False                      # strict: newline matters
    lenient = oracle.differential_test_golden(str(no_nl), str(golden), strip_newline=True)
    assert lenient[0]["match"] is True                      # opt-in lenient


# --------------------------------------------------------------------------
# C5 — battery curation invariants (curated to avoid overflow/sign/garbage RED)
# --------------------------------------------------------------------------
def test_shipped_battery_is_curated(repo_root):
    """C5: the shipped golden battery must stay within the demo-safe envelope —
    non-negative, <= 9999999.99 (PIC 9(7)V99), clean numeric, trailing newline.
    Adding an overflow/negative/garbage input would silently break the demo."""
    data = oracle.load_golden_fallback(str(repo_root / "src/sample/golden_io.json"))
    inputs = [c["input"] for c in data["cases"]]
    # validate_battery raises with a clear message on any out-of-envelope input
    oracle.validate_battery(inputs)


def test_validate_battery_rejects_overflow_negative_and_garbage():
    import pytest as _pytest
    with _pytest.raises(ValueError):
        oracle.validate_battery(["12345678.99\n"])   # > 9999999.99 overflow
    with _pytest.raises(ValueError):
        oracle.validate_battery(["-100.00\n"])       # negative (unsigned field)
    with _pytest.raises(ValueError):
        oracle.validate_battery(["abc\n"])           # non-numeric garbage
    with _pytest.raises(ValueError):
        oracle.validate_battery(["100.00"])          # missing trailing newline
    # a clean battery passes and returns the inputs
    assert oracle.validate_battery(["1000.00\n", "0.01\n"]) == ["1000.00\n", "0.01\n"]


# --------------------------------------------------------------------------
# differential_test_golden  (Python-vs-golden, the no-cobc demo path)
# --------------------------------------------------------------------------
def test_differential_test_golden_passes_for_correct_translation(fixtures_dir, tmp_path):
    golden = tmp_path / "golden.json"
    golden.write_text(json.dumps({"cases": [
        {"input": "1\n", "cobol": "00002\n"},
        {"input": "10\n", "cobol": "00020\n"},
    ]}))
    results = oracle.differential_test_golden(
        str(fixtures_dir / "twice_correct.py"), str(golden)
    )
    assert all(r["match"] for r in results)
    assert [r["input"] for r in results] == ["1\n", "10\n"]


def test_differential_test_golden_flags_wrong_translation(fixtures_dir, tmp_path):
    golden = tmp_path / "golden.json"
    golden.write_text(json.dumps({"cases": [{"input": "10\n", "cobol": "00020\n"}]}))
    results = oracle.differential_test_golden(
        str(fixtures_dir / "twice_wrong.py"), str(golden)
    )
    assert results[0]["match"] is False
    assert results[0]["cobol"] == "00020\n"
    assert results[0]["python"] == "20\n"


# --------------------------------------------------------------------------
# reference payroll.py  (known-good Python baseline for the demo + run())
# --------------------------------------------------------------------------
def test_reference_payroll_py_matches_golden(repo_root):
    """The shipped reference translation must be byte-for-byte equivalent to the
    captured COBOL outputs across the full input battery — including the
    half-up rounding-tie cases that a naive round() would get wrong."""
    results = oracle.differential_test_golden(
        str(repo_root / "src/sample/payroll.py"),
        str(repo_root / "src/sample/golden_io.json"),
    )
    failures = [r for r in results if not r["match"]]
    assert not failures, f"reference payroll.py diverges from COBOL: {failures}"


# --------------------------------------------------------------------------
# second sample: interest.cob — DIFFERENT idiom (truncation, not rounding).
# golden is REAL GnuCOBOL output (src/sample/build_samples.sh re-captures it).
# --------------------------------------------------------------------------
def test_interest_golden_io_is_wellformed(repo_root):
    data = oracle.load_golden_fallback(str(repo_root / "src/sample/interest_golden_io.json"))
    assert data["cases"], "interest_golden_io.json has no cases"
    assert "REAL" in data["capture_status"]            # honesty bar: not fabricated
    for case in data["cases"]:
        assert case["input"] and case["cobol"], "each case needs real input + cobol bytes"


def test_reference_interest_py_matches_golden(repo_root):
    """The reference interest.py (ROUND_DOWN/truncation) must be byte-for-byte equivalent
    to the captured REAL cobc outputs — proving the truncation idiom is handled."""
    results = oracle.differential_test_golden(
        str(repo_root / "src/sample/interest.py"),
        str(repo_root / "src/sample/interest_golden_io.json"),
    )
    failures = [r for r in results if not r["match"]]
    assert not failures, f"reference interest.py diverges from COBOL: {failures}"


def test_interest_sample_is_a_different_idiom_from_payroll(repo_root, tmp_path):
    """The interest sample must actually TEST something: a naive round()-based port (the
    payroll-style fix) FAILS the interest diff, because interest.cob TRUNCATES (no ROUNDED).
    This proves the second sample exercises a genuinely different idiom, not a duplicate."""
    naive = tmp_path / "interest_naive.py"
    naive.write_text(
        "import sys\n"
        "from decimal import Decimal, ROUND_HALF_UP\n"
        "RATE = Decimal('0.0375'); CENT = Decimal('0.01')\n"
        "raw = sys.stdin.readline().strip()\n"
        "p = Decimal(raw) if raw else Decimal(0)\n"
        "i = (p * RATE).quantize(CENT, rounding=ROUND_HALF_UP)\n"   # rounds, doesn't truncate
        "ip = int(abs(i)); fp = int((abs(i) - ip) * 100)\n"
        "print(f'{ip:07d}.{fp:02d}')\n"
    )
    results = oracle.differential_test_golden(
        str(naive), str(repo_root / "src/sample/interest_golden_io.json"))
    failures = [r for r in results if not r["match"]]
    assert failures, "a naive round() port should FAIL the truncation diff (else the sample tests nothing)"
    # the documented proof cases must be among the failures
    failed_inputs = {r["input"].strip() for r in failures}
    assert {"1.00", "13.33", "50000.50"} <= failed_inputs


# --------------------------------------------------------------------------
# prove_equivalence  (PRIMARY path — golden is ground truth, NO compiler needed)
# --------------------------------------------------------------------------
def test_prove_equivalence_uses_golden_as_ground_truth(repo_root):
    """The PRIMARY oracle path diffs Python against the pre-captured golden bytes.
    It must NOT require a live compiler — golden_io.json IS the ground truth."""
    results = oracle.prove_equivalence(
        str(repo_root / "src/sample/payroll.py"),
        str(repo_root / "src/sample/golden_io.json"),
    )
    assert results, "no cases proven"
    assert all(r["match"] for r in results)


def test_prove_equivalence_does_not_call_a_compiler(repo_root, monkeypatch):
    """Guard: prove_equivalence must never shell out to cobc / compile anything."""
    def _boom(*a, **k):
        raise AssertionError("prove_equivalence must not invoke the compiler")
    monkeypatch.setattr(oracle, "compile_cobol", _boom)
    results = oracle.prove_equivalence(
        str(repo_root / "src/sample/payroll.py"),
        str(repo_root / "src/sample/golden_io.json"),
    )
    assert all(r["match"] for r in results)


def test_run_returns_results_and_path_used(repo_root):
    """run() returns (results, path_used); with no binary it defaults to golden."""
    golden = str(repo_root / "src/sample/golden_io.json")
    results, path_used = oracle.run(str(repo_root / "src/sample/payroll.py"), golden)
    assert path_used == "golden"
    assert results and all(r["match"] for r in results)


# --------------------------------------------------------------------------
# verify_golden_against_binary  (freshness check — live cobc OR mounted binary)
# --------------------------------------------------------------------------
@requires_cobc
def test_verify_golden_against_binary_passes_for_fresh_capture(repo_root, tmp_path):
    """An opportunistic freshness check: a runnable COBOL binary (live-compiled or
    mounted) re-runs the golden inputs and confirms the captured bytes still match."""
    binary = oracle.compile_cobol(
        str(repo_root / "src/sample/payroll.cob"), str(tmp_path / "payroll")
    )
    report = oracle.verify_golden_against_binary(
        str(repo_root / "src/sample/golden_io.json"), binary
    )
    assert report and all(row["fresh"] for row in report)
    for row in report:
        assert set(row) >= {"input", "captured", "live", "fresh"}


def test_verify_golden_against_binary_flags_stale_capture(fixtures_dir, tmp_path):
    """If the binary's real output diverges from the captured bytes, mark it stale."""
    import shutil
    if shutil.which("cobc") is None:
        pytest.skip("cobc not installed")
    binary = oracle.compile_cobol(str(fixtures_dir / "twice.cob"), str(tmp_path / "tw"))
    bad_golden = tmp_path / "golden.json"
    bad_golden.write_text(json.dumps({"cases": [
        {"input": "10\n", "cobol": "99999\n"},  # deliberately wrong capture
    ]}))
    report = oracle.verify_golden_against_binary(str(bad_golden), binary)
    assert report[0]["fresh"] is False
    assert report[0]["captured"] == "99999\n"
    assert report[0]["live"] == "00020\n"


def test_run_binary_accepts_arbitrary_mounted_path(fixtures_dir, tmp_path):
    """run_binary points at ANY binary path (the mounted pre-compiled binary path),
    not a hardcoded location."""
    import shutil
    if shutil.which("cobc") is None:
        pytest.skip("cobc not installed")
    mounted = tmp_path / "subdir" / "payroll_linux"   # arbitrary 'mounted' location
    mounted.parent.mkdir()
    oracle.compile_cobol(str(fixtures_dir / "twice.cob"), str(mounted))
    assert oracle.run_binary(str(mounted), "21\n") == "00042\n"


def test_shipped_golden_io_matches_live_cobc_when_available(repo_root, tmp_path):
    """If cobc is present, the shipped golden_io.json must equal a live recompile
    of payroll.cob — proving the fallback is a faithful capture, not stale."""
    import shutil
    if shutil.which("cobc") is None:
        pytest.skip("cobc not installed; cannot revalidate golden capture")
    data = oracle.load_golden_fallback(str(repo_root / "src/sample/golden_io.json"))
    binary = oracle.compile_cobol(
        str(repo_root / "src/sample/payroll.cob"), str(tmp_path / "payroll")
    )
    for case in data["cases"]:
        live = oracle.run_binary(binary, case["input"])
        assert live == case["cobol"], (
            f"golden capture stale for input {case['input']!r}: "
            f"shipped={case['cobol']!r} live={live!r}"
        )


# --------------------------------------------------------------------------
# Option B PRIMARY — run a REAL pre-compiled binary live; auto-fall-back to golden
# --------------------------------------------------------------------------
@requires_cobc
def test_run_binary_accepts_lib_dir_for_bundled_libcob(fixtures_dir, tmp_path):
    """Recipe A bundles the binary with a lib/ dir run via LD_LIBRARY_PATH. run_binary
    must accept a lib_dir and put it on LD_LIBRARY_PATH for the child process."""
    binary = oracle.compile_cobol(str(fixtures_dir / "twice.cob"), str(tmp_path / "tw"))
    # an empty lib dir is harmless here; we only assert the kwarg is honored + runs
    libdir = tmp_path / "lib"
    libdir.mkdir()
    assert oracle.run_binary(binary, "10\n", lib_dir=str(libdir)) == "00020\n"


@requires_cobc
def test_run_binary_times_out(fixtures_dir, tmp_path):
    """A hung binary must raise TimeoutExpired so the caller can fall back."""
    import subprocess
    # a tiny shell 'binary' that sleeps longer than the timeout
    slow = tmp_path / "slow.sh"
    slow.write_text("#!/bin/sh\nsleep 5\n")
    slow.chmod(0o755)
    with pytest.raises(subprocess.TimeoutExpired):
        oracle.run_binary(str(slow), "x\n", timeout=0.5)


@requires_cobc
def test_differential_test_binary_uses_live_binary_as_ground_truth(repo_root, tmp_path):
    """Option B: diff the Python translation against the LIVE binary's real output,
    over the golden battery inputs. Correct payroll.py matches 10/10."""
    binary = oracle.compile_cobol(
        str(repo_root / "src/sample/payroll.cob"), str(tmp_path / "payroll")
    )
    results = oracle.differential_test_binary(
        str(repo_root / "src/sample/payroll.py"),
        binary,
        str(repo_root / "src/sample/golden_io.json"),
    )
    assert results and all(r["match"] for r in results)
    for r in results:
        assert set(r) >= {"input", "cobol", "python", "match"}


def test_run_falls_back_to_golden_when_no_binary(repo_root):
    """Option B primary with NO binary available -> transparent golden fallback,
    same diff records. Reports which path was used."""
    results, path_used = oracle.run(
        str(repo_root / "src/sample/payroll.py"),
        golden_path=str(repo_root / "src/sample/golden_io.json"),
        binary=None,
    )
    assert path_used == "golden"
    assert results and all(r["match"] for r in results)


@requires_cobc
def test_run_uses_binary_when_present(repo_root, tmp_path):
    """Option B primary: a runnable binary present -> live binary is ground truth."""
    binary = oracle.compile_cobol(
        str(repo_root / "src/sample/payroll.cob"), str(tmp_path / "payroll")
    )
    results, path_used = oracle.run(
        str(repo_root / "src/sample/payroll.py"),
        golden_path=str(repo_root / "src/sample/golden_io.json"),
        binary=binary,
    )
    assert path_used == "binary"
    assert results and all(r["match"] for r in results)


def test_run_auto_falls_back_when_binary_stalls(repo_root, tmp_path):
    """C-resilience: if the live binary stalls past the timeout, run() must
    transparently fall back to golden_io.json (not hang the demo)."""
    slow = tmp_path / "slow.sh"
    slow.write_text("#!/bin/sh\nsleep 10\n")
    slow.chmod(0o755)
    results, path_used = oracle.run(
        str(repo_root / "src/sample/payroll.py"),
        golden_path=str(repo_root / "src/sample/golden_io.json"),
        binary=str(slow),
        binary_timeout=0.5,
    )
    assert path_used == "golden"           # fell back, did not hang
    assert results and all(r["match"] for r in results)


def test_run_auto_falls_back_when_binary_errors(repo_root, tmp_path):
    """If the live binary errors (e.g. missing libcob / noexec), fall back to golden."""
    broken = tmp_path / "broken.sh"
    broken.write_text("#!/bin/sh\nexit 3\n")
    broken.chmod(0o755)
    results, path_used = oracle.run(
        str(repo_root / "src/sample/payroll.py"),
        golden_path=str(repo_root / "src/sample/golden_io.json"),
        binary=str(broken),
    )
    assert path_used == "golden"
    assert results and all(r["match"] for r in results)
