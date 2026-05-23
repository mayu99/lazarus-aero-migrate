"""Tests for the LAZARUS Managed Agent driver (src/agent.py).

These exercise the NETWORK-FREE logic of the driver against the verified Managed
Agents / Interactions API surface (see docs/RESEARCH_MANAGED_AGENTS.md):

  * base_environment construction (mounts AGENTS.md + seed SKILL.md files),
  * prompt building (initial + the FORGE safe-reload retry prompt),
  * extracting output text from `steps` (NOT a `.output_text` attr — unverified),
  * extracting environment_id,
  * the write -> run -> prove -> forge -> retry loop, with state threaded via
    environment_id across turns and an explicit re-read of .agents/skills/.

The Gemini client is faked, so nothing here hits the network or needs a key.
"""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
for p in (str(SRC_DIR), str(REPO_ROOT)):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)


@pytest.fixture
def agent_mod():
    """Import src/agent.py with a stubbed `google.genai` so it loads without the SDK."""
    google_pkg = types.ModuleType("google")
    genai_mod = types.ModuleType("google.genai")

    class _Client:  # placeholder; tests pass their own fake client into functions
        def __init__(self, *a, **k):
            pass

    genai_mod.Client = _Client
    google_pkg.genai = genai_mod
    sys.modules["google"] = google_pkg
    sys.modules["google.genai"] = genai_mod

    sys.modules.pop("agent", None)
    mod = importlib.import_module("agent")
    return importlib.reload(mod)


# --------------------------------------------------------------------------
# fakes that mimic the verified Interactions API step/stream shapes (§8)
# --------------------------------------------------------------------------
class FakeStep:
    def __init__(self, step_type, text=""):
        self.type = step_type
        self.content = [types.SimpleNamespace(type="text", text=text)]


class FakeInteraction:
    """Mimics a completed interaction: carries id, environment_id, steps."""
    def __init__(self, *, id, environment_id, steps):
        self.id = id
        self.environment_id = environment_id
        self.steps = steps


def make_stream(*, env_id, interaction_id, model_text, deltas=()):
    """Yield verified-shape SSE events, ending with a completed interaction."""
    final = FakeInteraction(
        id=interaction_id,
        environment_id=env_id,
        steps=[FakeStep("model_output", model_text)],
    )
    for d in deltas:
        yield types.SimpleNamespace(
            event_type="step.delta", delta=types.SimpleNamespace(text=d)
        )
    yield types.SimpleNamespace(
        event_type="interaction.completed", interaction=final
    )


def make_stream_steps_only(*, env_id, interaction_id, model_text):
    """C11 hardening: terminal interaction object has NO `.steps` attr (only id +
    environment_id). The model_output arrives via a streamed step.stop event, exactly
    the §8 shape. migrate() must still recover the text from the stream itself."""
    final = types.SimpleNamespace(id=interaction_id, environment_id=env_id)  # no .steps
    yield types.SimpleNamespace(
        event_type="step.stop",
        step=FakeStep("model_output", model_text),
    )
    yield types.SimpleNamespace(
        event_type="interaction.completed", interaction=final,
        interaction_id=interaction_id,
    )


def make_stream_empty_completed(*, env_id, interaction_id, model_text):
    """The REAL API shape: interaction.completed ships `event.interaction` "with empty
    outputs to reduce the payload size" (verbatim, findings-agents.md). So the model
    text is NOT on the completed event — it must come from streamed step.delta and/or
    a follow-up client.interactions.get(interaction_id). Here the deltas carry the text;
    the completed event's interaction has EMPTY steps + no output_text (but keeps
    environment_id + id). interactions.get(id) returns the fully-populated object."""
    # stream the model text as deltas (the live-trace path)
    for ch in (model_text,):
        yield types.SimpleNamespace(event_type="step.delta",
                                    delta=types.SimpleNamespace(text=ch),
                                    interaction_id=interaction_id)
    empty = types.SimpleNamespace(id=interaction_id, environment_id=env_id, steps=[])
    yield types.SimpleNamespace(event_type="interaction.completed", interaction=empty,
                                interaction_id=interaction_id)


