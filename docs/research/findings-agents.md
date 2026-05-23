# Findings — Managed Agents + Interactions API (owner: researcher-agents)

> Append verified facts here, each with a **source URL** and a verbatim quote where
> possible. Mark anything uncertain `[UNVERIFIED]`. Lead reconciles into
> `docs/RESEARCH_MANAGED_AGENTS.md` via doc-keeper.

> **STATUS: ALL CRITICAL ITEMS RESOLVED (2026-05-23, researcher-agents).** Every fact has a
> source + verbatim quote, or is marked `[UNVERIFIED]`.

## Sources (all real, fetched 2026-05-23)
- Agents overview: https://ai.google.dev/gemini-api/docs/agents.md.txt
- Managed Agents quickstart: https://ai.google.dev/gemini-api/docs/managed-agents-quickstart.md.txt
- Custom agents: https://ai.google.dev/gemini-api/docs/custom-agents.md.txt
- Agent environment: https://ai.google.dev/gemini-api/docs/agent-environment.md.txt
- Antigravity agent: https://ai.google.dev/gemini-api/docs/antigravity-agent.md.txt
- Antigravity model card: https://ai.google.dev/gemini-api/docs/models/antigravity-preview-05-2026.md.txt
- Interactions API: https://ai.google.dev/gemini-api/docs/interactions.md.txt
- Interactions quickstart: https://ai.google.dev/gemini-api/docs/interactions/quickstart.md.txt
- Interactions API reference (SSE/step shapes): https://ai.google.dev/static/api/interactions.md.txt
- Managed Agents launch blog: https://blog.google/innovation-and-ai/technology/developers-tools/managed-agents-gemini-api/
- **Official runnable cookbook (source of truth for working code):**
  https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_managed_agents.ipynb
- Official Python SDK README: https://github.com/googleapis/python-genai

## ⚠️ TOP RECONCILIATION NOTES (read first)
1. **`interactions.create` takes `environment` via `extra_body`, NOT a top-level kwarg.** Docs
   *pages* show top-level `environment="remote"`, but the SDK doesn't expose it typed yet; the
   cookbook (runnable) + SDK README confirm `extra_body={"environment": ...}`. `agents.create`
   IS different — `base_environment` is a real top-level typed param.
2. **Pin `google-genai>=2.4.0`** (CORRECTED — see SDK section). `client.agents` + the Environment
   API ship in 2.4.0; 1.55.0 (interactions debut) and the cookbook's 2.0.0 are BOTH too low for
   `agents.create`. REPIN requirements.txt + agent.py from 1.55.0 → 2.4.0.
3. **Base agent ID still has `-preview-`:** `antigravity-preview-05-2026`. Repo string is correct.
4. **FORGE caveat (C3):** a runtime-authored `SKILL.md` persists on disk when the environment is
   reused (verified); auto-RELOAD into the agent's instruction context mid-flight is `[UNVERIFIED]`
   — use the safe pattern below.

## Seed-fact corrections
- Two base managed agents: **Antigravity** (Gemini 3.5 Flash) + **Deep Research**. ✅ correct.
- One API call provisions an **Ubuntu** sandbox: **Python 3.12, Node.js 22, 4 CPU cores, 16 GB RAM**,
  ~5s cold provision. ✅ (agent-environment.md.txt).
- ❌ CORRECTION to the seed tool list: that list is the *generic platform* tools. The **Antigravity
  agent specifically does NOT support `computer_use`, `file_search`, `google_maps`, `function_calling`,
  `mcp`**. It supports only `code_execution`, `google_search`, `url_context`, Filesystem. (See C4.)
- ❌ CORRECTION: environments are **auto-snapshot+stopped after 15 min idle** and **retained 7 days
  since last active** (resumable by ID) — not "permanently deleted after 7 days of *inactivity*"
  loosely. Up to 1,000 agents ✅.

## CRITICAL — RESOLVED

### C1 — Base agent ID ✅ `antigravity-preview-05-2026`
Verbatim across antigravity-agent.md.txt, custom-agents.md.txt, managed-agents-quickstart.md.txt,
and the cookbook (`AGENT = "antigravity-preview-05-2026"`). Same string for `agent=` (interactions)
and `base_agent=` (agents.create). The `-preview-` is still present as of 2026-05-23.

