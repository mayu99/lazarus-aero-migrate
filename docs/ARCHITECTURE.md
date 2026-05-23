# LAZARUS — Architecture

## 1. System Overview

LAZARUS is a **single Managed Agent** running in one Google-hosted Linux sandbox. There is **no multi-agent orchestration** — the Managed Agents API does not expose sub-agent deployment (that lives in Antigravity 2.0 / ADK, not the Gemini API). Everything below happens as a stateful tool-use loop driven by Gemini 3.5 Flash.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Front-end (browser)                                                   │
│   • drop-zone for COBOL          • live step.* event trace             │
│   • plain-English logic panel    • COBOL↔Python diff viewer            │
│   • pytest terminal (red→green)  • forged-skill / git-diff panel       │
└───────────────▲───────────────────────────────────────────────┬──────┘
                │ SSE stream (step.start/delta/stop)              │ user input
                │                                                 ▼
┌───────────────┴───────────────────────────────────────────────────────┐
│  Orchestrator (FastAPI)  src/agent.py                                   │
│   client.interactions.create(agent="lazarus", input=..., stream=True,  │
│       extra_body={"environment": <id>})  # reuse env to keep state     │
└───────────────▲───────────────────────────────────────────────────────┘
                │ Interactions API
┌───────────────┴───────────────────────────────────────────────────────┐
│  MANAGED AGENT  (base: antigravity-preview-05-2026 · Gemini 3.5 Flash) │
│  Persistent Ubuntu sandbox (Python 3.12, Node 22; real GnuCOBOL via    │
│  micromamba/conda-forge userland — no root, installed into reused env) │
│   Tools used:  code_execution · filesystem (persistent)               │
│   Skills:      .agents/AGENTS.md + .agents/skills/*/SKILL.md           │
│                                                                        │
│   LOOP:  read COBOL → recover business rules → write Python →          │
│          compile+run original COBOL (real GnuCOBOL oracle) → gen tests→│
│          pytest → on fail: diagnose → (forge SKILL.md if new idiom) →  │
│          patch → re-run → until GREEN                                  │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. The core loop (write → run → **prove** → self-heal)

1. **Ingest.** The whole COBOL module is sent in one request (Gemini 3.5 Flash 1M-token context, 65,536-token max output for full-file generation).
2. **Recover business logic.** The agent emits a human-readable spec of the rules the COBOL encodes — tax/rounding/edge-cases. This is shown on screen (the "archaeology" beat) and used as the translation contract.
3. **Translate.** The agent writes `payroll.py` to the sandbox filesystem.
4. **Build the oracle.** During **pre-warm**, the agent **installs real GnuCOBOL itself inside the sandbox via micromamba / conda-forge** — userland, **no root** (the conda package brings its own compiler + `libcob` + `gmp`, so no system libraries or `apt` are needed; the sandbox has unrestricted outbound network). It installs into a long-lived `environment_id` that is reused on stage; the agent then **compiles the *original* COBOL with that real `cobc -x` and runs it** on a battery of inputs, capturing canonical outputs. Because the env is reused, the live run **needs no network at demo time**. **This is the ground truth** — real-compiler output, not agent-invented assertions.
5. **Generate equivalence tests.** `test_equivalence.py` asserts `python_output == cobol_output` byte-for-byte across the input battery.
6. **Run + iterate.** `pytest` runs; failures stream into the UI (RED). The agent reads the traceback and patches.
7. **FORGE self-heal.** If the failure is an *unknown idiom* — for the golden demo, **COBOL numeric `DISPLAY` formatting (zero-padded `0000775.00`) + `ROUND-HALF-UP` equivalence**; other candidates are `REDEFINES`, `OCCURS DEPENDING ON` — the agent **writes a new `.agents/skills/<idiom>/SKILL.md`** describing how to handle it. The skill **stays live for the rest of the migration** because we keep working **in the same `environment_id`**; the next pass **re-reads `.agents/skills/`** from that live environment. It re-runs, and tests go **GREEN**.

> **Why this idiom (narrative honesty, proven by real bytes):** the demo's RED is caused by COBOL's numeric `DISPLAY` **de-editing** (full PICTURE width, zero-padded: `0000775.00`) plus `COMPUTE ... ROUNDED` = **round-half-up** vs Python's banker's rounding — *not* by `COMP-3`. (A `USAGE DISPLAY` variant of the module produces byte-identical output to the COMP-3 version, so packed-decimal storage has zero effect on the diff.) The forged skill teaches exactly this format+rounding equivalence — the real, subtler institutional-knowledge gap.

> **Verified vs. unverified — and the scope of "persist" (so we never overclaim on stage):**
> - ✅ Startup auto-discovery of `.agents/skills/*/SKILL.md` is documented.
> - ✅ A forged skill stays available **for the lifetime of the live environment you keep reusing** (`environment_id`).
> - ⚠️ It does **NOT** carry into a *new* agent invocation. Verbatim: *"Each invocation forks the base environment, so every run starts clean."* A fresh run does **not** inherit skills forged in a previous run's environment.
> - To make a forged skill **permanent**, **re-register the agent** with the skill mounted in `base_environment` (`agents.create(..., base_environment={"type":"remote","sources":[…SKILL.md…]})`), or fork from the saved `environment_id`.
> - ⚠️ *Mid-interaction* hot-reload of a skill the agent just authored is **not documented** — LAZARUS triggers re-discovery on the next pass within the live environment, not a live in-flight reload.
>
> The on-stage beat ("the agent grafts itself a new skill and beats the idiom, in one live session") is fully real. We do **not** claim cross-run accumulation unless we re-register. Source: <https://ai.google.dev/gemini-api/docs/managed-agents-quickstart.md.txt>

## 3. Why the differential oracle matters (the judge-proofing)

The strongest attack on any "AI migrates code" demo: *"The agent wrote the code AND the tests, so passing proves internal consistency, not correctness."* (A DeepMind judge will ask exactly this.)

LAZARUS answers it structurally: the **oracle is the original COBOL program's real output**, produced by a real compiler (GnuCOBOL) the agent did not write. Equivalence is therefore *falsifiable*. If the Python rounds or formats a value differently than the mainframe would (e.g. banker's rounding vs COBOL `ROUND-HALF-UP`, or `775.0` vs the zero-padded `0000775.00`), the diff is non-zero and the test is RED — visibly, on stage.

```
   COBOL source ──real cobc (GnuCOBOL in-sandbox)──> run(inputs) ─> canonical_output ┐
                                                                                     ├─ assert ==
   COBOL source ──Gemini──> payroll.py ───────────── run(inputs) ─> python_output    ┘
