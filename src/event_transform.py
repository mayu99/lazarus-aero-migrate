"""
LAZARUS — transform the agent's raw tool output into CANONICAL UI events.

server.py forwards the agent's live `step.*` stream as `step` events directly, but
the seven SEMANTIC panels (business_rule, diff, pytest, oracle, forge, reload,
download) are DERIVED from the agent's tool outputs, not from raw interaction.steps
(web/STREAM_CONTRACT.md). This module holds the pure, unit-testable derivations.

Contract with the agent: to make the richest panels deterministic instead of
scraping prose, the agent emits machine-readable marker lines in its output:
  - `LAZARUS_ORACLE_JSON: [{"input","cobol","python","match"}, ...]`  (the diff!)
  - `LAZARUS_RULE: {"title","plain","cobol_ref"?,"severity"?}`        (one per rule)
We parse those when present; everything degrades gracefully when they're absent.
"""
from __future__ import annotations

import json
import pathlib
import re

_ORACLE_MARKER = "LAZARUS_ORACLE_JSON:"
_RULE_MARKER = "LAZARUS_RULE:"

# Progressive-phase detection: map the agent's live step text to a canonical phase so
# the UI rail advances DURING the run, not only at the end. Ordered most-specific first;
# the first pattern that matches a line wins. Phases match web/renderer.js PHASES.
_PHASE_PATTERNS: list[tuple[str, "re.Pattern[str]"]] = [
    # forge/forged/forges/forging as a verb, but NOT preceded by a hyphen/word char, so
    # "conda-forge" (the gnucobol install channel — that's the ORACLE beat) doesn't wrongly
    # trip the FORGE rail. The .agents/skills/ + SKILL.md paths are unambiguous either way.
    ("forge", re.compile(r"\.agents/skills/|SKILL\.md|(?<![-\w])forg(e|ed|es|ing)\b", re.I)),
    ("reload", re.compile(r"re-?read|re-?load|reusing (the )?environment", re.I)),
    ("test", re.compile(r"\bpytest\b|equivalence test|byte[\s-]for[\s-]byte|\d+\s+(passed|failed)", re.I)),
    ("oracle", re.compile(r"\bcobc\b|gnucobol|micromamba|differential oracle|golden_io|compil", re.I)),
    ("translate", re.compile(r"payroll\.py|writ(e|ing)\s+(the\s+)?python|translat", re.I)),
    ("recover", re.compile(r"business rule|recover|archaeolog|plain english", re.I)),
    ("ingest", re.compile(r"read(ing)?\s+(the\s+)?cobol|provision|ingest|sandbox", re.I)),
]


def _parse_marker_payloads(text: str, marker: str) -> list:
    """Return the parsed JSON payload after each `marker` line; skip malformed ones."""
    out = []
    for line in text.splitlines():
        idx = line.find(marker)
        if idx == -1:
            continue
        payload = line[idx + len(marker):].strip()
        try:
            out.append(json.loads(payload))
        except (json.JSONDecodeError, ValueError):
            continue
    return out


def parse_oracle_records(text: str) -> list[dict]:
    """Extract the differential-oracle records ({input,cobol,python,match}) the agent
    printed via the LAZARUS_ORACLE_JSON marker. Returns [] if absent/malformed."""
    records: list[dict] = []
    for payload in _parse_marker_payloads(text, _ORACLE_MARKER):
        if isinstance(payload, list):
            records.extend(r for r in payload if isinstance(r, dict))
        elif isinstance(payload, dict):
            records.append(payload)
    return records


def _case_name(record: dict) -> str:
    inp = (record.get("input") or "").strip()
    return f"test_equivalence[{inp}]"


def _mismatch_message(record: dict) -> str:
    return (
        "AssertionError: byte mismatch — COBOL "
        f"{record.get('cobol')!r} != Python {record.get('python')!r} "
        "(COBOL DISPLAY de-editing + ROUND-HALF-UP)"
    )


