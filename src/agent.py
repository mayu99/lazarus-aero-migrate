"""
LAZARUS — Managed Agent driver.

Single Gemini 3.5 Flash Managed Agent (Antigravity) that migrates COBOL -> tested
Python, proves equivalence against the original COBOL (differential oracle), and
forges its own SKILL.md when it meets an unknown idiom.

Reconciled to the VERIFIED Managed Agents / Interactions API surface (see
docs/RESEARCH_MANAGED_AGENTS.md, consolidated 2026-05-23). Key facts this code
depends on:
  - SDK:               google-genai >= 2.4.0 floor (client.agents + Environment API ship in
                       2.4.0; step.* SSE in 2.0.0; output_text in 2.3.0). We pin >= 2.6.0.
  - Base agent id:     "antigravity-preview-05-2026"  (Gemini 3.5 Flash; same string for
                       agent= and base_agent=)
  - Gemini 3.x config: BREAKING — do NOT send temperature / top_p / top_k anywhere; they
                       are rejected/ignored on Gemini 3.x. The only generation knob is
                       thinking_level (str: minimal|low|medium|high; default now "medium").
                       We pass NO generation_config and rely on the "medium" default, so
                       there is nothing to break here — keep it that way.
  - Capability note:   The MANAGED-AGENT runtime does not expose function_calling,
                       structured output, mcp, computer_use, or file_search. (This is an
                       agent-runtime limitation, NOT a model limitation — the underlying
                       gemini-3.5-flash model DOES support function calling & structured
                       output; the Antigravity agent simply doesn't surface them.)
  - Create agent:      client.agents.create(id, base_agent, system_instruction, base_environment)
  - Run interaction:   client.interactions.create(agent=..., input=..., stream=...,
                       extra_body={"environment": "remote" | <env_id> | {type,sources}})
                       -> environment is passed via extra_body, NOT a top-level kwarg.
  - State threading:   reuse interaction.environment_id (files + packages persist).
                       previous_interaction_id is the MODEL path's state carrier and is
                       UNVERIFIED on the agent path, so we thread state via environment_id.
  - Streaming events:  event.event_type in {step.start, step.delta, step.stop,
                       interaction.created, interaction.completed, interaction.status_update,
                       error}; step.delta carries event.delta.text; the completed event
                       carries the final interaction (with .steps, .id, .environment_id).
  - Reading output:    iterate interaction.steps for the model_output step (the agent
                       resource has no guaranteed .output_text attr).

FORGE beat (SAFE pattern — do NOT rely on silent mid-run auto-reload of an
agent-authored SKILL.md, which is UNVERIFIED):
  1. The agent writes .agents/skills/<idiom>/SKILL.md and commits it (persists on disk
     IN THIS environment).
  2. The retry interaction REUSES the same environment_id so the file is present.
  3. The retry prompt EXPLICITLY instructs the agent to re-read .agents/skills/ before
     retrying — we never assume the forged skill is already in context.
  Persistence scope: the forged skill lives in the reused environment, NOT forever. A
  fresh agent invocation forks a clean base_environment; carrying a forged skill into
  future runs permanently means re-registering the agent with that SKILL.md mounted.
"""
from __future__ import annotations

import argparse
import pathlib
import re

from google import genai  # pip install -U "google-genai>=2.6.0"

AGENT_ID = "lazarus"
BASE_AGENT = "antigravity-preview-05-2026"   # Gemini 3.5 Flash managed agent (verified)
MAX_ITERATIONS = 4                            # hard cap — never loop forever on stage

AGENTS_DIR = pathlib.Path(__file__).resolve().parent.parent / ".agents"

# Heuristics for reading the agent's terminal message (the demo also shows this on screen).
_PASS_RE = re.compile(
    r"(all\s+(\d+\s+)?(equivalence\s+)?tests?\b[^.\n]{0,40}\bpass"  # "All 30 Equivalence Tests: PASS"
    r"|\ball\s+tests?\s+pass(ed)?\b"
    r"|\b0\s+failed\b"
    r"|\b\d+\s+passed,\s*0\s+failed\b"
    r"|\b100\s*%\s*(success|pass)"
    r"|\bequivalent to (the )?original cobol\b"
    r"|\bbyte[\s\-]for[\s\-]byte\s+(identical|equivalent)\b)",
    re.I,
)
# Clear failure signals VETO a pass (handles negations like "not equivalent").
_FAIL_RE = re.compile(
    r"\b([1-9]\d*\s+(tests?\s+)?failed"
    r"|did\s*n[o']?t\s+pass"
    r"|not\s+(byte[\s\-]for[\s\-]byte\s+)?(equivalent|identical)"
    r"|still\s+(red|failing)"
    r"|could\s+not\s+(reach|achieve|pass))",
    re.I,
)
_FORGE_RE = re.compile(r"(\.agents/skills/[\w\-./]+SKILL\.md)", re.I)


