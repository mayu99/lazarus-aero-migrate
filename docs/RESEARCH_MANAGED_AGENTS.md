# RESEARCH — Managed Agents + Interactions API

> Single source of truth for the **agent runtime** LAZARUS runs on. Owner:
> `doc-keeper` (consolidated from `docs/research/findings-agents.md`, owner
> researcher-agents). Every technical claim carries a source URL + verbatim quote
> where possible. Unconfirmed items live in **§11 Open / unverified**.
>
> Status legend: ✅ verified · ⏳ pending · ❌ corrected/false.
> Last consolidation pass: 2026-05-23 (pass 4 — consolidated researcher-agents'
> full, fully-cited writeup. All four load-bearing items RESOLVED; corrected my
> earlier pass-2/3 guesses on the base agent ID, file_search, and the streaming shape).

---

## 0. What changed in this pass (corrections to my earlier guesses)

- ✅ **Base agent ID `antigravity-preview-05-2026` is CORRECT** (verbatim in the
  cookbook + antigravity docs). My pass-2/3 "likely invented" suspicion was wrong —
  I had only fetched the generic interactions page, not the antigravity-specific docs.
- ✅ **The Antigravity agent does NOT support `file_search` or `computer_use`** (the
  seed tool list was the *generic platform* list). My pass-3 "File Search supported
  but unused" was a *model*-level fact that does NOT hold at the *agent* level.
  ARCHITECTURE's "Explicitly NOT used / unsupported" framing is **ACCURATE**.
- ✅ **Streaming uses `step.*` events**, not the model-path `content.delta` shape from
  the bundled skill. Corrected in §8.
- ✅ **`environment` is passed via `extra_body={"environment": ...}`** on
  `interactions.create`, not as a top-level kwarg.

## 1. Overview

The Gemini API **Managed Agents** feature lets one API call provision a hosted
agent that reasons, executes code, manages files, and browses the web inside a
Google-hosted Linux environment. LAZARUS uses a **single** Antigravity agent (no
multi-agent orchestration) driven through the **Interactions API**.

- ✅ One API call provisions an **Ubuntu** environment: **Python 3.12, Node.js 22,
  4 CPU cores, 16 GB RAM**, ~5s cold provision.
  Source: <https://ai.google.dev/gemini-api/docs/agent-environment.md.txt>
- ✅ Antigravity is **"built on Gemini 3.5 Flash"** (input 1,048,576 / compacted
  ~135k, output 65,536; inputs text+image, output text).
  Source: Managed Agents launch blog ·
  <https://blog.google/innovation-and-ai/technology/developers-tools/managed-agents-gemini-api/>
- ✅ Interactions API is in **Beta** — pin versions, re-test the morning of.
  Source: <https://ai.google.dev/gemini-api/docs/interactions.md.txt>

## 2. Model / Agent IDs

- ✅ **Two base managed agents:** **Antigravity** (Gemini 3.5 Flash) and **Deep Research**.
- ✅ **Base agent ID: `antigravity-preview-05-2026`** — VERIFIED verbatim across
  `antigravity-agent.md.txt`, `custom-agents.md.txt`, `managed-agents-quickstart.md.txt`,
  and the official cookbook (`AGENT = "antigravity-preview-05-2026"`). The `-preview-`
  suffix is still present as of 2026-05-23. The **same string** is used both for
  `agent=` (Interactions API) and `base_agent=` (`agents.create`).
  Sources: <https://ai.google.dev/gemini-api/docs/antigravity-agent.md.txt> ·
  <https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_managed_agents.ipynb>

## 3. Capabilities (tools) — Antigravity agent specifically