class FakeInteractions:
    def __init__(self, scripted):
        self._scripted = list(scripted)  # list of dicts describing each turn
        self.calls = []                  # records kwargs of each create()
        self.get_calls = []              # records ids passed to get()

    def create(self, **kwargs):
        self.calls.append(kwargs)
        spec = self._scripted[len(self.calls) - 1]
        if spec.get("steps_only"):
            return make_stream_steps_only(
                env_id=spec["env_id"], interaction_id=spec["interaction_id"],
                model_text=spec["model_text"],
            )
        if spec.get("empty_completed"):
            return make_stream_empty_completed(
                env_id=spec["env_id"], interaction_id=spec["interaction_id"],
                model_text=spec["model_text"],
            )
        return make_stream(
            env_id=spec["env_id"], interaction_id=spec["interaction_id"],
            model_text=spec["model_text"], deltas=spec.get("deltas", ()),
        )

    def get(self, interaction_id):
        """Authoritative final fetch — returns the fully-populated interaction."""
        self.get_calls.append(interaction_id)
        spec = next(s for s in self._scripted if s["interaction_id"] == interaction_id)
        return FakeInteraction(
            id=interaction_id, environment_id=spec["env_id"],
            steps=[FakeStep("model_output", spec["model_text"])],
        )


class FakeAgents:
    def __init__(self):
        self.created = []

    def create(self, **kwargs):
        self.created.append(kwargs)


class FakeClient:
    def __init__(self, scripted):
        self.agents = FakeAgents()
        self.interactions = FakeInteractions(scripted)


# --------------------------------------------------------------------------
# base_environment construction
# --------------------------------------------------------------------------
def test_build_base_environment_mounts_agents_md(agent_mod):
    env = agent_mod.build_base_environment()
    assert env["type"] == "remote"
    targets = [s["target"] for s in env["sources"]]
    assert ".agents/AGENTS.md" in targets
    agents_src = next(s for s in env["sources"] if s["target"] == ".agents/AGENTS.md")
    assert agents_src["type"] == "inline"
    assert "LAZARUS" in agents_src["content"]


# --------------------------------------------------------------------------
# version pin / base agent id  (verified facts)
# --------------------------------------------------------------------------
def test_base_agent_id_is_verified_string(agent_mod):
    assert agent_mod.BASE_AGENT == "antigravity-preview-05-2026"


def test_no_sampling_params_sent_to_gemini_3x(agent_mod, tmp_path):
    """Gemini 3.x BREAKING: temperature/top_p/top_k are rejected. migrate() must never
    send them — directly or nested in extra_body/generation_config."""
    cobol = tmp_path / "p.cob"
    cobol.write_text("IDENTIFICATION DIVISION.\n")
    client = FakeClient([
        {"env_id": "env1", "interaction_id": "i1",
         "model_text": "All tests pass. 3/3 equivalent to original COBOL."},
    ])
    agent_mod.migrate(client, str(cobol))

    forbidden = {"temperature", "top_p", "top_k"}

    def _scan(obj):
        if isinstance(obj, dict):
            assert not (forbidden & set(obj)), f"sampling param leaked: {forbidden & set(obj)}"
            for v in obj.values():
                _scan(v)

    for call in client.interactions.calls:
        assert forbidden.isdisjoint(call), f"sampling param in kwargs: {call.keys()}"
        _scan(call.get("extra_body"))
        _scan(call.get("generation_config"))


# --------------------------------------------------------------------------
# prompt building — initial + FORGE safe-reload retry
# --------------------------------------------------------------------------
def test_build_prompt_includes_cobol_and_oracle_steps(agent_mod):
    prompt = agent_mod._build_prompt("IDENTIFICATION DIVISION.")
    assert "IDENTIFICATION DIVISION." in prompt
    assert "differential" in prompt.lower() or "oracle" in prompt.lower()