def build_base_environment() -> dict:
    """Mount AGENTS.md + any seed SKILL.md files into a fresh remote sandbox.

    base_environment is an object (not a bare string); `sources` mounts files at the
    paths the agent auto-discovers on startup (.agents/AGENTS.md, .agents/skills/*/SKILL.md).
    """
    sources = [
        {
            "type": "inline",
            "target": ".agents/AGENTS.md",
            "content": (AGENTS_DIR / "AGENTS.md").read_text(),
        }
    ]
    for skill_md in sorted((AGENTS_DIR / "skills").glob("*/SKILL.md")):
        sources.append(
            {
                "type": "inline",
                "target": f".agents/skills/{skill_md.parent.name}/SKILL.md",
                "content": skill_md.read_text(),
            }
        )
    return {"type": "remote", "sources": sources}


def ensure_agent(client: genai.Client) -> None:
    """Create or update the custom agent (mounts fresh AGENTS.md + skills)."""
    try:
        existing = {a.id for a in client.agents.list().agents}
    except Exception:
        existing = set()
    if AGENT_ID in existing:
        try:
            client.agents.delete(id=AGENT_ID)
        except Exception:
            pass
    client.agents.create(
        id=AGENT_ID,
        base_agent=BASE_AGENT,
        system_instruction="You are LAZARUS, an autonomous COBOL->Python migration agent. "
        "Follow .agents/AGENTS.md exactly.",
        base_environment=build_base_environment(),
        tools=[{"type": "code_execution"}]
    )


def _build_prompt(cobol: str, filename: str = "payroll.cob") -> str:
    py_name = filename.replace(".cob", ".py") if filename.endswith(".cob") else "payroll.py"
    
    if "interest" in filename.lower():
        idiom_hint = (
            "For this module the divergence is numeric DISPLAY de-editing (PIC 9(7)V99 -> zero-padded 7 int digits + '.' + 2 decimals) "
            "plus COBOL `COMPUTE` without `ROUNDED` = truncation/round-down (drop the extra fraction digits, do NOT round, e.g. "
            "use Decimal.quantize(Decimal('0.01'), rounding=ROUND_DOWN), NOT Python's round() or Decimal.quantize(ROUND_HALF_UP)). Name the skill for "
            "the real idiom (e.g. numeric-display-truncation)."
        )
    else:
        # Default or payroll
        idiom_hint = (
            "For this module the divergence is numeric DISPLAY "
            "de-editing (PIC 9(7)V99 -> zero-padded 7 int digits + '.' + 2 decimals) plus "
            "COBOL `ROUNDED` = round-half-UP (use Decimal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), NOT Python "
            "round()/banker's). It is NOT the COMP-3 storage (USAGE DISPLAY emits identical "
            "bytes). Name the skill for the real idiom (e.g. numeric-display-rounding)."
        )

    return (
        "Migrate this COBOL program to idiomatic Python. Work in the sandbox.\n"
        "1. Recover and print the business rules in plain English.\n"
        f"2. Translate to Python and write the final module to /workspace/{py_name} "
        "(the orchestrator fetches exactly that path from the environment — write it "
        "there, not just to a notebook cell).\n"
        "3. DIFFERENTIAL ORACLE (ground truth = the ORIGINAL COBOL's REAL output):\n"
        "   - PRIMARY: src/sample/golden_io.json holds real GnuCOBOL outputs captured "
        "ahead of time. Use these as ground truth. Do NOT try to install micromamba or "
        "any COBOL compiler (the sandbox has no root/package manager and live installs "
        "will time out); the diff must strictly and only depend on comparing the Python "
        "module output against the pre-captured golden_io.json bytes. Do NOT run any "
        "conda or micromamba commands under any circumstances.\n"
        f"4. Generate equivalence tests asserting python_output == golden_cobol_output "
        f"byte-for-byte; run pytest.\n"
        f"5. On failure, diagnose the TRUE idiom from the byte diff and write "
        f".agents/skills/<idiom>/SKILL.md teaching yourself how to handle it, commit it, "
        f"and report the path you wrote. {idiom_hint}\n"
        "6. EMIT MACHINE-READABLE MARKERS for the live UI. These are REQUIRED, one per "
        "line, with the EXACT prefix, as plain text in your output (not inside a code "
        "cell). The UI parses these prefixes verbatim:\n"
        "   - For EACH recovered rule (emit at least 3): `LAZARUS_RULE: {\"title\":..., "
        "\"plain\":..., \"cobol_ref\":..., \"severity\":\"rule|edge_case|gotcha\"}`\n"
        "   - After running the oracle, exactly ONE line: `LAZARUS_ORACLE_JSON: "
        "[{\"input\":..., \"cobol\":..., \"python\":..., \"match\":true|false}, ...]` "
        "covering EVERY golden input (the per-input COBOL-vs-Python byte values — this is "
        "the test panel's money shot).\n"
        f"   - As your FINAL step, print the COMPLETE final {py_name} exactly once, on the "
        f"line `LAZARUS_MODULE:` immediately followed by a single fenced ```python block "
        f"containing the WHOLE module verbatim (the same bytes you wrote to "
        f"/workspace/{py_name}). The orchestrator recovers the module from this block to "
        "render the diff + arm Download, so it must be the entire runnable file — no "
        "elisions, no '...'.\n"
        "Emit the markers even on a failing iteration (the UI shows RED then GREEN). "
        "When done, state clearly whether all equivalence tests PASS.\n"
        f"Stop when tests pass or after {MAX_ITERATIONS} iterations.\n\n"
        f"COBOL:\n```cobol\n{cobol}\n```"
    )



