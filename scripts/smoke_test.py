#!/usr/bin/env python3
"""
LAZARUS — live-path smoke test (run the INSTANT the hackathon key is provisioned).

This is the fastest way to find out what the real Gemini Managed Agents API
actually does on the day. It exercises the entire live path end-to-end:

    1. GEMINI_API_KEY is set?              -> hard fail with a clear message if not
    2. google-genai >= 2.4.0 importable?    -> client.agents needs >= 2.4.0
    3. ensure_agent(client)                 -> create/find the custom "lazarus" agent
    4. migrate(client, payroll.cob)         -> one real write->run->prove->forge loop
    5. assert the agent reached byte-for-byte equivalence (RED -> GREEN)

Exit code 0 = the live path works. Non-zero = it doesn't, with the reason printed.
Run it BEFORE the demo; if it's red, you have time to fix it (or fall back to the
UI's ?mock=1 break-glass).

Usage:
    export GEMINI_API_KEY=...
    pip install -r requirements.txt
    python scripts/smoke_test.py [--input src/sample/payroll.cob]
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

MIN_SDK = (2, 4, 0)  # client.agents + Environment APIs ship in google-genai 2.4.0


def _fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"\n[SMOKE TEST: FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)


def _check_key() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        _fail("GEMINI_API_KEY is not set. `export GEMINI_API_KEY=...` (the key "
              "provisioned at the event), then re-run.")
    print("[1/5] GEMINI_API_KEY present .......... OK")


def _check_sdk() -> None:
    try:
        import importlib.metadata as md
        ver = md.version("google-genai")
    except Exception as e:  # pragma: no cover - environment dependent
        _fail(f"google-genai not installed: {e}. Run `pip install -r requirements.txt`.")
    parts = tuple(int(x) for x in ver.split(".")[:3] if x.isdigit())
    if parts < MIN_SDK:
        _fail(f"google-genai {ver} is too old; need >= {'.'.join(map(str, MIN_SDK))} "
              "(client.agents lives there). Run `pip install -U 'google-genai>=2.6.0'`.")
    print(f"[2/5] google-genai {ver} (>= {'.'.join(map(str, MIN_SDK))}) ... OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(ROOT / "src" / "sample" / "payroll.cob"))
    args = ap.parse_args()

    _check_key()
    _check_sdk()

    import agent as agent_mod  # imported after the SDK check so failures are clear

    print("[3/5] creating/finding the 'lazarus' managed agent ...")
    client = agent_mod.genai.Client()
    agent_mod.ensure_agent(client)
    print("       agent ready ........................ OK")

    print("[4/5] running one live migration (this streams real agent steps) ...\n")
    result = agent_mod.migrate(client, args.input)

    print("\n[5/5] checking the agent reached byte-for-byte equivalence ...")
    output = agent_mod.extract_output_text(result)
    env_id = agent_mod.extract_environment_id(result)
    if not agent_mod._tests_passed(output):
        print(f"       environment_id={env_id}", file=sys.stderr)
        _fail("the agent did NOT report passing equivalence tests. Inspect the "
              "streamed output above; tighten the prompt or fall back to ?mock=1.")
    print(f"       RED -> GREEN confirmed. environment_id={env_id}")
    print("\n[SMOKE TEST: PASS] the live LAZARUS path works end-to-end. Ship it.")


if __name__ == "__main__":
    main()