def test_build_prompt_uses_golden_as_primary_not_apt(agent_mod):
    """No-apt sandbox reality (devils-advocate): the prompt must make golden_io.json
    the PRIMARY oracle ground truth and must NOT instruct an apt-get install of cobc."""
    prompt = agent_mod._build_prompt("IDENTIFICATION DIVISION.")
    low = prompt.lower()
    assert "golden_io.json" in low
    assert "apt-get" not in low and "apt install" not in low


def test_build_prompt_names_true_idiom_not_comp3(agent_mod):
    """C13 (narrative honesty): the diagnosis the agent is steered toward must be the
    REAL idiom (numeric DISPLAY de-editing + round-half-up), and must explicitly say it
    is NOT the COMP-3 storage (which has zero effect on output bytes)."""
    low = agent_mod._build_prompt("IDENTIFICATION DIVISION.").lower()
    assert "round" in low and ("half-up" in low or "round_half_up" in low)
    assert "display" in low                       # the de-editing/format idiom
    assert "not the comp-3" in low or "not comp-3" in low


def test_build_prompt_requests_machine_readable_markers(agent_mod):
    """The UI's structured panels need machine-readable data, so the prompt must ask the
    agent to print the LAZARUS_ORACLE_JSON + LAZARUS_RULE marker lines, AND the LAZARUS_MODULE
    block (the tarball-independent, deterministic source for the diff + download)."""
    prompt = agent_mod._build_prompt("IDENTIFICATION DIVISION.")
    assert "LAZARUS_ORACLE_JSON" in prompt
    assert "LAZARUS_RULE" in prompt
    assert "LAZARUS_MODULE" in prompt
    assert "/workspace/payroll.py" in prompt


def test_forge_retry_prompt_instructs_explicit_reread(agent_mod):
    """The SAFE FORGE pattern: the retry prompt MUST explicitly tell the agent to
    re-read .agents/skills/ (do not rely on silent mid-run auto-reload)."""
    prompt = agent_mod._build_forge_retry_prompt(".agents/skills/numeric-display-rounding/SKILL.md")
    low = prompt.lower()
    assert ".agents/skills/" in prompt
    assert "re-read" in low or "read" in low
    assert "numeric-display-rounding" in low


# --------------------------------------------------------------------------
# _tool_breadcrumb — live activity breadcrumbs from tool steps (Phase 2)
# --------------------------------------------------------------------------
def test_tool_breadcrumb_from_code_execution_call(agent_mod):
    """A code_execution_call step yields a `$ <command>` breadcrumb (first line, trimmed)."""
    step = types.SimpleNamespace(
        type="code_execution_call",
        arguments=types.SimpleNamespace(code="micromamba install -c conda-forge gnucobol\nmore"),
    )
    crumb = agent_mod._tool_breadcrumb(step)
    assert crumb == "$ micromamba install -c conda-forge gnucobol"


def test_tool_breadcrumb_accepts_dict_arguments(agent_mod):
    """arguments may arrive as a dict (defensive) — still recover the command."""
    step = types.SimpleNamespace(type="code_execution_call", arguments={"code": "cobc -x payroll.cob"})
    assert agent_mod._tool_breadcrumb(step) == "$ cobc -x payroll.cob"


def test_tool_breadcrumb_result_ok_and_error(agent_mod):
    ok = types.SimpleNamespace(type="code_execution_result", is_error=False, result="10 passed")
    assert agent_mod._tool_breadcrumb(ok).startswith("✓ ok")
    err = types.SimpleNamespace(type="code_execution_result", is_error=True, result="Traceback ...")
    assert agent_mod._tool_breadcrumb(err).startswith("✗ error")