def to_pytest_event(records: list[dict], iteration: int = 1) -> dict:
    """Build the canonical `pytest` event with STRUCTURED per-case cobol-vs-python
    values (the #1 demo money shot), from the oracle records."""
    cases = []
    passed = failed = 0
    for r in records:
        ok = bool(r.get("match"))
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
        case = {
            "name": _case_name(r),
            "status": "pass" if ok else "fail",
            "cobol": r.get("cobol"),
            "python": r.get("python"),
        }
        if not ok:
            case["message"] = _mismatch_message(r)
        cases.append(case)
    result = "green" if failed == 0 and cases else ("red" if failed else "green")
    summary = (f"{passed} passed, {failed} failed" if failed == 0
               else f"{failed} failed, {passed} passed")
    return {
        "type": "pytest",
        "result": result,
        "iteration": iteration,
        "summary": summary,
        "cases": cases,
        "source": "agent_pytest",  # the agent's OWN per-case oracle (LAZARUS_ORACLE_JSON);
                                    # oracle_harness_pytest_event() overrides this for the
                                    # orchestrator's local differential-oracle run.
    }


def oracle_event(golden_path: str) -> dict:
    """The differential-oracle banner: real compiler + the input battery, from the
    golden capture (real cobc output, available offline)."""
    data = json.loads(pathlib.Path(golden_path).read_text())
    return {
        "type": "oracle",
        "compiler": data.get("captured_with", "GnuCOBOL cobc"),
        "inputs": [(c.get("input") or "").strip() for c in data.get("cases", [])],
        "note": "Canonical outputs captured from the original COBOL binary (ground truth).",
    }


def business_rules_from_text(text: str) -> list[dict]:
    """Recovered business rules (the archaeology panel) from LAZARUS_RULE markers."""
    rules = []
    for payload in _parse_marker_payloads(text, _RULE_MARKER):
        if not isinstance(payload, dict):
            continue
        rule = {"type": "business_rule"}
        rule.update(payload)
        rules.append(rule)
    return rules


def phase_for_text(text: str) -> str | None:
    """Map one chunk of the agent's live step text to a canonical phase, or None.

    Used by server.py to advance the UI's phase rail PROGRESSIVELY off the streamed
    `step.delta` text — so the journey shows ingest->recover->translate->oracle->test->
    forge live, instead of jumping straight to the terminal verdict. Best-effort: returns
    None when no milestone keyword is present (the caller simply doesn't emit a phase).
    """
    for phase, pat in _PHASE_PATTERNS:
        if pat.search(text):
            return phase
    return None


_MODULE_MARKER = "LAZARUS_MODULE:"


def python_module_from_output(text: str) -> str | None:
    """Recover the agent's COMPLETE payroll.py source from its model output — the PRIMARY,
    tarball-independent module source (the Files-API whole-env tarball can hang past the demo
    budget; qa saw 180s+ never return). This is the agent's REAL written code, echoed in its
    own output — not invented.

    Resolution order:
      1. DETERMINISTIC: the explicit `LAZARUS_MODULE:` marker the agent is instructed to print
         exactly once, immediately followed by a single fenced ```python block holding the
         whole final module (agent.py prompt + .agents/AGENTS.md). Preferred — unambiguous.
      2. FALLBACK: the LARGEST python-ish fenced block that looks like a real module (has an
         import / def / class / print and >=5 lines), for runs where the marker is absent.
    Returns the module text (fences stripped), or None if nothing qualifies.
    """
    # 1. Explicit marker: `LAZARUS_MODULE:` then the next fenced block (optionally on the
    #    same or following lines). This is the deterministic path.
    idx = text.find(_MODULE_MARKER)
    if idx != -1:
        after = text[idx + len(_MODULE_MARKER):]
        m = re.search(r"```(?:python|py)?\s*\n(.*?)```", after, re.S)
        if m:
            body = m.group(1).strip("\n")
            if body.strip():
                return body

    # 2. Fallback: the largest module-shaped fenced python block anywhere in the output.
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    best = None
    for block in blocks:
        body = block.strip("\n")
        lines = body.splitlines()
        looks_like_module = (
            len(lines) >= 5
            and re.search(r"^\s*(import |from .+ import |def |class |print\()", body, re.M)
        )
        if looks_like_module and (best is None or len(body) > len(best)):
            best = body
    return best