### C2 — `client.agents.create(...)` ✅
Verbatim (custom-agents.md.txt):
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
Cookbook fork-from-environment variant (useful for FORGE):
```python
client.agents.create(id="my-forked-agent", base_agent="my-gemini-api-agent",
    system_instruction="...", base_environment={"env_id": interaction.environment_id})
```
- **Params:** `id`, `base_agent`, `system_instruction`, `base_environment`.
- **`base_environment`:** `{type:"remote", sources:[...], network?}` OR `{env_id:"<existing>"}` (fork).
- **Source object:** `type` (`"inline"`|`"repository"`), `target` (path), `content` (inline) | `source` (git URL).
- **Lifecycle:** `client.agents.list().agents` (iter `.id`); `client.agents.get(id=...)`;
  `client.agents.delete(id=...)`.

### C3 — AGENTS.md / SKILL.md real? ✅ YES (one honest caveat)
- Blog (verbatim): *"define everything in markdown files like AGENTS.md and SKILL.md and register
  them as a managed agent"*.
- custom-agents.md.txt (verbatim): *"The agent automatically loads `.agents/AGENTS.md`
  (or `/.agents/AGENTS.md`) from the environment as system instructions on startup."*;
  *"Place them under `.agents/skills/<skill-name>/SKILL.md` and the harness auto-discovers and
  registers them."*; *"Skills loaded from `.agents/skills/` and `/.agents/skills/` are both
  discovered automatically."* SKILL.md = YAML frontmatter (`---\nname:\n---`) + markdown body.
- **Persistence VERIFIED.** Blog: *"Each interaction creates or receives an environment, which you
  can use in follow-up calls to resume the session with all files and state intact."*
  agent-environment.md.txt: *"Packages installed during an interaction persist when you reuse the
  same `environment_id`."* Cookbook: agent writes `knowledge.md` in turn 1, recalls it in turn 2.

**⚠️ FORGE CAVEAT (be honest on stage):** auto-load is documented as a **startup** event. There is
**SKILL.md discovery is a STARTUP/SCAN event — NOT mid-interaction (RESOLVED 2026-05-23).**
custom-agents.md.txt verbatim: *"Skills loaded from `.agents/skills/` and `/.agents/skills/` are
both discovered automatically."* · *"Place them under `.agents/skills/<skill-name>/SKILL.md` and the
harness auto-discovers and registers them."* · *"The Antigravity runtime scans `.agents/` (and the
root of the environment) for these files."* All three describe a point-in-time scan at init. There is
**ZERO** "during execution / on demand / at runtime / re-scanned mid-interaction" language anywhere
(confirmed ABSENT in custom-agents, antigravity-agent, agent-environment, blog, cookbook). So a
SKILL.md the agent writes mid-run is **NOT** auto-registered as a skill within that same interaction.

➡️ **FORGE self-heal is honestly a TWO-TURN loop:**
- Turn 1: agent hits unknown idiom → writes `/.agents/skills/<idiom>/SKILL.md` into the env (tests RED).
- Turn 2: a NEW interaction starts against the SAME `environment_id` (file persists on disk) → that
  interaction's STARTUP scan registers the new skill → agent retries → GREEN.