def test_tool_breadcrumb_none_for_non_tool_or_bare_step(agent_mod):
    """Defensive: a model_output step, an unknown step, or a tool call with no detail -> None
    (the caller emits nothing — breadcrumbs are a bonus, never required)."""
    assert agent_mod._tool_breadcrumb(types.SimpleNamespace(type="model_output")) is None
    assert agent_mod._tool_breadcrumb(types.SimpleNamespace(type="thought")) is None
    assert agent_mod._tool_breadcrumb(types.SimpleNamespace(type="code_execution_call",
                                                            arguments=None)) is None
    assert agent_mod._tool_breadcrumb(None) is None


def test_run_interaction_forwards_tool_breadcrumbs_to_ui(agent_mod, monkeypatch):
    """End-to-end: _run_interaction emits a tool breadcrumb to emit_to_ui when the stream
    carries a code-execution step (step.start/step.stop), so the live UI shows real activity
    during silent tool stretches. The breadcrumb is UI-only — it must NOT pollute the
    accumulated model output that marker/module parsing reads."""
    captured = []
    monkeypatch.setattr(agent_mod, "emit_to_ui", captured.append)

    final = types.SimpleNamespace(id="iX", environment_id="envX")

    class _ToolStreamClient:
        class interactions:
            get_calls = []
            @staticmethod
            def create(**kwargs):
                yield types.SimpleNamespace(  # the agent runs a compile via code execution
                    event_type="step.start", interaction_id="iX",
                    step=types.SimpleNamespace(
                        type="code_execution_call",
                        arguments=types.SimpleNamespace(code="cobc -x payroll.cob -o /workspace/bin")),
                )
                yield types.SimpleNamespace(  # result of the tool call
                    event_type="step.stop", interaction_id="iX",
                    step=types.SimpleNamespace(type="code_execution_result",
                                               is_error=False, result="(compiled)"),
                )
                yield types.SimpleNamespace(  # the model's narrative text
                    event_type="step.delta", interaction_id="iX",
                    delta=types.SimpleNamespace(text="Compiled and ran the oracle."),
                )
                yield types.SimpleNamespace(
                    event_type="interaction.completed", interaction=final, interaction_id="iX")
            @staticmethod
            def get(interaction_id):
                _ToolStreamClient.interactions.get_calls.append(interaction_id)
                return final

    itx = agent_mod._run_interaction(_ToolStreamClient(), input_text="x", environment="remote")

    joined = "".join(captured)
    assert "$ cobc -x payroll.cob" in joined          # the command breadcrumb reached the UI
    assert "✓ ok" in joined                            # the result breadcrumb reached the UI
    assert "Compiled and ran the oracle." in joined    # the model narrative still streamed
    # The breadcrumbs must NOT be in the accumulated model output (marker/module parsing input)
    assert "cobc -x" not in agent_mod.extract_output_text(itx)


# --------------------------------------------------------------------------
# extracting results from the verified step shape (NOT .output_text)
# --------------------------------------------------------------------------
def test_extract_output_text_reads_model_output_step(agent_mod):
    itx = FakeInteraction(
        id="i1", environment_id="env1",
        steps=[FakeStep("thought", "thinking"), FakeStep("model_output", "RESULT")],
    )
    assert agent_mod.extract_output_text(itx) == "RESULT"


def test_extract_environment_id(agent_mod):
    itx = FakeInteraction(id="i1", environment_id="env-xyz", steps=[])
    assert agent_mod.extract_environment_id(itx) == "env-xyz"


# --------------------------------------------------------------------------
# the migrate loop — single green pass
# --------------------------------------------------------------------------
def test_migrate_single_pass_when_tests_pass(agent_mod, tmp_path):
    cobol = tmp_path / "p.cob"
    cobol.write_text("IDENTIFICATION DIVISION.\n")
    client = FakeClient([
        {"env_id": "env1", "interaction_id": "i1",
         "model_text": "All tests pass. ORACLE: 3/3 equivalent to original COBOL."},
    ])
    result = agent_mod.migrate(client, str(cobol))
    # only one interaction (no forge needed)
    assert len(client.interactions.calls) == 1
    # first call provisions a fresh remote env via extra_body (verified surface)
    first = client.interactions.calls[0]
    assert first["agent"] == agent_mod.AGENT_ID
    assert first["stream"] is True
    assert first["extra_body"] == {"environment": "remote"}
    assert result.environment_id == "env1"