def diff_event(cobol_src: str, python_src: str, *,
               cobol_name: str = "payroll.cob", python_name: str = "payroll.py") -> dict:
    """Build the canonical `diff` event: original COBOL (left) vs the agent's Python (right).

    This is emitted from REAL sources — the COBOL the user submitted and the payroll.py the
    agent actually wrote (fetched via the Files API) — so the side-by-side viewer populates
    even when the agent never printed a marker.
    """
    return {
        "type": "diff",
        "left": {"lang": "cobol", "name": cobol_name, "code": cobol_src},
        "right": {"lang": "python", "name": python_name, "code": python_src},
    }


def oracle_harness_pytest_event(records: list[dict], iteration: int = 1) -> dict:
    """Structured per-case pytest event from the ORCHESTRATOR's differential-oracle run.

    Same shape as to_pytest_event (per-case cobol-vs-python bytes), but each case name is
    labeled `oracle_equivalence[...]` and the summary names the harness — because these
    records come from src/differential_oracle.py running the agent's payroll.py against the
    real-cobc golden bytes, NOT from the agent's own pytest stdout. Truthful labeling keeps
    the demo honest (the diff is real either way; we just don't claim it as the agent's test).
    """
    ev = to_pytest_event(records, iteration=iteration)
    for case in ev["cases"]:
        inp = case["name"][case["name"].find("[") + 1: case["name"].rfind("]")]
        case["name"] = f"oracle_equivalence[{inp}]"
    ev["source"] = "differential_oracle"
    ev["summary"] = f"{ev['summary']} (differential oracle: agent python vs real-cobc golden bytes)"
    return ev


# A faithful-but-deterministic set of recovered rules for the payroll module, used ONLY as
# the fallback when the agent emitted no LAZARUS_RULE markers. These are the actual rules of
# src/sample/payroll.cob (see golden_io.json business_rule note), not invented chatter — the
# UI never sits empty, and what it shows is true of the module under migration.
_PAYROLL_FALLBACK_RULES: list[dict] = [
    {
        "type": "business_rule",
        "title": "Progressive tax withholding",
        "plain": "22.5% of gross pay is withheld as tax; net = gross - tax.",
        "cobol_ref": "COMPUTE WS-TAX ROUNDED = WS-GROSS-PAY * 0.225",
        "severity": "rule",
    },
    {
        "type": "business_rule",
        "title": "Half-up rounding (not banker's)",
        "plain": "COBOL ROUNDED rounds half-up. Python's default round() is banker's "
                 "rounding, so a naive port diverges on ties (e.g. 1.00 -> 0.77 vs 0.78).",
        "cobol_ref": "COMPUTE ... ROUNDED  ==>  Decimal.quantize(ROUND_HALF_UP)",
        "severity": "gotcha",
    },
    {
        "type": "business_rule",
        "title": "Fixed-width zero-padded DISPLAY",
        "plain": "Net is rendered as PIC 9(7)V99: 7 integer digits + 2 decimals, zero-padded, "
                 "unsigned, with a trailing newline — the exact bytes the diff compares.",
        "cobol_ref": "01 WS-NET-PAY PIC 9(7)V99.  DISPLAY WS-NET-PAY",
        "severity": "edge_case",
    },
]


def business_rules_fallback() -> list[dict]:
    """Deterministic recovered-rules fallback for the payroll module (>=3 rules).

    Returned only when business_rules_from_text() found no LAZARUS_RULE markers, so the
    archaeology panel never sits empty on the live path. These are the real rules of the
    sample module, copied (not paraphrased loosely) so the panel stays truthful.
    """
    return [dict(r) for r in _PAYROLL_FALLBACK_RULES]