- Within a single turn the agent can still USE what it wrote by `code_execution` reading the file
  directly (it's on disk), but it is NOT a registered managed "skill" until the next interaction's scan.
- To bank the skill PERMANENTLY: re-register the agent with it mounted in `base_environment`
  (or fork `base_environment={"env_id": env_id}` so startup re-discovers it).
- ❌ DO NOT claim "authors a skill and the harness hot-loads it mid-thought in the same turn" —
  that's an OVERCLAIM / `[UNVERIFIED]`. The demoable, honest framing is the 2-turn write→rescan→retry.
- NB: an "...discovered automatically during execution" phrase may appear in SDK *guides*; it was NOT
  found in the API docs and most likely means on-demand invocation of ALREADY-registered skills
  (progressive disclosure), not runtime re-scanning of newly authored files. Quote the API-doc
  scan/auto-discover/register lines, which are unambiguous.

### C4 — computer_use / file_search ✅ NOT supported (repo honesty claim accurate)
antigravity-agent.md.txt (verbatim): **Supported** = `code_execution`, `google_search`,
`url_context`, Filesystem (via `environment`). **NOT supported** = `file_search`, `computer_use`,
`google_maps`, `function_calling`, `mcp`. Also unsupported: temperature/top_p/top_k/stop_sequences/
max_output_tokens, **structured outputs**, audio/video/doc inputs (**text+image only**).
`background=True` requires `store=True`.

## Interactions API — usage (RESOLVED)
Runnable forms (cookbook, verbatim):
```python
from google import genai
client = genai.Client(api_key=GEMINI_API_KEY)
AGENT = "antigravity-preview-05-2026"

interaction = client.interactions.create(agent=AGENT, input="...",
    extra_body={"environment": "remote"})                       # single shot
turn2 = client.interactions.create(agent=AGENT, input="...",
    extra_body={"environment": turn1.environment_id})           # reuse env (persists)
client.interactions.create(agent=AGENT, input="Read /workspace/data.csv...",
    extra_body={"environment": {"type": "remote", "sources": [  # inject file at call time
        {"type": "inline", "content": csv_data, "target": "/workspace/data.csv"}]}})
client.interactions.create(agent=AGENT, input="curl the Gemini API...",
    extra_body={"environment": {"type": "remote", "network": {"allowlist": [  # net allowlist+creds
        {"domain": "generativelanguage.googleapis.com",
         "transform": [{"x-goog-api-key": GEMINI_API_KEY}]}]}}})
```
- `extra_body` is a **direct kwarg** to `create()` (not in `http_options`/`config`).
- `environment_id` → `interaction.environment_id`.
- Read result: `interaction.output_text` (convenience, quickstart) — BUT API reference says no
  `output_text` on the resource; safest is to iterate steps for the final `model_output` content.
- `previous_interaction_id`: model path only / `[UNVERIFIED]` for agent path (agent path uses
  environment reuse; ABSENT from agents cookbook).
- Status enum (reference, verbatim): `in_progress | requires_action | completed | failed |
  cancelled | incomplete | budget_exceeded`.

## Streaming / `interaction.steps` shape (RESOLVED — live UI)
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
- **event types** (`event.event_type`, reference): `step.start`, `step.delta`, `step.stop`,
  `interaction.created`, `interaction.completed`, `interaction.status_update`, `error`.
- **chunk fields**: `event_type`, `event_id` (resume token), `interaction_id`, `status`, `index`,
  `step` (full Step on start/stop), `delta` (`{type, text}` on step.delta).
- **step types** (`event.step.type`, reference verbatim shapes):
  - `user_input` → `{type, content:[{type:"text", text}]}`
  - `thought` → `{type, summary:[{type:"text", text}], signature}`
  - `code_execution_call` → `{type, id, arguments:{code, language}, signature}`
  - `code_execution_result` → `{type, call_id, result, is_error, signature}`
  - `model_output` → `{type, content:[{type:"text", text}]}`
- ⚠️ The `gemini-interactions-api` SKILL shows an OLDER model-path shape (`content.delta`); use the
  `step.*` shape above for the agent path.
- ⚠️ TERMINAL EVENT: `interaction.completed` carries `event.interaction` but **"with empty outputs to
  reduce the payload size"** (API reference, verbatim). The completed event does NOT contain full
  text/steps. To get the authoritative final object after a stream, call
  `client.interactions.get(event.interaction_id)` (every event carries `event.interaction_id`), OR
  accumulate text from `step.delta` + build the timeline from `step.start`/`step.stop` as they arrive
  (cookbook approach). `output_text` is NOT a documented resource field — read final text from the last
  `model_output` step's `content[].text`; read env id from `interaction.environment_id`.
- **`interaction.steps` IS a real field** — but on the RETURNED/fetched interaction OBJECT
  (non-streaming), not a stream event name. Cookbook (verbatim, non-streaming):
  `for step in interaction.steps: step.type / step.name / step.arguments / step.content[].text`.
  So the repo's "interaction.steps as the demo surface" is VALID for the final/fetched object; for
  LIVE streaming assemble the same picture from `step.start` / `step.delta` / `step.stop`.

## Environment lifecycle (RESOLVED)
- Provision via `extra_body={"environment":"remote"}`; ~5s cold start; env id `interaction.environment_id`.
- Reuse: `extra_body={"environment": env_id}`. Persists files + installed packages (verbatim above).
- Idle (verbatim): *"Auto-snapshot and stopped after 15 minutes of inactivity."*
- Retention (verbatim): *"Retained for 7 days since last active. Can be resumed by passing its ID."*
- Resources (verbatim): *"CPU: 4 cores; Memory: 16 GB"*; Ubuntu + Py3.12 + Node22. Compute free in preview.

### ⚠️ TWO PERSISTENCE BEHAVIORS — do not confuse (RESOLVED 2026-05-23)
managed-agents-quickstart.md.txt has BOTH of these statements; they apply to DIFFERENT patterns:
- **Invoking a SAVED agent by ID forks the base env each time** (verbatim): *"Each invocation forks
  the base environment, so every run starts clean."* → a conda install / forged SKILL.md from one run
  does NOT carry to the next on this path. To bank a tool/skill permanently here, bake it into
  `base_environment` at `agents.create` time.
- **Reusing an EXPLICIT environment_id RESUMES the same sandbox** (verbatim): *"Files from turn 1
  (`fibonacci.txt`) persist in turn 2"* when you "Pass [the environment_id] ... to resume." →
  installed packages + files PERSIST.
- **Practical rule for LAZARUS:** keep ONE long-lived `environment_id` for the whole demo session
  (pre-warm GnuCOBOL install → COBOL compile → migration → tests → FORGE all in that same ENV via
  `extra_body={"environment": ENV}`). Do NOT pre-warm into ENV then expect a fresh
  `environment="remote"` run (or a fresh invoke-by-saved-agent-id) to inherit it — those fork clean.
- **FORGE corollary:** a forged SKILL.md persists across runs only while you reuse the same env_id;
  to make it permanent, re-register the agent with it mounted in `base_environment`. (Never claim
  "persists forever / accumulates across runs" — that's an overclaim. See devils-advocate verdict.)

## Download produced files (RESOLVED)
Whole-env tarball via Files API (cookbook, verbatim):
```python
url = f"https://generativelanguage.googleapis.com/v1beta/files/environment-{env_id}:download?alt=media"
# curl -L -s -o snapshot.tar -H "x-goog-api-key: {KEY}" {url}
import tarfile
with tarfile.open("snapshot.tar") as tar: tar.extractall("extracted")
```
Extract `/workspace/...` for the migrated module. No `client.environments.download()` helper.

## SDK / install (RESOLVED — exact floor from the official changelog)
**`pip install -U 'google-genai>=2.4.0'`.** `from google import genai` → `client = genai.Client(api_key=...)`.
Exact version archaeology (github.com/googleapis/python-genai/blob/main/CHANGELOG.md, verbatim):
- **1.55.0** (2025-12-11): "Add the Interactions API" — interactions DEBUT (this is where the repo's
  1.55.0 pin came from; it's too low for everything below).
- **2.0.0** (2026-05-07): BREAKING (interactions only) — "Add steps for interactions" + "Rename SSE
  events to interaction.created and interaction.completed". → the `step.*` / `interaction.completed`
  streaming schema only exists from 2.0.0. A 1.55.0 pin breaks the live trace.
- **2.3.0** (2026-05-15): "Interaction.{output_text,output_image,...}" → `interaction.output_text` added.
- **2.4.0** (2026-05-17): "Support Agent and Environment APIs" → **`client.agents`
  (create/get/list/delete) + the Environment API ship HERE**. Below 2.4.0, `client.agents` does not exist.
➡️ **Floor = 2.4.0** (covers client.agents + environment + step.* SSE + output_text). REPIN
requirements.txt + agent.py: `google-genai>=1.55.0` → `google-genai>=2.4.0`. (Cookbook's 2.0.0 is
also too low for client.agents.)

## Pricing / quota (RESOLVED)
- agents.md.txt/blog: *"pay-as-you-go ... based on Gemini model tokens and tool usage"*, *"typically
  consuming 100k to 3M tokens"* per run; *"up to 1,000 managed agents"*; env compute not billed in preview.
- Interaction storage: paid 55 days / free 1 day (interactions.md.txt; `store=true` default).
- Exact $ per token for the Antigravity agent: `[UNVERIFIED]` — defer to gemini-3.5-flash token
  pricing in findings-gemini.md.

## Underlying model (RESOLVED)
Antigravity *"built on Gemini 3.5 Flash"* (blog). Context window: input 1,048,576 (compacted ~135k),
output 65,536; inputs text+image, output text (model card).

## Cookbook / reference examples
- Managed agents quickstart notebook (all code above):
  https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_managed_agents.ipynb
- Skills repo mounted as a `repository` source: https://github.com/google-gemini/gemini-skills
  (target `/.agents/skills`).
- Community Antigravity-compatible SKILL.md skills: https://github.com/cnemri/google-genai-skills

## ⚠️ PRODUCT DISTINCTION — ai.google.dev vs docs.cloud.google.com (RESOLVED 2026-05-23)
There are TWO different Managed-Agents products. **Do not mix their docs.**

| | **ai.google.dev Gemini API Managed Agents (Antigravity)** ← HACKATHON | docs.cloud.google.com **Gemini Enterprise Agent Platform** |
|---|---|---|
| Auth | **API key** (hackathon hands out Gemini API keys) | **GCP project** (`projects/{id}/locations/{loc}`) |
| Python / Node | **3.12 / 22** | 3.11 / 20 |
| Network default | **Unrestricted outbound** | **Isolation ON by default** (allowlist to enable) |
| Retention | "7 days since last active" | 7-day TTL, reset each interaction |
| Root/sudo | not documented (assume none) | verbatim: *"The container lacks privileged administrative credentials or permissions."* |

**The hackathon API key is governed by the ai.google.dev docs.** (devils-advocate's "Python 3.11 /
Node 20 / network-off" came from the Enterprise GCP product — the wrong product for us.)
- Enterprise sandbox doc: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/sandbox-environment

## Sandbox capability facts for the LIVE-COMPILE / GnuCOBOL beat (RESOLVED)
- **code_execution = real bash** (antigravity-agent.md.txt, verbatim): *"Run Bash, Python, and
  Node.js commands. Install packages, run tests, build apps."* and *"Run shell commands (bash,
  Python, Node) with stdout/stderr capture."* curl & wget pre-installed.
- **Network** (agent-environment.md.txt, verbatim): *"By default, environments have unrestricted
  outbound network access."* → can reach pip/npm/conda/apt mirrors.
- **Runtime install**: documented = `pip install` / `npm install`; "Install packages ... build apps".
  **Root/sudo NOT documented → `apt-get` is the RISKY path; do not rely on it.**
- **Binary mount via `sources` is BLOCKED** (agent-environment.md.txt, verbatim): *"The agent is
  currently constrained to reading text and image files. Binary file support is not yet available."*
  Source types: `inline` (text, ≤1MB/file, ≤2MB total), `repository` (git, ≤500MB), `gcs` (≤2GB).
  → CANNOT base64-mount a precompiled `cobc`. The "ship a prebuilt binary via sources" escape hatch is dead.
- **VERDICT — live-compile SURVIVES** via code_execution(bash) at runtime + unrestricted network,
  NOT via sources. Recommended no-root install of GnuCOBOL: **micromamba/conda from conda-forge into
  a `/workspace` prefix** (userland, persists in env); ALT = build from source `--prefix=/workspace`
  (needs gcc+gmp, likely present, `[UNVERIFIED]`). Build a FALLBACK: pre-capture COBOL ground-truth
  output offline and ship as inline TEXT sources to keep the differential-oracle claim honest if
  live `cobc` install ever fails. (Detailed verification = task #8.)

## TASK #8 — No-root live-install of GnuCOBOL in the antigravity sandbox (RESOLVED 2026-05-23)

### Verified facts
- **`conda-forge/gnucobol-feedstock` EXISTS** (github.com/conda-forge/gnucobol-feedstock, maintainer
  @pavelzw, package GPL-3.0). Package name = **`gnucobol`**, builds for **linux-64** (+ osx). Install:
  `conda install -c conda-forge gnucobol`. Provides the `cobc` compiler. ✅ resolves the prior
  `[UNVERIFIED]` "is gnucobol on conda-forge" assumption.
- **Why conda is the right path:** `cobc` translates COBOL→C and then **invokes a C compiler at
  COMPILE time** (gnucobol FAQ, verbatim: *"GnuCOBOL compiles COBOL into C then compiles the
  intermediate code with the configured C compiler, usually gcc, into assembler for object code,
  linked into executable machine code."*). So compiling COBOL in-sandbox needs a C compiler + libcob
  + gmp PRESENT. The **conda `gnucobol` package pulls its own compiler/libcob/gmp as dependencies**,
  so it works even if the sandbox has no system gcc — sidesteps the gcc-presence question entirely.
- **micromamba = userland, no root.** Official installer places it in `~/.local/bin`. Static binary,
  no root needed. (mamba-org/micromamba-releases.)
- GnuCOBOL current stable = **3.2** (3.1.2 also referenced); GnuCOBOL 4 in testing.

### ⭐ Recommended recipe — micromamba + conda-forge into a /workspace prefix (no root, persists)
Run these via the agent's `code_execution` (bash) **during PRE-WARM** (network on):
```bash
# 1. Bootstrap micromamba (userland, no root) — curl & wget are pre-installed
cd /workspace
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
export MAMBA_ROOT_PREFIX=/workspace/.mamba

# 2. Create a userland env with GnuCOBOL from conda-forge (pulls cobc + C compiler + libcob + gmp)
/workspace/bin/micromamba create -y -p /workspace/cobol -c conda-forge gnucobol

# 3. Verify cobc works
/workspace/cobol/bin/cobc --version
# 4. Compile + run a COBOL program (no system gcc needed; conda toolchain is on the env)
/workspace/cobol/bin/cobc -x -o /workspace/hello /workspace/hello.cob \
  && /workspace/hello
```
Invoke `cobc` by its absolute path `/workspace/cobol/bin/cobc` (no shell activation needed), OR
`/workspace/bin/micromamba run -p /workspace/cobol cobc -x program.cob`.

### ⭐ THE DEMO FRAMING that defeats "no network on stage"
- Network is **unrestricted by default** but the install is the only step that needs it.
- **PRE-WARM (before going on stage, network on):** run the recipe above in a remote env; capture
  `interaction.environment_id`.
- **Persistence:** installed packages + files persist in that env (agent-environment.md.txt verbatim:
  *"Packages installed during an interaction persist when you reuse the same environment_id."*).
- **ON STAGE:** reuse the SAME env (`extra_body={"environment": prewarmed_env_id}`). `cobc` is
  ALREADY installed at `/workspace/cobol/bin/cobc` — the agent compiles + runs COBOL with NO network
  call required for the toolchain. The live differential oracle (run COBOL vs run migrated Python)
  works on stage even if conference Wi-Fi is hostile.

### Backup path — build from source (no root)
If conda is undesirable: `repository` source can git-clone GnuCOBOL *source* (text, ≤500MB), then:
`./configure --prefix=/workspace/usr && make && make install`, then
`export PATH=/workspace/usr/bin:$PATH; export LD_LIBRARY_PATH=/workspace/usr/lib:$LD_LIBRARY_PATH`.
Needs gcc + gmp-dev present. gcc is *likely* present (agent "builds apps") but `[UNVERIFIED]`; gmp
may be missing → conda path avoids this risk. Static link option exists: `cobc -fstatic-linkage` /
`cobc -static` (gnucobol FAQ) — but irrelevant once cobc is installed in-env.

### Fallback if ALL live-install fails (oracle stays honest)
Pre-capture GnuCOBOL ground-truth outputs OFFLINE; ship expected outputs as inline TEXT `sources`;
diff migrated Python against them. Keeps the "COBOL-as-oracle" claim truthful without live cobc.
backend-eng (task #4) should wire BOTH: live-compile primary + captured-output fallback.

### Open items for backend-eng to confirm LOCALLY (I have no live sandbox creds)
- `[UNVERIFIED-but-high-confidence]` exact conda-forge `gnucobol` version pin + that the linux-64
  build's cobc runs in a vanilla Ubuntu container. Pin a known-good version once tested.
- micromamba download URL stability — `https://micro.mamba.pm/api/micromamba/linux-64/latest` (or the
  install script `"${SHELL}" <(curl -L https://micro.mamba.pm/install.sh)`). If `micro.mamba.pm` is
  ever blocked, mirror via github.com/mamba-org/micromamba-releases.
Sources: github.com/conda-forge/gnucobol-feedstock; gnucobol.sourceforge.io/faq; github.com/mamba-org/micromamba-releases.

## Could not fetch
- YouTube https://www.youtube.com/watch?v=OdrOmc_RX8A — not retrievable as text via WebFetch
  (video page, no transcript). `[UNVERIFIED]` — not used as a source.
- anaconda.org & mamba.readthedocs.io blocked by fetch policy — used GitHub feedstock + mirrors
  + search instead to verify the conda-forge `gnucobol` package and micromamba commands.
