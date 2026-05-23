# LAZARUS — Completion Design (Agent-Team Build)

> Date: 2026-05-23 · Owner: team-lead (Claude) · Status: approved, in progress
> Goal: take the LAZARUS scaffold to a complete, **verified-against-reality**, demo-ready
> Google I/O 2026 hackathon project — research + docs + runnable backend + live web UI.

## 1. Ground truth established before dispatch (2026-05-23)

Verified directly against live docs (`ai.google.dev/gemini-api/docs/...`):

- **Gemini 3.5 Flash is REAL + GA (~2026-05-19).** Model ID `gemini-3.5-flash`.
  1M context · 65k max output · thinking levels `minimal|low|medium|high`
  (default `medium`) · "thought preservation" across turns · all Gemini 3
  features **except Computer Use**.
- **Managed Agents are REAL.** Base agents: **Antigravity** (powered by Gemini 3.5
  Flash) and **Deep Research**. One API call provisions an Ubuntu sandbox
  (Python 3.12, Node 22). Environments deleted after 7 days idle. Up to 1,000 agents.
- Tools listed for Managed Agents: Google Search, Google Maps, Code execution,
  URL context, Computer Use, File Search.

## 2. Open questions the team must resolve (reality-check posture)

1. **Exact base agent ID** — code uses `antigravity-preview-05-2026`; GA may have
   dropped the `-preview`. Confirm the real string and `base_agent` value.
2. **Are `computer_use` / `file_search` actually unsupported?** Live tool list
   includes both — ARCHITECTURE.md's "Explicitly NOT used" + "single-agent honesty"
   framing may be wrong and must be corrected if so.
3. **Are `AGENTS.md` / `SKILL.md` real Managed Agents primitives?** The FORGE
   centerpiece depends on it. If not real, redesign the self-authoring beat around
   whatever the real custom-agent/skills mechanism is.
4. **Exact custom-agent + Interactions API surface** — verify `client.agents.create(...)`
   signature, `interactions.create(...)`, environment reuse, streaming/steps shape,
   and the minimum `google-genai` version.

## 3. Team roster (6 teammates + lead)

| Name | Role | Lane (files it owns) |
|---|---|---|
| `researcher-gemini` | Gemini 3.5 Flash specs deep-dive | `docs/research/findings-gemini.md` |
| `researcher-agents` | Managed Agents / Interactions API deep-dive | `docs/research/findings-agents.md` |
| `doc-keeper` | Consolidate findings → polished docs; correct stale claims | `docs/RESEARCH_*.md`, edits to `docs/ARCHITECTURE.md`, `README.md` |
| `backend-eng` | Harden `agent.py`, oracle, tests, sample, fallback | `src/`, `tests/`, `.agents/`, `requirements.txt` |
| `frontend-eng` | Live-trace web UI (steps + diff + pytest terminal + git-diff) | `web/` |
| `devils-advocate` | Challenge every premise; verify falsifiability | `docs/research/CHALLENGES.md` |

Lanes are disjoint directories so all six can edit concurrently without conflict.
Only `doc-keeper` edits shared prose docs (`ARCHITECTURE.md`/`README.md`); others
propose corrections via SendMessage.

## 4. Parallelism plan (honors "spawn now, parallel" + "verify & correct")

- **API-independent work starts immediately:** the differential oracle (pure local
  Python + GnuCOBOL), the golden COBOL sample + input battery, `golden_io.json`
  fallback, the oracle's own pytest, and the web UI shell (consumes a stable
  step-stream contract regardless of model version).
- **API-dependent work consumes findings:** `agent.py`'s Managed Agents wiring is
  reconciled to verified facts as `researcher-agents` posts them. backend-eng reads
  `docs/research/findings-agents.md` and coordinates via messages before finalizing.
- `devils-advocate` runs continuously and files blocking concerns the moment a
  load-bearing claim looks false.

## 5. Definition of done

1. `docs/RESEARCH_GEMINI_3.5.md` + `docs/RESEARCH_MANAGED_AGENTS.md` written, every
   claim cited to a live URL; stale claims in `ARCHITECTURE.md`/`README.md` corrected.
2. `src/differential_oracle.py` runs locally with a passing test suite; `golden_io.json`
   fallback present and verified.
3. `src/agent.py` reconciled to the real Managed Agents + Interactions API surface
   (correct model ID, base agent, method signatures, version pin).
4. `web/` live-trace UI runs and renders a (mocked or live) step stream + diff +
   pytest terminal + git-diff panel.
5. `docs/research/CHALLENGES.md` lists every devil's-advocate objection with a
   resolution or an explicit accepted-risk note.
6. `requirements.txt` pinned; `README.md` quick-start works end to end.