def _build_forge_retry_prompt(skill_path: str) -> str:
    """Follow-up prompt for the FORGE retry turn (SAFE re-read pattern).

    The forged SKILL.md persists on disk in the reused environment, but we do NOT
    assume it has been auto-reloaded into the agent's instruction context. So we
    explicitly tell the agent to re-read it (and the rest of .agents/skills/) before
    re-attempting the translation.
    """
    return (
        "Your previous attempt failed on an unknown COBOL idiom and you forged a new "
        f"skill at {skill_path}.\n"
        "That file is on disk in this SAME environment, but it is NOT yet loaded into "
        "your instructions. Before retrying:\n"
        f"1. Re-read {skill_path} (e.g. `cat {skill_path}`), and also re-scan "
        ".agents/skills/ for any other skills you have authored.\n"
        "2. Apply the technique from that skill to fix the Python translation.\n"
        "3. Re-run the differential oracle + pytest and report whether all equivalence "
        "tests now PASS.\n"
        "If a DIFFERENT unknown idiom appears, forge another "
        ".agents/skills/<idiom>/SKILL.md and report its path."
    )


def _model_output_text(step) -> str:
    """Pull text from a model_output step's content (verified shape §8:
    model_output -> {type, content:[{type:"text", text}]})."""
    if getattr(step, "type", None) != "model_output":
        return ""
    return "".join(
        part.text
        for part in (getattr(step, "content", None) or [])
        if getattr(part, "type", None) == "text"
    )


def _tool_breadcrumb(step) -> str | None:
    """Human one-liner for a tool step, or None if the step carries no tool detail.

    DEFENSIVE (the agent runtime's exact step shape for tool calls is not fully verified
    from a dev box): we read the documented Managed-Agents shapes
    (web/STREAM_CONTRACT.md adapter table) but tolerate anything missing —
      * code_execution_call   -> `$ <arguments.code>` (the command/code the agent ran),
      * code_execution_result -> a short status line (`✗ error` / `✓ ok`) + any result text.
    Returns None when the step isn't a tool step or exposes no usable detail, so the caller
    simply emits nothing — breadcrumbs are a live-UX bonus, never required. These breadcrumbs
    feed phase_for_text (server side) so the rail lights recover/translate/oracle/test off
    real tool activity (`cobc`, `pytest`, `payroll.py`) instead of only end-block prose.
    """
    stype = getattr(step, "type", None)
    if stype == "code_execution_call":
        args = getattr(step, "arguments", None)
        code = getattr(args, "code", None) if args is not None else None
        if not code and isinstance(args, dict):
            code = args.get("code")
        if code:
            first = code.strip().splitlines()[0][:200] if code.strip() else ""
            return f"$ {first}" if first else None
        return None
    if stype == "code_execution_result":
        is_error = bool(getattr(step, "is_error", False))
        result = getattr(step, "result", None)
        snippet = ""
        if isinstance(result, str) and result.strip():
            snippet = " " + result.strip().splitlines()[-1][:160]
        mark = "✗ error" if is_error else "✓ ok"
        return f"{mark}{snippet}".rstrip() or None
    return None