# --------------------------------------------------------------------------
# LIVE-PATH BUG: interaction.completed ships EMPTY outputs (payload-size).
# extract_output_text must NOT read empty terminal .steps; it must use the
# stream-accumulated text and/or the authoritative interactions.get() fetch.
# --------------------------------------------------------------------------
def test_extract_output_text_when_completed_event_is_empty(agent_mod, tmp_path):
    """Real API: the completed event's interaction has EMPTY steps. migrate() must still
    recover the model text (from streamed deltas) and detect pass/forge correctly."""
    cobol = tmp_path / "p.cob"
    cobol.write_text("IDENTIFICATION DIVISION.\n")
    client = FakeClient([
        # turn 1: RED + forge; text ONLY in streamed deltas, completed event is empty
        {"env_id": "env1", "interaction_id": "i1", "empty_completed": True,
         "model_text": "FAILED unknown idiom. FORGED .agents/skills/numeric-display-rounding/SKILL.md"},
        {"env_id": "env1", "interaction_id": "i2", "empty_completed": True,
         "model_text": "All tests pass. equivalent to original COBOL."},
    ])
    result = agent_mod.migrate(client, str(cobol))
    assert len(client.interactions.calls) == 2     # forge recovered from streamed text
    assert result.environment_id == "env1"          # env id still present on completed event


def test_get_used_as_authoritative_fetch_after_stream(agent_mod):
    """_run_interaction performs the authoritative client.interactions.get(id) after the
    stream (the completed event is empty), and the returned object exposes the fetched
    steps' text — no double-fetch needed by extract_output_text."""
    client = FakeClient([
        {"env_id": "env9", "interaction_id": "i9", "empty_completed": True,
         "model_text": "All tests pass. equivalent to original COBOL."},
    ])
    itx = agent_mod._run_interaction(client, input_text="x", environment="remote")
    assert client.interactions.get_calls == ["i9"]            # one authoritative fetch
    # the fetched object's real text is available, env id preserved
    assert "tests pass" in agent_mod.extract_output_text(itx).lower()
    assert agent_mod.extract_environment_id(itx) == "env9"
    assert client.interactions.get_calls == ["i9"]            # no second fetch


# --------------------------------------------------------------------------
# the migrate loop — forge then retry (the FORGE beat, SAFE pattern)
# --------------------------------------------------------------------------
def test_migrate_forges_then_retries_reusing_environment(agent_mod, tmp_path):
    cobol = tmp_path / "p.cob"
    cobol.write_text("IDENTIFICATION DIVISION.\n")
    client = FakeClient([
        # turn 1: RED — unknown idiom, agent forged a SKILL.md
        {"env_id": "env1", "interaction_id": "i1",
         "model_text": "FAILED: unknown idiom numeric DISPLAY format + ROUND-HALF-UP. "
                       "FORGED .agents/skills/numeric-display-rounding/SKILL.md"},
        # turn 2: GREEN after re-reading the forged skill
        {"env_id": "env1", "interaction_id": "i2",
         "model_text": "All tests pass. 3/3 equivalent to original COBOL."},
    ])
    result = agent_mod.migrate(client, str(cobol))

    assert len(client.interactions.calls) == 2
    # turn 2 REUSES the env id from turn 1 (state threaded via environment, §5.2)
    second = client.interactions.calls[1]
    assert second["extra_body"] == {"environment": "env1"}
    # turn 2 prompt explicitly re-reads the forged skill (SAFE pattern)
    assert ".agents/skills/" in second["input"]
    assert result.id == "i2"