```

**Primary path (verified-true for this sandbox):** **real GnuCOBOL** is installed via **micromamba / conda-forge userland** (no `apt`, no root — the sandbox has unrestricted outbound network) during a **pre-warm** step into a long-lived `environment_id`; the original COBOL is compiled & run with it in-sandbox. The env is reused on stage, so the live run itself needs **no network** (the install happened at pre-warm).

**Deterministic fallback:** a pre-computed `golden_io.json` (input→output pairs captured from the *same* real GnuCOBOL run before the event); diff against that if the live run stalls. Same guarantee, no live execution.

> **Honesty point (a strength, not a hedge):** under BOTH paths the oracle is **real GnuCOBOL output**, never agent-invented — so the falsifiability / anti-objection claim holds either way. The only thing that differs between the two is *when* the real compiler ran (live on stage vs. captured pre-event).

## 4. Managed Agents configuration (verified against live docs, May 2026)

> Requires `google-genai >= 2.0.0`. `base_environment` is an **object** (not a bare
> string); `sources` mounts files at the paths the agent auto-discovers. On
> `interactions.create`, the environment is passed via **`extra_body={"environment": …}`**
> (the SDK doesn't expose a typed top-level `environment=` kwarg yet — the runnable
> cookbook uses `extra_body`).

```python
from google import genai
client = genai.Client()

# One-time: create the reusable custom agent, mounting AGENTS.md + seed skills.
client.agents.create(
    id="lazarus",
    base_agent="antigravity-preview-05-2026",   # Gemini 3.5 Flash managed agent
    system_instruction="You are LAZARUS... follow .agents/AGENTS.md.",
    base_environment={
        "type": "remote",
        "sources": [
            {"type": "inline", "target": ".agents/AGENTS.md", "content": "..."},
            {"type": "inline", "target": ".agents/skills/numeric-display-rounding/SKILL.md", "content": "..."},
        ],
    },
    # tools omitted -> defaults to code_execution + google_search + url_context
)

# Run: first call provisions a fresh sandbox; capture the server-generated env id.
itx = client.interactions.create(agent="lazarus", input=PROMPT, stream=True,
                                 extra_body={"environment": "remote"})
