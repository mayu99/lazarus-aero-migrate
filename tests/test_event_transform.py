"""Tests for src/event_transform.py — turning the agent's raw tool output into the
CANONICAL UI events (web/STREAM_CONTRACT.md). The #1 money shot is structured
per-case pytest results carrying the COBOL-vs-Python byte values, NOT raw stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
for p in (str(SRC_DIR), str(REPO_ROOT)):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

import event_transform as et


# --------------------------------------------------------------------------
# parse_oracle_records — pull the structured {input,cobol,python,match} list out
# of the agent's output (it prints a LAZARUS_ORACLE_JSON: marker line)
# --------------------------------------------------------------------------
def test_parse_oracle_records_from_marker_line():
    out = (
        "...agent chatter...\n"
        'LAZARUS_ORACLE_JSON: [{"input": "1.00\\n", "cobol": "0000000.77\\n", '
        '"python": "0000000.78\\n", "match": false}]\n'
        "...more chatter...\n"
    )
    records = et.parse_oracle_records(out)
    assert len(records) == 1
    assert records[0]["cobol"] == "0000000.77\n"
    assert records[0]["python"] == "0000000.78\n"
    assert records[0]["match"] is False


def test_parse_oracle_records_returns_empty_when_absent():
    assert et.parse_oracle_records("no marker here, just prose") == []


def test_parse_oracle_records_ignores_malformed_json():
    assert et.parse_oracle_records("LAZARUS_ORACLE_JSON: {not valid json") == []


# --------------------------------------------------------------------------
# to_pytest_event — structured cases (the money shot)
# --------------------------------------------------------------------------
def test_to_pytest_event_red_with_per_case_cobol_vs_python():
    records = [
        {"input": "1.00\n", "cobol": "0000000.77\n", "python": "0000000.78\n", "match": False},
        {"input": "1000.00\n", "cobol": "0000775.00\n", "python": "0000775.00\n", "match": True},
    ]
    ev = et.to_pytest_event(records, iteration=1)
    assert ev["type"] == "pytest"
    assert ev["result"] == "red"          # at least one mismatch
    assert ev["iteration"] == 1
    assert ev["summary"] == "1 failed, 1 passed"
    assert len(ev["cases"]) == 2
    c0 = ev["cases"][0]
    assert c0["status"] == "fail"
    assert c0["cobol"] == "0000000.77\n" and c0["python"] == "0000000.78\n"
    assert "1.00" in c0["name"]
    assert c0["message"]                  # non-empty mismatch explanation
    assert ev["cases"][1]["status"] == "pass"


def test_to_pytest_event_green_when_all_match():
    records = [
        {"input": "1000.00\n", "cobol": "0000775.00\n", "python": "0000775.00\n", "match": True},
    ]
    ev = et.to_pytest_event(records, iteration=2)
    assert ev["result"] == "green"
    assert ev["summary"] == "1 passed, 0 failed"
    assert all(c["status"] == "pass" for c in ev["cases"])


def test_to_pytest_event_labels_agent_source():
    """The agent's own per-case oracle (from LAZARUS_ORACLE_JSON) is labeled
    source='agent_pytest', so the UI distinguishes it from the orchestrator's harness."""
    records = [{"input": "1000.00\n", "cobol": "0000775.00\n",
                "python": "0000775.00\n", "match": True}]
    assert et.to_pytest_event(records)["source"] == "agent_pytest"


# --------------------------------------------------------------------------
# oracle_event — the differential-oracle banner (real compiler + inputs)
# --------------------------------------------------------------------------
def test_oracle_event_from_golden(tmp_path):
    golden = tmp_path / "golden.json"
    golden.write_text(json.dumps({
        "program": "payroll.cob",
        "captured_with": "GnuCOBOL 3.2.0 (cobc -x), 2026-05-23",
        "cases": [{"input": "1000.00\n", "cobol": "0000775.00\n"},
                  {"input": "0.01\n", "cobol": "0000000.01\n"}],
    }))
    ev = et.oracle_event(str(golden))
    assert ev["type"] == "oracle"
    assert "GnuCOBOL" in ev["compiler"]
    assert ev["inputs"] == ["1000.00", "0.01"]   # newline-stripped, display-ready
    assert ev["note"]


# --------------------------------------------------------------------------
# python_module_from_output — resilience fallback when the tarball fetch fails
# --------------------------------------------------------------------------
def test_python_module_from_output_extracts_fenced_block():
    out = ("Here's the migration:\n\n```python\n"
           "import sys\nfrom decimal import Decimal\n\ndef main():\n    print('ok')\n"
           "\nif __name__ == '__main__':\n    main()\n```\nDone.")
    mod = et.python_module_from_output(out)
    assert mod is not None
    assert mod.startswith("import sys") and "def main()" in mod
    assert "```" not in mod              # fences stripped


def test_python_module_from_output_picks_largest_real_module():
    out = ("```python\nx = 1\n```\n"                       # too short, not a module
           "```python\nimport os\ndef f():\n    return 1\nclass C:\n    pass\nprint(f())\n```")
    mod = et.python_module_from_output(out)
    assert mod is not None and "class C" in mod            # the substantial block wins


def test_python_module_from_output_none_without_code_block():
    assert et.python_module_from_output("I finished. All tests pass. No code here.") is None
    # a fenced block that isn't a module (no import/def/class/print, too short) -> None
    assert et.python_module_from_output("```\njust prose\nin a block\n```") is None