def test_migrate_recovers_output_from_stream_when_terminal_has_no_steps(agent_mod, tmp_path):
    """C11: don't depend on a guessed `interaction.steps` array on the terminal object.
    If model_output arrives only via streamed step.stop events, migrate() must still
    READ it — proven here by the forge->retry firing off output that exists ONLY in the
    stream. If migrate ignored the streamed text, it would see no forge path and stop
    after 1 turn; a 2nd turn proves the streamed output was recovered and parsed."""
    cobol = tmp_path / "p.cob"
    cobol.write_text("IDENTIFICATION DIVISION.\n")
    client = FakeClient([
        # turn 1: RED + forge — but the model_output is ONLY in the stream (no .steps)
        {"env_id": "env1", "interaction_id": "i1", "steps_only": True,
         "model_text": "FAILED unknown idiom. FORGED .agents/skills/numeric-display-rounding/SKILL.md"},
        # turn 2: GREEN
        {"env_id": "env1", "interaction_id": "i2", "steps_only": True,
         "model_text": "All tests pass. equivalent to original COBOL."},
    ])
    result = agent_mod.migrate(client, str(cobol))
    assert len(client.interactions.calls) == 2   # forge detected from streamed text -> retry
    assert client.interactions.calls[1]["extra_body"] == {"environment": "env1"}
    assert ".agents/skills/" in client.interactions.calls[1]["input"]
    assert result.id == "i2"


def test_migrate_caps_iterations(agent_mod, tmp_path):
    cobol = tmp_path / "p.cob"
    cobol.write_text("IDENTIFICATION DIVISION.\n")
    # every turn stays RED + forges -> must stop at MAX_ITERATIONS, never loop forever
    scripted = [
        {"env_id": "env1", "interaction_id": f"i{n}",
         "model_text": "FAILED: unknown idiom. FORGED .agents/skills/x/SKILL.md"}
        for n in range(agent_mod.MAX_ITERATIONS + 3)
    ]
    client = FakeClient(scripted)
    agent_mod.migrate(client, str(cobol))
    assert len(client.interactions.calls) == agent_mod.MAX_ITERATIONS


# --------------------------------------------------------------------------
# C10 — REAL iteration counter, enforced in code + surfaced to the UI
# --------------------------------------------------------------------------
def test_migrate_emits_iteration_counter_to_ui(agent_mod, tmp_path, monkeypatch):
    """C10: the hard cap must be a real, observable counter — each turn reports
    (current, MAX_ITERATIONS) to the UI so the frontend can render it on stage."""
    seen = []
    monkeypatch.setattr(agent_mod, "emit_iteration",
                        lambda current, total: seen.append((current, total)))
    cobol = tmp_path / "p.cob"
    cobol.write_text("IDENTIFICATION DIVISION.\n")
    client = FakeClient([
        {"env_id": "env1", "interaction_id": "i1",
         "model_text": "FAILED. FORGED .agents/skills/x/SKILL.md"},
        {"env_id": "env1", "interaction_id": "i2",
         "model_text": "All tests pass. equivalent to original COBOL."},
    ])
    agent_mod.migrate(client, str(cobol))
    # one counter event per interaction turn, numbered from 1, total = MAX_ITERATIONS
    assert seen == [(1, agent_mod.MAX_ITERATIONS), (2, agent_mod.MAX_ITERATIONS)]


def test_migrate_counter_stops_at_max_when_never_green(agent_mod, tmp_path, monkeypatch):
    """C10: the counter must hard-stop at MAX_ITERATIONS (no off-by-one over-run)."""
    seen = []
    monkeypatch.setattr(agent_mod, "emit_iteration",
                        lambda current, total: seen.append(current))
    cobol = tmp_path / "p.cob"
    cobol.write_text("IDENTIFICATION DIVISION.\n")
    scripted = [
        {"env_id": "env1", "interaction_id": f"i{n}",
         "model_text": "FAILED. FORGED .agents/skills/x/SKILL.md"}
        for n in range(agent_mod.MAX_ITERATIONS + 3)
    ]
    agent_mod.migrate(FakeClient(scripted), str(cobol))
    assert seen == list(range(1, agent_mod.MAX_ITERATIONS + 1))