> ⚠️ **MODEL capability vs MANAGED-AGENT-RUNTIME capability are different things —
> state this distinction wherever it could read as a contradiction:**
> the *model* `gemini-3.5-flash` supports function calling, structured output, and
> file search (see `RESEARCH_GEMINI_3.5.md §3`); the *Antigravity managed agent
> runtime* exposes only `code_execution` + `google_search` + `url_context` +
> filesystem — **not** `function_calling` / `file_search` / `computer_use` / `mcp` /
> structured output. These are **managed-agent limitations, not model ones.** Both
> statements are correct and not in conflict. Verbatim (antigravity-agent doc):
> *"file_search, computer_use, google_maps, function_calling and mcp are not yet
> supported."*
>
> The generic platform advertises still more tools (Google Maps, Computer Use, File
> Search); the **Antigravity agent** supports the narrower set below. Use THIS list.
> Source (verbatim): <https://ai.google.dev/gemini-api/docs/antigravity-agent.md.txt>

- ✅ **Supported:** `code_execution`, `google_search`, `url_context`, **Filesystem**
  (via the persistent `environment`).
- ✅ **NOT supported:** `file_search`, `computer_use`, `google_maps`,
  `function_calling`, `mcp`.
- ✅ Also **not supported by the agent:** `temperature` / `top_p` / `top_k` /
  `stop_sequences` / `max_output_tokens`, **structured outputs**, and audio/video/doc
  inputs (**text + image only**).
- ✅ `background=True` requires `store=True`.

> ✅ **C2/C4 RESOLVED:** ARCHITECTURE.md's claim that `computer_use` / `file_search` /
> `mcp` / `function_calling` / sub-agents are "Explicitly NOT used / unsupported" is
> **ACCURATE for the Antigravity agent** and is a genuine honesty strength — keep it.
> (Note: this differs from the *model* `gemini-3.5-flash`, which DOES list File Search
> and structured outputs — but the managed agent does not expose them. See
> `RESEARCH_GEMINI_3.5.md §3`.)

## 4. Skills / self-authoring (`AGENTS.md` / `SKILL.md`) — the FORGE beat

> ✅ **C1/C3 RESOLVED: these ARE real primitives**, with one honest caveat about the
> live "hot-reload" timing. This is the $5k-bonus centerpiece; word it precisely.

- ✅ **`AGENTS.md` auto-loads as system instructions on startup** (verbatim,
  `custom-agents.md.txt`): *"The agent automatically loads `.agents/AGENTS.md`
  (or `/.agents/AGENTS.md`) from the environment as system instructions on startup."*
- ✅ **`SKILL.md` files auto-discover on startup** (verbatim): *"Place them under
  `.agents/skills/<skill-name>/SKILL.md` and the harness auto-discovers and registers
  them."*; *"Skills loaded from `.agents/skills/` and `/.agents/skills/` are both
  discovered automatically."* A `SKILL.md` is YAML frontmatter (`---\nname:\n---`) +
  markdown body.
- ✅ The launch blog confirms the model: *"define everything in markdown files like
  AGENTS.md and SKILL.md and register them as a managed agent."*
- ✅ **Persistence is VERIFIED — but SESSION-SCOPED, not eternal.**
  - Within a session (reusing the same `environment_id`): Blog: *"Each interaction
    creates or receives an environment, which you can use in follow-up calls to resume
    the session with all files and state intact."* `agent-environment.md.txt`:
    *"Packages installed during an interaction persist when you reuse the same
    `environment_id`."* Cookbook: agent writes `knowledge.md` in turn 1, recalls it in turn 2.
  - ⚠️ **A NEW invocation starts CLEAN.** Verbatim (`managed-agents-quickstart.md.txt`):
    *"Each invocation forks the base environment, so every run starts clean."* So a
    fresh agent run does **NOT** inherit files/skills forged in a previous run's
    environment unless you explicitly reuse that `environment_id` or re-register the agent.
    Source: <https://ai.google.dev/gemini-api/docs/managed-agents-quickstart.md.txt>
  - To make a forged skill **permanent** across future runs: **re-register the agent**
    with the skill mounted in `base_environment` (`agents.create(..., base_environment=
    {"type":"remote","sources":[…SKILL.md…]})`), or fork from the saved `environment_id`
    via `base_environment={"env_id": env_id}`.