def extract_output_text(interaction, client: genai.Client | None = None) -> str:
    """Return the agent's terminal model output text.

    Resolution order (live-path safe — the completed event ships EMPTY outputs):
      1. text accumulated from the stream during _run_interaction (the live trace),
      2. the interaction object's own model_output steps (a fetched/non-streaming object),
      3. an authoritative client.interactions.get(id) fetch, when a client is available
         and nothing above produced text (the completed event was empty + no deltas).
    `output_text` is intentionally NOT trusted as the primary source (not a documented
    field below SDK 2.3.0; empty on the completed event).
    """
    streamed = getattr(interaction, "_lazarus_output_text", None)
    if streamed:
        return streamed

    from_steps = "".join(
        _model_output_text(step) for step in (getattr(interaction, "steps", None) or [])
    )
    if from_steps:
        return from_steps

    fetch_client = client or getattr(interaction, "_lazarus_client", None)
    itx_id = getattr(interaction, "id", None)
    if fetch_client is not None and itx_id is not None \
            and hasattr(fetch_client, "interactions") \
            and hasattr(fetch_client.interactions, "get"):
        try:
            fetched = fetch_client.interactions.get(itx_id)
            return "".join(
                _model_output_text(s) for s in (getattr(fetched, "steps", None) or [])
            )
        except Exception:
            return ""
    return ""


def extract_environment_id(interaction) -> str | None:
    """The env id to reuse on the next turn (carries files + forged skills)."""
    return getattr(interaction, "environment_id", None)


def _tests_passed(output_text: str) -> bool:
    # A clear failure signal vetoes a pass (e.g. "2 failed", "not equivalent").
    if _FAIL_RE.search(output_text):
        return False
    return bool(_PASS_RE.search(output_text))


def _forged_skill_path(output_text: str) -> str | None:
    m = _FORGE_RE.search(output_text)
    return m.group(1) if m else None