# follow-up turns REUSE the environment (files + forged skills + oracle binary persist):
itx2 = client.interactions.create(agent="lazarus", input=NEXT,
                                  extra_body={"environment": itx.environment_id})
```

- **State carrier:** the agent path threads state via **environment reuse** —
  `extra_body={"environment": itx.environment_id}` keeps the sandbox files (forged
  skills + the oracle binary) **alive across turns of the same session**. (`previous_interaction_id`
  is the *model*-path history carrier; its behavior on the agent path is undocumented, so we rely on the environment.)
- **Persistence is session-scoped, not eternal:** verbatim, *"Each invocation forks the
  base environment, so every run starts clean."* So a brand-new invocation does **not**
  inherit a prior run's forged skills. To bank a skill permanently, re-register the agent
  with it mounted in `base_environment` (see §2 step 7).
- **Environment lifecycle:** `"remote"` provisions a fresh sandbox (~5s); reuse the returned `environment_id` to keep state. Sandboxes auto-snapshot + stop after 15 min idle and are retained 7 days since last active (resumable by ID). 4 CPU / 16 GB (free during preview).
- **Skills are config:** `.agents/AGENTS.md` (persona + loop policy) and `.agents/skills/<name>/SKILL.md` (idiom handlers **auto-discovered at startup**). FORGE writes new ones at runtime; they re-register on the next pass via environment reuse (see §2, step 7).
- **Observable steps:** the agent streams Server-Sent Events — `step.start` / `step.delta` / `step.stop` plus `interaction.created` / `interaction.completed` — carrying `thought`, `code_execution_call/result`, and `model_output` steps. These render as the live "agent working" UI (this *is* the demo surface).

### Supported features we rely on (and ONLY these)
✅ `code_execution` (Bash/Python) · ✅ persistent filesystem · ✅ `google_search` · ✅ `url_context` · ✅ `AGENTS.md`/`SKILL.md` startup discovery · ✅ streamed `step.*` SSE events

### Explicitly NOT used (documented as unsupported by the Antigravity agent)
❌ sub-agent orchestration · ❌ `mcp` · ❌ `computer_use` · ❌ `function_calling` · ❌ `file_search` · ❌ `google_maps` · ❌ structured outputs

> **Model vs. agent-runtime (so this never reads as a contradiction):** the *model*
> `gemini-3.5-flash` supports function calling, structured output, and file search;
> the **Antigravity managed-agent runtime** we actually run exposes only
> `code_execution` + `google_search` + `url_context` + filesystem (not
> `function_calling` / `file_search` / `computer_use` / `mcp` / structured output).
> Both are true — we build to the agent runtime's matrix. This honesty is a
> deliberate strength: every primitive we demo is one the docs guarantee.
> See `docs/RESEARCH_MANAGED_AGENTS.md §3`.

## 5. Components to build

| Component | File | Owner role |
|---|---|---|
| Managed agent setup + loop driver | `src/agent.py` | Agent engineer |
| GnuCOBOL oracle + byte-diff harness | `src/differential_oracle.py` | Agent engineer |
| Live trace UI (steps + diff + terminal) | `web/` | Front-end engineer |
| `AGENTS.md` + seed skills | `.agents/` | Agent engineer |
| Golden COBOL sample + input battery | `src/sample/` | Utility/QA |
| Fallback cache (`golden_io.json`, recorded run) | `src/sample/` | Utility/QA |

## 6. Data flow for the live demo

`drop payroll.cob` → `interactions.create(stream=True)` → steps stream to UI → sandbox writes Python + compiles COBOL + runs both + pytest → RED → forge `SKILL.md` (git diff animates) → next pass re-reads `.agents/skills/` from the **same live environment** → pytest GREEN → `download` migrated module from that environment.

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Auto-iteration non-deterministic / loops forever | Hard cap iterations (≤4) with a visible counter; cached green run as fallback |
| Getting GnuCOBOL into the sandbox (no `apt`/root) | **Pre-warm: install real GnuCOBOL via `micromamba`/conda-forge userland** (no root; network is on) into a long-lived `environment_id`, reused on stage so the live run needs no network **or** fall back to `golden_io.json` captured from the same `cobc` run |
| Cold-start latency at 0:00 | Pre-warm sandbox with a `background=true` heartbeat before walking on |
| COBOL too large for clean 2-min run | Curated ~150-line module with one reproducible bug class (decimal/rounding) |
| Beta API breaking change | Pin `-preview-05-2026`; smoke-test the morning of; record backup video |