> ⚠️ **DOC-CONSUMER NOTE:** do not write "skills persist forever / accumulate dialect
> coverage across runs / persist for future runs" — that is an OVERCLAIM (devils-advocate
> escalation #2). The honest framing is "stays live for the session you keep reusing;
> fresh runs fork clean; re-register to bank it permanently."

> ⚠️ **FORGE CAVEAT — be precise on stage (lead's framing guidance, 2026-05-23):**
> Auto-load/auto-discovery is documented as a **startup** event. There is **NO
> documented statement** that a `SKILL.md` *authored by the agent mid-run* is
> *auto-reloaded into its instruction context* on a continued interaction (confirmed
> ABSENT from custom-agents, agent-environment, blog, and cookbook). Treat
> mid-interaction hot-reload as `[UNVERIFIED]`.
>
> **VERIFIED-SAFE MECHANISM to describe everywhere (ARCHITECTURE §2/§4, README,
> DEMO_SCRIPT narration):** the agent *writes the skill, persists it in the sandbox,
> reuses the environment, and re-reads it on the next pass.* Concretely: (1) agent
> writes `/.agents/skills/<idiom>/SKILL.md` into the env; (2) the file persists on
> disk (verified); (3) the next run starts as a **fresh startup against that env** —
> either reuse `extra_body={"environment": env_id}` and instruct the agent to read
> `/.agents/skills/`, OR **fork** a refreshed agent with
> `base_environment={"env_id": env_id}` so startup discovery re-registers the forged
> skill. **Do NOT claim mid-interaction hot-reload / "auto-loads forever."**

## 5. SDK usage

> Python SDK: `pip install -U 'google-genai>=2.0.0'` (cookbook). JS/TS:
> `@google/genai >= 2.0.1`. `from google import genai` → `genai.Client(api_key=...)`.
> ⚠️ **REPO ACTION (backend-eng, task #5):** `requirements.txt` + `src/agent.py`
> pin `>=1.55.0` — bump to `>=2.0.0`. The `1.55.0` in the interactions docs is the
> *model*-interactions path, not the managed-agents path.

### 5.1 Create a custom agent (VERIFIED — `custom-agents.md.txt`, verbatim)

```python
agent = client.agents.create(
    id="data-analyst",
    base_agent="antigravity-preview-05-2026",
    system_instruction="You are a data analyst. Always include visualizations and export results as PDF.",
    base_environment={"type": "remote", "sources": [
        {"type": "inline", "target": ".agents/AGENTS.md", "content": "..."},
        {"type": "inline", "target": ".agents/skills/slide-maker/SKILL.md",
         "content": "---\nname: slide-maker\n---\n# Slide Maker\n..."},
        {"type": "repository", "source": "https://github.com/my-org/analysis-templates",
         "target": "/workspace/templates"}]},
)
```

- **Params:** `id`, `base_agent`, `system_instruction`, `base_environment`.
- **`base_environment`:** `{type:"remote", sources:[...], network?}` OR
  `{env_id:"<existing>"}` (fork an existing environment — useful for FORGE).
- **Source object:** `type` (`"inline"` | `"repository"`), `target` (path),
  `content` (inline) | `source` (git URL).
- **Lifecycle helpers:** `client.agents.list().agents` (iterate `.id`),
  `client.agents.get(id=...)`, `client.agents.delete(id=...)`.

Fork-from-environment variant (the FORGE reload path):
```python
client.agents.create(id="my-forked-agent", base_agent="my-gemini-api-agent",
    system_instruction="...", base_environment={"env_id": interaction.environment_id})
```

### 5.2 Run an agent interaction (VERIFIED — cookbook, verbatim)

```python
from google import genai
client = genai.Client(api_key=GEMINI_API_KEY)
AGENT = "antigravity-preview-05-2026"

# single shot — provision a fresh env:
interaction = client.interactions.create(agent=AGENT, input="...",
    extra_body={"environment": "remote"})

# reuse env (files + installed packages persist):
turn2 = client.interactions.create(agent=AGENT, input="...",
    extra_body={"environment": interaction.environment_id})

# inject a file at call time:
client.interactions.create(agent=AGENT, input="Read /workspace/data.csv...",
    extra_body={"environment": {"type": "remote", "sources": [
        {"type": "inline", "content": csv_data, "target": "/workspace/data.csv"}]}})

# network allowlist + credential injection (e.g. to curl the Gemini API):
client.interactions.create(agent=AGENT, input="curl the Gemini API...",
    extra_body={"environment": {"type": "remote", "network": {"allowlist": [
        {"domain": "generativelanguage.googleapis.com",
         "transform": [{"x-goog-api-key": GEMINI_API_KEY}]}]}}})
```

- ✅ **`extra_body` is a direct kwarg** to `create()` — NOT inside `http_options`/`config`.
  Docs *pages* show top-level `environment="remote"`, but the SDK doesn't expose it
  typed yet; the runnable cookbook + SDK README confirm `extra_body={"environment": ...}`.
- ✅ **Env id:** `interaction.environment_id`.
- ⚠️ **Reading the result:** `interaction.output_text` is a convenience accessor
  (quickstart), but the **API reference says there is no `output_text` on the resource**
  — the safest path is to iterate `steps` for the final `model_output` content (see §8).
- ⚠️ **`previous_interaction_id`:** model path only; `[UNVERIFIED]` for the agent path
  (the agent path carries state via **environment reuse**, and `previous_interaction_id`
  is ABSENT from the agents cookbook). For LAZARUS, thread state via `environment_id`.

## 6. Status values

- ✅ Verbatim (API reference): `in_progress | requires_action | completed | failed |
  cancelled | incomplete | budget_exceeded`.
  Source: <https://ai.google.dev/static/api/interactions.md.txt>

## 7. Environment lifecycle

- ✅ Provision via `extra_body={"environment":"remote"}`; ~5s cold start; id at
  `interaction.environment_id`.
- ✅ Reuse via `extra_body={"environment": env_id}` — files + installed packages persist.
- ✅ Idle (verbatim): *"Auto-snapshot and stopped after 15 minutes of inactivity."*
- ✅ Retention (verbatim): *"Retained for 7 days since last active. Can be resumed by
  passing its ID."* (This corrects the looser seed phrasing "permanently deleted after
  7 days of inactivity.")
- ✅ Resources (verbatim): *"CPU: 4 cores; Memory: 16 GB"*; Ubuntu + Py3.12 + Node22.
  Compute is free during preview.
  Source: <https://ai.google.dev/gemini-api/docs/agent-environment.md.txt>
- ⏳ "Up to 1,000 managed agents" — **[UNVERIFIED]**, dropped from the verified set
  (researcher-gemini QA: not stated in `agent-environment.md.txt`). Do not cite this
  number until a primary source is found.

> ✅ ARCHITECTURE's "4 CPU / 16 GB", "~5s provision", "auto-snapshot after 15 min idle",
> "retained 7 days" are all CONFIRMED.

## 8. Streaming / steps shape (for the live UI)

> ✅ This drives the demo's "agent working" trace. Use the **agent-path `step.*`
> shape** below — NOT the model-path `content.delta` shape from the bundled skill.

Stream loop (cookbook, verbatim):
```python
stream = client.interactions.create(agent=AGENT, input="...", stream=True,
    extra_body={"environment": "remote"})
for event in stream:
    if event.event_type in ("interaction.created","step.start","step.stop","interaction.completed"):
        print(f"[{event.event_type}]")
    elif event.event_type == "step.delta":
        if hasattr(event.delta, "text") and event.delta.text:
            print(event.delta.text, end="", flush=True)
```

- ✅ **Event types** (`event.event_type`, reference): `step.start`, `step.delta`,
  `step.stop`, `interaction.created`, `interaction.completed`,
  `interaction.status_update`, `error`.
- ✅ **Chunk fields:** `event_type`, `event_id` (resume token), `interaction_id`,
  `status`, `index`, `step` (full Step on start/stop), `delta` (`{type, text}` on `step.delta`).
- ✅ **Step types** (`event.step.type`, verbatim shapes):
  - `user_input` → `{type, content:[{type:"text", text}]}`
  - `thought` → `{type, summary:[{type:"text", text}], signature}`
  - `code_execution_call` → `{type, id, arguments:{code, language}, signature}`
  - `code_execution_result` → `{type, call_id, result, is_error, signature}`
  - `model_output` → `{type, content:[{type:"text", text}]}`
- ⚠️ **For frontend-eng:** render the streamed `step.*` events (thoughts, code-exec
  calls/results, model_output). ARCHITECTURE/README's `interaction.steps` wording is
  close to correct — the agent path really is step-based — but the precise event names
  are `step.start|delta|stop`, not a `steps` array field.
  Source: <https://ai.google.dev/static/api/interactions.md.txt>

## 9. Download produced files

Whole-env tarball via the Files API (cookbook, verbatim):
```python
url = f"https://generativelanguage.googleapis.com/v1beta/files/environment-{env_id}:download?alt=media"
# curl -L -s -o snapshot.tar -H "x-goog-api-key: {KEY}" {url}
import tarfile
with tarfile.open("snapshot.tar") as tar: tar.extractall("extracted")
```
Extract `/workspace/...` for the migrated module. There is **no**
`client.environments.download()` helper.

## 10. Pricing / quota

- ✅ **Pay-as-you-go** "based on Gemini model tokens and tool usage"; a run typically
  consumes **100k–3M tokens**; env compute **not billed during preview**.
  ("Up to 1,000 managed agents" was dropped — [UNVERIFIED], see §7.)
- ✅ Interaction storage: paid 55 days / free 1 day (`store=true` default).
- ⏳ Exact $ per token for the Antigravity agent — defer to the `gemini-3.5-flash`
  token pricing in `RESEARCH_GEMINI_3.5.md §5`.
  Sources: <https://ai.google.dev/gemini-api/docs/agents.md.txt> · launch blog.

## 11. Sources

- Agents overview: <https://ai.google.dev/gemini-api/docs/agents.md.txt>
- Managed Agents quickstart: <https://ai.google.dev/gemini-api/docs/managed-agents-quickstart.md.txt>
- Custom agents: <https://ai.google.dev/gemini-api/docs/custom-agents.md.txt>
- Agent environment: <https://ai.google.dev/gemini-api/docs/agent-environment.md.txt>
- Antigravity agent: <https://ai.google.dev/gemini-api/docs/antigravity-agent.md.txt>
- Antigravity model card: <https://ai.google.dev/gemini-api/docs/models/antigravity-preview-05-2026.md.txt>
- Interactions API: <https://ai.google.dev/gemini-api/docs/interactions.md.txt>
- Interactions API reference (SSE/step shapes): <https://ai.google.dev/static/api/interactions.md.txt>
- Managed Agents launch blog: <https://blog.google/innovation-and-ai/technology/developers-tools/managed-agents-gemini-api/>
- Official cookbook (runnable source of truth):
  <https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_managed_agents.ipynb>
- Python SDK README: <https://github.com/googleapis/python-genai>
- Skills repo (mountable as a `repository` source): <https://github.com/google-gemini/gemini-skills>

## 12. Open / unverified

All four load-bearing items are now RESOLVED (§2, §3, §4). Remaining minor gaps:

- [ ] `previous_interaction_id` behavior on the **agent** path (use `environment_id`
      reuse instead; `previous_interaction_id` is the model-path state carrier).
- [ ] Whether `interaction.output_text` exists on the agent resource (reference says
      no; iterate `steps` for `model_output` to be safe).
- [ ] Exact $ per token for the Antigravity agent (defer to gemini-3.5-flash pricing).
- [ ] Mid-interaction hot-reload of an agent-authored `SKILL.md` (use the verified-safe
      env-reuse / fork pattern in §4 instead — do not claim hot-reload).