def _run_interaction(client: genai.Client, *, input_text: str, environment):
    """One streamed interaction. Forwards step.delta text to the UI and accumulates the
    model output FROM THE STREAM.

    LIVE-PATH NOTE (verified, findings-agents.md): the `interaction.completed` event ships
    `event.interaction` "with empty outputs to reduce the payload size" — its .steps /
    output_text are EMPTY on the real API. So we (1) accumulate text from step.delta /
    step.stop during the stream (the live trace), and (2) after the stream, fetch the
    AUTHORITATIVE final object via client.interactions.get(interaction_id). We return that
    fetched object (carrying real .steps + .environment_id), with the streamed text
    attached as `_lazarus_output_text` and the client attached so extract_output_text can
    do a get() fallback if needed.
    """
    stream = client.interactions.create(
        agent=AGENT_ID,
        input=input_text,
        stream=True,
        extra_body={"environment": environment},   # env via extra_body (verified surface)
    )

    completed = None
    interaction_id = None
    env_id = None
    output_parts: list[str] = []
    for event in stream:
        # Every event carries interaction_id (resume/fetch token).
        interaction_id = getattr(event, "interaction_id", None) or interaction_id
        et = getattr(event, "event_type", None)
        if et == "step.delta":
            text = getattr(getattr(event, "delta", None), "text", None)
            if text:
                emit_to_ui(text)
                output_parts.append(text)
        elif et in ("step.start", "step.stop"):
            step = getattr(event, "step", None)
            # ACTIVITY BREADCRUMB (defensive): if this is a tool step (code execution),
            # forward a one-line breadcrumb so the live UI shows real activity during the
            # silent multi-minute tool stretches (conda/compile/pytest) and the phase rail
            # advances off it. No-op when the step carries no tool detail.
            crumb = _tool_breadcrumb(step)
            if crumb:
                emit_to_ui(crumb + "\n")
            if et == "step.stop":
                # Terminal text of a completed step (verified §8 carries the full Step here).
                output_parts.append(_model_output_text(step))
        elif et == "interaction.completed":
            completed = getattr(event, "interaction", None)
            # env id is still present on the (otherwise-empty) completed interaction.
            env_id = extract_environment_id(completed) or env_id
            interaction_id = getattr(completed, "id", None) or interaction_id

    # Authoritative final fetch: the completed event's payload is empty, so re-fetch the
    # full interaction object when we can. Fall back to the completed event if get() fails.
    final = completed
    if interaction_id is not None and hasattr(client, "interactions") \
            and hasattr(client.interactions, "get"):
        try:
            fetched = client.interactions.get(interaction_id)
            if fetched is not None:
                final = fetched
        except Exception:
            pass  # network/SDK hiccup -> use the completed event + streamed text

    if final is not None:
        accumulated = "".join(output_parts)
        if not accumulated:  # nothing streamed -> use the fetched object's steps
            accumulated = "".join(
                _model_output_text(s) for s in (getattr(final, "steps", None) or [])
            )
        try:
            final._lazarus_output_text = accumulated
            final._lazarus_client = client
        except (AttributeError, TypeError):
            pass  # immutable object; extract_output_text(client=) can still fetch
        # Make sure env id survives even if the fetched object lacks it.
        if env_id and not extract_environment_id(final):
            try:
                final.environment_id = env_id
            except (AttributeError, TypeError):
                pass
    return final


def migrate(client: genai.Client, cobol_path: str):
    """Run the write -> run -> prove -> self-heal loop, streaming steps to the UI.

    The MAX_ITERATIONS cap is ENFORCED here in code (C10): a real per-turn counter is
    emitted to the UI via emit_iteration() and the loop hard-stops at MAX_ITERATIONS —
    the prompt text is only a hint, never the safety net (an infinite loop on stage is
    death). State threads across forge->retry turns via environment_id. Returns the
    final completed interaction (carries .id, .environment_id, .steps).
    """
    cobol = pathlib.Path(cobol_path).read_text()
    interaction = None

    filename = pathlib.Path(cobol_path).name
    for iteration in range(1, MAX_ITERATIONS + 1):
        emit_iteration(iteration, MAX_ITERATIONS)   # visible counter (UI renders this)

        if iteration == 1:
            interaction = _run_interaction(
                client, input_text=_build_prompt(cobol, filename=filename), environment="remote"
            )
        else:
            # Reuse the SAME environment so the forged SKILL.md is on disk, and explicitly
            # instruct the agent to re-read it (SAFE pattern; no silent auto-reload).
            interaction = _run_interaction(
                client,
                input_text=_build_forge_retry_prompt(_pending_skill_path),
                environment=extract_environment_id(interaction),
            )

        output = extract_output_text(interaction)
        if _tests_passed(output):
            break
        _pending_skill_path = _forged_skill_path(output)
        if not _pending_skill_path:
            # Failed but no new skill was forged -> nothing new to re-read; stop early.
            break

    return interaction


def emit_to_ui(text: str) -> None:
    """Forward streamed text/steps to the front-end live trace. Wire to SSE/WebSocket."""
    print(text, end="", flush=True)


def emit_iteration(current: int, total: int) -> None:
    """Surface the enforced iteration counter to the UI (C10's visible counter).

    Called once per loop turn before the interaction runs. Wire to the same SSE/
    WebSocket channel so the front-end can render e.g. "Iteration 2 / 4".
    """
    print(f"\n[iteration {current}/{total}]", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="src/sample/payroll.cob")
    args = ap.parse_args()

    client = genai.Client()  # reads GEMINI_API_KEY
    ensure_agent(client)
    result = migrate(client, args.input)

    # Persist the environment id so follow-up turns reuse the same sandbox + forged skills:
    env_id = extract_environment_id(result)
    itx_id = getattr(result, "id", None)
    print(f"\n[done] environment_id={env_id} interaction_id={itx_id}")


if __name__ == "__main__":
    main()