def test_python_module_from_output_prefers_lazarus_module_marker():
    """The explicit LAZARUS_MODULE: marker block is the deterministic source — it wins even
    over a larger generic python block elsewhere in the output."""
    out = (
        "```python\nimport os\ndef helper():\n    return 1\nclass Big:\n    pass\n"
        "print('a much larger but UNMARKED block that should NOT be chosen')\n```\n\n"
        "LAZARUS_MODULE:\n```python\n"
        "from decimal import Decimal\ndef payroll():\n    return Decimal('1')\nprint(payroll())\n"
        "```\n"
    )
    mod = et.python_module_from_output(out)
    assert mod is not None
    assert "def payroll()" in mod                   # the MARKED block, not the bigger one
    assert "def helper()" not in mod


def test_python_module_from_output_marker_block_can_be_short():
    """Under the explicit marker we trust the agent — even a short module is accepted (the
    >=5-line heuristic only guards the unmarked fallback)."""
    out = "LAZARUS_MODULE:\n```python\nprint('hi')\n```\n"
    assert et.python_module_from_output(out) == "print('hi')"


# --------------------------------------------------------------------------
# business_rules_from_text — recovered rules for the archaeology panel
# --------------------------------------------------------------------------
def test_business_rules_from_marker_lines():
    out = (
        "LAZARUS_RULE: {\"title\": \"Progressive tax\", \"plain\": \"22.5% withheld\", "
        "\"cobol_ref\": \"COMPUTE WS-TAX ROUNDED\", \"severity\": \"rule\"}\n"
        "LAZARUS_RULE: {\"title\": \"Half-up rounding\", \"plain\": \"ROUNDED is half-up\", "
        "\"severity\": \"gotcha\"}\n"
    )
    rules = et.business_rules_from_text(out)
    assert len(rules) == 2
    assert rules[0]["type"] == "business_rule"
    assert rules[0]["title"] == "Progressive tax"
    assert rules[1]["severity"] == "gotcha"


def test_business_rules_empty_when_absent():
    assert et.business_rules_from_text("no rules emitted") == []


# --------------------------------------------------------------------------
# business_rules_fallback — deterministic >=3 rules when markers are absent
# --------------------------------------------------------------------------
def test_business_rules_fallback_has_at_least_three_typed_rules():
    rules = et.business_rules_fallback()
    assert len(rules) >= 3
    assert all(r["type"] == "business_rule" for r in rules)
    assert all(r.get("title") and r.get("plain") and r.get("cobol_ref") for r in rules)
    # the rounding gotcha (the demo's whole point) must be present
    assert any(r["severity"] == "gotcha" for r in rules)
    assert any("half-up" in r["plain"].lower() or "ROUND_HALF_UP" in r["cobol_ref"]
               for r in rules)


def test_business_rules_fallback_returns_independent_copies():
    a = et.business_rules_fallback()
    a[0]["title"] = "mutated"
    assert et.business_rules_fallback()[0]["title"] != "mutated"


# --------------------------------------------------------------------------
# phase_for_text — progressive-phase milestone detection
# --------------------------------------------------------------------------
def test_phase_for_text_maps_milestones():
    assert et.phase_for_text("Reading the COBOL source, provisioning sandbox") == "ingest"
    assert et.phase_for_text("Recovering the business rules in plain English") == "recover"
    assert et.phase_for_text("Writing payroll.py now") == "translate"
    assert et.phase_for_text("Compiling with cobc / micromamba gnucobol") == "oracle"
    assert et.phase_for_text("Running pytest: 10 passed") == "test"
    assert et.phase_for_text(".agents/skills/foo/SKILL.md written") == "forge"


def test_phase_for_text_none_on_plain_chatter():
    assert et.phase_for_text("hmm let me think about this") is None


def test_phase_for_text_conda_forge_is_oracle_not_forge():
    """Regression: 'conda-forge' (the gnucobol install channel) is the ORACLE beat, not
    FORGE — the forge pattern must not match 'forge' inside 'conda-forge'. This matters now
    that tool breadcrumbs surface the literal install command to phase_for_text."""
    assert et.phase_for_text("$ micromamba install -c conda-forge gnucobol") == "oracle"
    # real forge verbs/paths still detected
    assert et.phase_for_text("Forged a new skill") == "forge"
    assert et.phase_for_text("forging .agents/skills/x/SKILL.md") == "forge"


# --------------------------------------------------------------------------
# diff_event — COBOL<->Python side-by-side from real sources
# --------------------------------------------------------------------------
def test_diff_event_carries_both_sides():
    ev = et.diff_event("IDENTIFICATION DIVISION.", "print('hi')",
                       cobol_name="payroll.cob", python_name="payroll.py")
    assert ev["type"] == "diff"
    assert ev["left"] == {"lang": "cobol", "name": "payroll.cob",
                          "code": "IDENTIFICATION DIVISION."}
    assert ev["right"] == {"lang": "python", "name": "payroll.py",
                           "code": "print('hi')"}


# --------------------------------------------------------------------------
# oracle_harness_pytest_event — truthful labeling of the orchestrator's run
# --------------------------------------------------------------------------
def test_oracle_harness_pytest_event_labels_source_and_cases():
    records = [
        {"input": "1.00\n", "cobol": "0000000.77\n", "python": "0000000.78\n", "match": False},
        {"input": "1000.00\n", "cobol": "0000775.00\n", "python": "0000775.00\n", "match": True},
    ]
    ev = et.oracle_harness_pytest_event(records, iteration=1)
    assert ev["type"] == "pytest"
    assert ev["source"] == "differential_oracle"          # not the agent's own pytest
    assert ev["result"] == "red"
    assert all(c["name"].startswith("oracle_equivalence[") for c in ev["cases"])
    assert "differential oracle" in ev["summary"]
    # the per-case bytes survive (the diff is still real)
    fail = next(c for c in ev["cases"] if c["status"] == "fail")
    assert fail["cobol"] == "0000000.77\n" and fail["python"] == "0000000.78\n"
