# Findings — Gemini 3.5 Flash (owner: researcher-gemini)

> Append verified facts here, each with a **source URL** and a verbatim quote where
> possible. Mark anything uncertain `[UNVERIFIED]`. Lead reconciles into
> `docs/RESEARCH_GEMINI_3.5.md` via doc-keeper.

## Seed facts (verified by lead, 2026-05-23)
- Model ID: `gemini-3.5-flash` — GA (~2026-05-19).
  Source: https://ai.google.dev/gemini-api/docs/interactions/whats-new-gemini-3.5
- 1M token context, 65k max output tokens.
- Thinking levels: `minimal | low | medium | high`; default shifted to `medium`.
- "Thought preservation": intermediate reasoning maintained across multi-turn.
- All Gemini 3 family features EXCEPT Computer Use.

## Verified (researcher-gemini, 2026-05-23 — live docs)
- [x] Exact pricing (input/output/cached) — §4
- [x] Rate limits / quotas (free tier vs paid; hackathon temp accounts) — §5
- [x] Multimodal inputs supported (image/audio/video/pdf) + limits — §6
- [x] How to set thinking level via SDK (param name + values) + verbatim code — §7
- [x] Structured output / function calling support + how — §9
- [x] Knowledge cutoff / training date — §3
- [x] Differences vs `gemini-3-flash-preview` — §11
- [x] Quickstart code (Python `google-genai`) verified against docs — §8
- [x] Minimum `google-genai` version — §10

---

## 1. Model identity & status
- **Model ID:** `gemini-3.5-flash`. Status: "generally available (GA), stable, and ready
  for scaled production use." Release ~2026-05-19. Preview predecessor: `gemini-3-flash-preview`.
- Sources: https://ai.google.dev/gemini-api/docs/interactions/whats-new-gemini-3.5 ·
  https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash.md.txt
  (spec: "Versions: Stable: `gemini-3.5-flash` · Preview: `gemini-3-flash-preview`")

## 2. Context / output token limits
- Input (context window): **1,048,576** (1M). Output: **65,536** (65k).
- Source: https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash.md.txt

## 3. Knowledge cutoff
- **January 2025.** Latest update: May 2026.
- Source: https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash.md.txt
  (The whats-new pages do NOT state a cutoff; the model spec page does.)

## 4. Pricing (per 1M tokens) — verified
Source: https://ai.google.dev/gemini-api/docs/pricing.md.txt (no explicit date on page)

### gemini-3.5-flash
| | Standard (paid) | Batch (paid) | Free tier |
|---|---|---|---|
| Input | **$1.50** | $0.75 | Free of charge |
| Output (incl. thinking tokens) | **$9.00** | $4.50 | Free of charge |
| Context caching | $0.15 | $0.075 | — |
| Cache storage | $1.00 / 1M tokens / hour | $1.00 / 1M tokens / hour | — |

- Output price "includes thinking tokens" (verbatim) → thinking is billed as output.

### gemini-3-flash-preview (comparison)
- Input $0.50 (text/image/video), $1.00 (audio); Output $3.00; Caching $0.05/$0.10.
- **Cost impact:** 3.5 is **3x** preview on both input ($1.50 vs $0.50 text) and output ($9.00 vs $3.00).
- `[UNVERIFIED]` whether 3.5 has a separate audio-input surcharge (preview did; 3.5 page showed flat $1.50).

## 5. Rate limits / quotas
Source: https://ai.google.dev/gemini-api/docs/rate-limits.md.txt
- Exact RPM/TPM/RPD **not published**: "Rate limits depend on a variety of factors (such as
  your usage tier) and can be viewed in Google AI Studio." → https://aistudio.google.com/rate-limit
- Tiers: Free ("Active project or free trial"); Tier 1 (link billing acct, $250 cap);
  Tier 2 ($100 paid + 3 days, $2,000 cap); Tier 3 ($1,000 paid + 30 days, $20k–$100k+ cap).
- Batch enqueued-token limits (3.5-flash): T1 = 3,000,000 · T2 = 400,000,000 · T3 = 1,000,000,000.
- Free tier: 3.5-flash listed "Free of charge" → a free AI Studio key CAN call it (free-tier rate caps apply).
- Hackathon/temp accounts: no dedicated note in docs. `[UNVERIFIED]` — assume Free-tier limits; verify the issued key in AI Studio.

## 6. Multimodal inputs
- Inputs: "Text, Image, Video, Audio, and PDF". Output: Text only.
- Source: https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash.md.txt
- Per-file size/resolution caps: `[UNVERIFIED]` → https://ai.google.dev/gemini-api/docs/interactions/media-resolution

## 7. Thinking levels + EXACT SDK param
Sources: https://ai.google.dev/gemini-api/docs/interactions/thinking.md.txt ·
https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.5.md.txt
- **Param:** `thinking_level` (string). Replaces deprecated numeric `thinking_budget`.
- **Values:** `"minimal" | "low" | "medium" | "high"`. **Default = `medium`**
  ("The default thinking effort is now `medium`, changed from `high` in Gemini 3 Flash Preview";
  "`medium` yields very good results... while being faster and more cost-efficient").
- Thought preservation/signatures ON by default → carries multi-turn reasoning, increases token cost.

### Verified Python — generate_content (typed config)
Source: https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.5.md.txt (verbatim)
```python
from google import genai
from google.genai import types

client = genai.Client()
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="Prove that the square root of 2 is irrational.",
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level="high")
    ),
)
print(response.text)
```

### Verified Python — Interactions API (recommended for agents)
Source: https://ai.google.dev/gemini-api/docs/interactions/thinking.md.txt (model → 3.5 per quickstart)
```python
from google import genai

client = genai.Client()
interaction = client.interactions.create(
    model="gemini-3.5-flash",
    input="List 3 famous physicists and their key contributions",
    generation_config={"thinking_level": "low"},
)
print(interaction.output_text)
```

## 8. Quickstart (Interactions API) — verified
Source: https://ai.google.dev/gemini-api/docs/interactions/quickstart.md.txt
```python
from google import genai

client = genai.Client()  # reads AI Studio API key from env
interaction = client.interactions.create(
    model="gemini-3.5-flash",
    input="Explain how AI works in a few words",
)
print(interaction.output_text)
```
- Install: `pip install -q -U google-genai` (docs recommend `>=2.0.0`, §10).
- API key: https://aistudio.google.com/app/apikey . REST uses `$GEMINI_API_KEY`; SDK reads env.
- Output props on interaction: `output_text`, `output_image`, `output_audio`.
- `interactions.create()` params: `model`, `input` (str|list of parts), `generation_config`
  (holds `thinking_level`), `previous_interaction_id`, `tools`, `system_instruction`,
  `store` (default true), `background`, `stream`.
  Source: https://ai.google.dev/gemini-api/docs/interactions.md.txt

## 9. Structured output & function calling
Source: https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash.md.txt
- **Structured outputs: Supported. Function calling: Supported.**
- Also supported: Caching, Code execution, File search, Batch API, Flex inference,
  Priority inference, Grounding with Google Maps, Search grounding, Thinking, URL context.
- 3.x function-calling convention (breaking): responses must include `id`, match `name`,
  match response counts. Multimodal results go INSIDE function-response parts.
  Source: https://ai.google.dev/gemini-api/docs/interactions/whats-new-gemini-3.5
- **NOT supported by 3.5-flash:** Computer use ("Computer Use is not supported at this moment"),
  Image generation, Audio generation, Live API.

## 10. Minimum google-genai SDK version
- Docs: "We strongly recommend updating to `google-genai` SDK **v2.0.0 or later**."
  Source: https://ai.google.dev/gemini-api/docs/interactions/whats-new-gemini-3.5
- PyPI cross-check (2026-05-23): 2.0.0 exists; latest **2.6.0**. JS `@google/genai` latest v2.0.1.
- **ACTION:** bump repo `requirements.txt` `google-genai>=1.55.0` → **`>=2.0.0`** (prefer `>=2.6.0`).

## 11. Differences vs gemini-3-flash-preview (migration)
Sources: https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.5.md.txt + interactions/whats-new
1. Model string `gemini-3-flash-preview` → `gemini-3.5-flash`.
2. Default thinking `high` → `medium` (re-test prompts).
3. `thinking_budget` (numeric) → `thinking_level` (string enum).
4. **Remove `temperature`, `top_p`, `top_k`** — "no longer recommended" for Gemini 3.x.
5. Pricing ~3x higher (§4).
6. Thought preservation ON by default → more tokens/cost.
7. Stricter function-calling conventions (id/name/count).
8. Computer Use not yet on 3.5 (stay on 3 Flash Preview for it).
9. Knowledge cutoff January 2025.
10. SDK floor → `>=2.0.0`.

---

## CONTRADICTIONS WITH CURRENT REPO (for team-lead / backend-eng)
1. **`requirements.txt` pins `google-genai>=1.55.0`** — docs require **`>=2.0.0`** for 3.5-flash.
   MUST bump. `src/agent.py` lines 9 & 23 repeat `>=1.55.0`.
2. **`src/agent.py` header (lines 14–15)** says the LAZARUS agent doesn't support
   `function_calling`/structured output. That's a *managed-agent config* claim, NOT a model
   limit — the **model `gemini-3.5-flash` DOES support both** (spec page §9). Flagging the
   wording; whether the Antigravity managed agent exposes them is task #2/#5's lane.
3. `src/agent.py` uses the managed-agent shape (`interactions.create(agent=..., environment=...,
   stream=True)`, `agents.create(...)`). I could NOT confirm that surface from the model/interactions
   docs I fetched — owned by task #2 (researcher-agents). No contradiction found; just unverified by me.

## OPEN / UNVERIFIED
- Exact RPM/TPM/RPD per tier (AI Studio dashboard only).
- Hackathon/temp-account quota specifics.
- Separate audio-input pricing for 3.5 (preview had one; 3.5 page showed flat $1.50).
- Per-file multimodal size/resolution caps (see media-resolution guide).

---

# Option B — portable COBOL binary (task #8, researcher-gemini, 2026-05-23)

> ⛔ **SUPERSEDED 2026-05-23 — the "mount a pre-compiled binary" framing below is DEAD.**
> researcher-agents resolved the complementary question: `base_environment.sources` accept
> **TEXT and image only** — verbatim (`agent-environment.md.txt`): *"The agent is currently
> constrained to reading text and image files. Binary file support is not yet available."*
> Source caps: inline = TEXT ≤1MB/file (≤2MB total), repository = git ≤500MB, gcs ≤2GB.
> **You cannot base64-mount a compiled `cobc`/`payroll`/AppImage via `sources`.**
>
> ✅ **The GOAL still holds and is achievable — see [Option B-revised](#option-b-revised--no-root-runtime-acquisition-of-gnucobol)
> below: no-root RUNTIME acquisition of GnuCOBOL via the agent's bash (`code_execution`,
> unrestricted network).** Recipe C (user-space `--prefix` install) below survives as a
> fallback; the binary-mount / musl-single-file recipes (A, B) are kept only for the record.

**Goal:** produce a `payroll` (and ideally `cobc`-free) executable that runs the original
COBOL live in the antigravity sandbox — **Ubuntu, Python 3.12 base, x86_64, 4c/16GB, NO root,
NO gcc/cobc/build-essential, has git/curl** — so the differential oracle runs without `apt`.

## TL;DR / RECOMMENDATION
- **DO NOT rely on `cobc -static` against glibc.** It's discouraged by the GnuCOBOL maintainer
  (LGPL re-link obligation) AND technically fragile: libcob calls `getpwnam`/NSS at startup, and
  glibc fully-static binaries can't load NSS modules → warnings + version-skew breakage.
- **RECOMMENDED (robust, proven): "bundle libcob + LD_LIBRARY_PATH."** Build the binary on a
  matching Ubuntu image, ship the `payroll` ELF **plus its `.so` deps** in a `lib/` dir, and run
  with `LD_LIBRARY_PATH=./lib`. No root, no install needed on target. This is exactly the
  pattern AWS-Lambda COBOL projects use (Lambda = same "no GnuCOBOL, no root" constraint).
- **MOST robust if you want a single file: musl-static** (Alpine toolchain) — musl has no NSS
  dynamic-module problem, so a fully static ELF actually works. Heavier to build; use only if
  the bundle approach is rejected.
- **GLIBC CAVEAT (applies to ALL approaches): build on glibc <= the sandbox's glibc.** A binary
  built on newer glibc fails on older with `version 'GLIBC_2.xx' not found`. Build on Ubuntu
  matching the sandbox (assume 24.04 / glibc 2.39 unless researcher-agents confirms otherwise),
  or build on an OLDER base (22.04 / glibc 2.35) for forward-compat. musl-static sidesteps this.

## What I verified mechanically (macOS Homebrew GnuCOBOL 3.2.0; I have NO Docker/Linux here)
- **Program is correct & deterministic:** `echo "0050000.00" | ./payroll` → `0038750.00`
  (gross 50000.00 − 22.5% tax = 38750.00). This is the oracle ground-truth for the demo input.
- **cobc pipeline:** cobc translates COBOL→C→links `-lcob`. Confirmed via `cobc -x -v -save-temps`:
  `clang -c ... -I.../gmp/include` then `clang -o payroll payroll.o -L.../lib -lcob`.
- **libcob's runtime deps (otool -L on libcob.4):** `libgmp` (always), plus optionally
  `libxml2`, `libjson-c`, `libncurses`, `libdb`. → Dropping the optional ones at configure time
  shrinks the bundle to ~`libcob + libgmp + libc/libm`.
- **KEY: the compiled binary needs NO COB_CONFIG_DIR / COB_COPY_DIR at runtime.** I ran it with
  `COB_CONFIG_DIR=/nonexistent COB_COPY_DIR=/nonexistent` and it still printed `0038750.00`.
  Those dirs are compile-time only → nothing extra to mount for the runtime binary. (Verified
  with GnuCOBOL 3.2 dynamic build; behavior is the same on Linux.)
- **macOS is NOT a valid build host for the deployable binary:** `cobc -static` on macOS still
  produced a Mach-O linked to `libcob.4.dylib` (otool -L). Mach-O ≠ ELF, and there's no static
  libSystem. **backend-eng MUST build on Linux x86_64** (Docker `ubuntu:24.04` / `ubuntu:22.04`).

## RECIPE A (RECOMMENDED) — bundle libcob + LD_LIBRARY_PATH  (no root on target)
Build host = Docker on backend-eng's machine (I can't run Docker in my sandbox). Match/undershoot
the sandbox glibc; 22.04 chosen for forward-compat.
```dockerfile
# build.Dockerfile  — produces /out/{payroll, lib/*.so}
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y --no-install-recommends gnucobol libcob-dev gnucobol-dev 2>/dev/null \
 || apt-get install -y --no-install-recommends gnucobol
# (Ubuntu pkg name is `gnucobol`; runtime lib is libcob; -dev provides headers for compile.)
WORKDIR /build
COPY payroll.cob .
RUN cobc -x -O2 -o payroll payroll.cob
# Gather the binary + its shared-lib deps into a self-contained bundle:
RUN mkdir -p /out/lib && cp payroll /out/ \
 && ldd payroll | awk '/=>/ && $3 ~ /^\// {print $3}' \
      | grep -E 'libcob|libgmp|libxml2|libjson-c|libncurses|libdb' \
      | xargs -I{} cp -vL {} /out/lib/
```
Extract `/out` and commit `payroll` + `lib/` into the small mountable repo. **Run on the sandbox:**
```bash
chmod +x ./payroll
echo "0050000.00" | LD_LIBRARY_PATH="$PWD/lib" ./payroll      # -> 0038750.00
```
Even more self-contained (no env var needed): set an rpath at build so it looks in `./lib`:
```bash
cobc -x -O2 -Wl,-rpath,'$ORIGIN/lib' -o payroll payroll.cob   # $ORIGIN = dir of the binary
```
**Verify the bundle is complete (on a clean container with NO gnucobol installed):**
```bash
docker run --rm -v "$PWD/out":/m ubuntu:24.04 bash -c \
  'cd /m && echo "0050000.00" | LD_LIBRARY_PATH=/m/lib ./payroll'   # must print 0038750.00
ldd ./payroll    # every line should resolve; only libc/ld-linux from the system is OK
```
- **Size:** payroll ELF is tiny (~30–60 KB); the `lib/` bundle is dominated by libgmp (~500 KB)
  + libcob (~700 KB–1 MB). Total bundle typically **< 2–3 MB**. [size = estimate; backend-eng confirm]
- **Why robust:** no root, no apt, no `cobc` on target; libc/ld-linux come from the sandbox
  (so no NSS/getpwnam static-link problem); only requirement is build-glibc <= sandbox-glibc.

## RECIPE B (single-file, most portable) — musl fully-static via Alpine
Use only if a multi-file bundle is unacceptable. musl avoids the glibc/NSS static problem, so a
true single static ELF works and is glibc-version-independent.
```dockerfile
# musl-static.Dockerfile
FROM alpine:3.20
RUN apk add --no-cache build-base gnucobol gnucobol-dev gmp-dev gmp-static musl-dev
WORKDIR /build
COPY payroll.cob .
# Force static link of libcob + libgmp + musl:
RUN cobc -x -static -O2 \
      -L/usr/lib -Wl,-Bstatic -lcob -lgmp -Wl,-Bdynamic \
      -static -o payroll payroll.cob \
 || COB_LDFLAGS="-static" cobc -x -O2 -o payroll payroll.cob
RUN file payroll && ldd payroll || true     # expect: "not a dynamic executable"
```
**Verify it's truly static:** `ldd payroll` must print **`not a dynamic executable`** (or `file`
shows `statically linked`). Run anywhere: `echo "0050000.00" | ./payroll` → `0038750.00`.
- Caveat: Alpine's GnuCOBOL/gmp-static availability varies by Alpine version; if `gmp-static`
  is missing, build gmp `--enable-static` from source first. Heavier than Recipe A.
- Caveat: the demo uses only ACCEPT/DISPLAY/COMPUTE/NUMVAL — no ISAM/screen/XML — so the
  `--without-db --without-xml --without-json` minimal libcob is sufficient (fewer static deps).

## RECIPE C (fallback) — user-space install with --prefix (no root), then PATH/LD_LIBRARY_PATH
This is the GnuCOBOL maintainer's explicitly recommended no-admin approach. Heavier (ships a
whole prefix) but bulletproof if the binary bundle won't link:
```bash
./configure --prefix="$HOME/gc" && make && make install
export PATH="$HOME/gc/bin:$PATH"; export LD_LIBRARY_PATH="$HOME/gc/lib:$LD_LIBRARY_PATH"
```
Pre-build `$HOME/gc` in Docker, commit it, mount it, and `source` the exports. Bigger artifact
(~tens of MB) but lets the sandbox even *recompile* if needed.

## Alternatives evaluated and REJECTED for this use case
- **AppImage:** would bundle libcob+deps into one runnable file, but AppImage normally needs FUSE
  (or `--appimage-extract`/`APPIMAGE_EXTRACT_AND_RUN=1`) — extra moving parts vs Recipe A's plain
  `LD_LIBRARY_PATH`. No upstream GnuCOBOL AppImage exists; you'd build it yourself. Not worth it
  when the bundle approach already works root-free. Skip.
- **COBOL→WASM:** technically real (GnuCOBOL→C→Emscripten→WASM; Cloudflare's `cobweb`/`cobaul`
  uses GnuCOBOL 2.2), BUT cobweb targets Cloudflare Workers only — "not Browser or WASI support."
  Our sandbox runs native x86_64 ELF already, so WASM adds a runtime (wasmtime/node) and buys
  nothing. Reject. Source: https://developer.fermyon.com/wasm-languages/cobol ,
  https://github.com/cloudflare/cobweb
- **Pure-pip / pure-Python COBOL runtime:** none mature exists on PyPI (searched). Reject.
  (Note: this would also defeat the demo's POINT — the differential oracle must run the *real*
  GnuCOBOL, not a reimplementation, to be a trustworthy ground truth.)

## What I could NOT do / hand-off
- **I have NO Docker/Linux in my sandbox** (daemon unreachable; even `timeout` absent), so I could
  not produce/`ldd`-verify the actual x86_64 ELF. All Linux specifics are from docs + the
  lambda-cobol Dockerfile pattern + my macOS cobc probe. **backend-eng must run Recipe A in
  Docker and confirm:** (1) `ldd payroll` resolves cleanly, (2) clean-container run prints
  `0038750.00`, (3) record exact bundle size + the sandbox glibc version.
- **The sandbox's exact glibc version is unconfirmed** — depends on the antigravity base image
  (researcher-agents owns the env spec). Build on 22.04 to be safe; if sandbox is 22.04-based,
  match it. This is the single biggest correctness risk for Recipe A.
- **Whether base_environment can actually mount + chmod+x + execute a committed binary file** is
  researcher-agents' lane (task #2). Recipe assumes yes; if the mount is read-only or noexec,
  fall back to Recipe C (user-space install) or Option A (live `apt`/`pip` install).

## Sources
- Static linking discouraged by maintainer + no-root `--prefix` approach:
  https://sourceforge.net/p/gnucobol/discussion/help/thread/9375eca1/
- GnuCOBOL static-linking flags (`-static`, `-fstatic-call`):
  https://gnucobol.sourceforge.io/historical/open-cobol/Static-Linking.html
- libcob runtime deps (gmp/db/ncurses/xml): https://gnucobol.sourceforge.io/faq/index.html
- Why glibc full-static fails (NSS/getpwnam/dlopen) + musl is the static-friendly fix:
  https://linuxvox.com/blog/why-would-it-be-impossible-to-fully-statically-link-an-application/
- Proven "build cobc, `cobc -x`, copy libcob.so.4 next to binary" pattern (AWS Lambda, same
  no-GnuCOBOL/no-root constraint): https://raw.githubusercontent.com/didier-durand/lambda-cobol/main/Dockerfile
  (also configures `--without-db --without-xml --without-json` to minimize deps)
- Ubuntu pkg names (gnucobol / libcob) + libgmp10 2:6.3.0 on noble: https://packages.ubuntu.com/noble/
- Local verification: GnuCOBOL 3.2.0 on macOS arm64 (this machine), 2026-05-23.

---

# Option B-revised — no-root RUNTIME acquisition of GnuCOBOL  (task #8 PIVOT, 2026-05-23)

**Why this replaces the binary-mount plan:** `sources` can't carry a compiled binary (see the
SUPERSEDED banner up top). But the antigravity agent's `code_execution` tool is verbatim *"Run
Bash, Python, and Node.js commands. Install packages, run tests, build apps."* with **network
unrestricted by default** and **curl/wget preinstalled**, and packages installed during an
interaction **persist when you reuse the same `environment_id`**. So the agent can just *install*
GnuCOBOL into a userland prefix at runtime — no root, no `sources`, no `apt`.
(Target env confirmed by researcher-agents: Ubuntu, Python 3.12, Node 22, 4 CPU / 16 GB,
network unrestricted — NOT the GCP "Enterprise Agent Platform" product, which is network-off.)

## TL;DR / RECOMMENDATION — Recipe D (micromamba + conda-forge `gnucobol`)
**Cleanest no-root path. VERIFIED the package exists, builds for linux-64, and ships a working
`cobc`.** The agent runs this in its bash; it persists in the env for the rest of the session:
```bash
# 1) Bootstrap micromamba — a SINGLE STATIC binary, no root, no deps (glibc system = our Ubuntu):
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
export MAMBA_ROOT_PREFIX=/workspace/mamba          # userland; lives in the persistent env
# 2) Create an env with GnuCOBOL from conda-forge (pulls gmp/json-c/libxml2/ncurses/libdb auto):
./bin/micromamba create -y -p /workspace/cobol -c conda-forge gnucobol
# 3) Use cobc (conda sets up the runtime libs for you — no manual LD_LIBRARY_PATH bundling):
/workspace/cobol/bin/cobc -x -o payroll src/sample/payroll.cob
echo "0050000.00" | /workspace/cobol/bin/payroll          # -> 0038750.00 (oracle ground truth)
# (or `./bin/micromamba run -p /workspace/cobol cobc -x ...` to get the env's PATH/libs set)
```
- **Verified facts (authoritative, 2026-05-23):**
  - `conda-forge/gnucobol-feedstock` EXISTS — package `gnucobol` **v3.2**, GPL-3.0,
    *"COBOL85-202x compiler supporting lots of dialect specific extensions"*; feedstock last
    updated 2026-04-24 (actively maintained).
    Source: https://github.com/conda-forge/gnucobol-feedstock/blob/main/recipe/meta.yaml
  - **linux_64 is in the active build matrix** (Azure CI builds `linux_64`, `osx_64`, `osx_arm64`;
    recipe `skip: True # [win]`). So the linux-64 build IS published to the conda-forge channel.
    Source: https://github.com/conda-forge/gnucobol-feedstock (README build-status table)
  - **The conda package provides a working compile+run toolchain** — the feedstock's own CI test
    does `cobc -x -o out test.cbl && ./out | grep "Hello World!"`.
    Source: https://github.com/conda-forge/gnucobol-feedstock/blob/main/recipe/test.sh
  - **Runtime deps are pulled automatically by conda** — recipe `host:` = gmp, json-c, libxml2,
    ncurses, libdb. This is the big win over binary-mount: NO manual `.so` bundling / no glibc
    skew (conda ships its own libs under the prefix).
  - **micromamba is a single static standalone binary** (no root, no deps); install one-liner:
    `curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba`.
    Caveat from the docs: needs a **glibc** system (our Ubuntu sandbox qualifies; *Alpine does not*).
    Source: https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html ·
    https://github.com/mamba-org/micromamba-releases
- **Demo trade-off:** the conda `create` pulls ~tens of MB on first run (a few seconds on the
  unrestricted network). For the live demo, do it in a **pre-warm step** (the DEMO_SCRIPT already
  shows "sandbox pre-warmed, GnuCOBOL already installed") and reuse that `environment_id` so it's
  instant on stage. Persists for the session; for a fresh run, re-run the one-liner or fork the env.

## Recipe E (fallback) — source build into a userland prefix (no root)
If conda is undesirable, `code_execution` "builds apps", so build from GNU source. Needs a C
toolchain + `gmp` headers in the sandbox — **[UNVERIFIED] whether gcc/gmp-dev are preinstalled**;
the agent can `apt-get` only if it has sudo (it does NOT) — so install gmp via conda or a userland
gcc if missing. Cleaner to just use Recipe D.
```bash
curl -LO https://ftp.gnu.org/gnu/gnucobol/gnucobol-3.2.tar.xz
tar xf gnucobol-3.2.tar.xz && cd gnucobol-3.2
./configure --prefix=/workspace/usr && make -j4 && make install
export PATH=/workspace/usr/bin:$PATH
export LD_LIBRARY_PATH=/workspace/usr/lib:$LD_LIBRARY_PATH
cobc --version    # verify
```
- Note: GnuCOBOL **3.2** is the current source tarball on ftp.gnu.org (matches the conda version);
  sha256 pinned in the feedstock recipe (`3bb48af46...`) if you want to verify the download.
  Source: https://github.com/conda-forge/gnucobol-feedstock/blob/main/recipe/meta.yaml

## Recipe F — `repository` source (git clone of SOURCE, then build in-sandbox)
`sources` CAN carry a git repo (text, ≤500MB) — so you may mount **GnuCOBOL source** (or a vendored
copy) and build it in the env with Recipe E's `./configure && make`. You still can't ship the
*compiled* artifact via `sources`; this only moves the source in. Lower value than Recipe D.

## Alt runtimes (fallback scan) — same verdict as before, still REJECT
- **COBOL→WASM** (Cloudflare cobweb / Fermyon): Workers-only, no WASI/standalone runtime; the
  sandbox runs native ELF, so it buys nothing. Source: https://developer.fermyon.com/wasm-languages/cobol
- **Pure-pip / pure-Python COBOL**: none mature on PyPI; and a reimplementation would defeat the
  oracle's "real GnuCOBOL = ground truth" purpose.

## Persistence across env reuse — doc-grounded YES, but [UNVERIFIED-needs-live-test]
researcher-agents' verdict (2026-05-23): the documented model covers our case, but it isn't
named explicitly, so treat as **doc-says-yes, backend must confirm with a stop/resume test.**
- ✅ Docs guarantee (verbatim, `agent-environment.md.txt`): *"Packages installed during an
  interaction persist when you reuse the same `environment_id`."* + filesystem persistence
  (cookbook: file written turn 1 is readable turn 2 via the same env_id). A conda env at
  `/workspace/cobol` is just files under `/workspace` + installed packages → squarely covered.
- ⚠️ NOT explicitly documented: the docs never name `/workspace` or conda, and "packages persist"
  is phrased around pip/npm. Two residual risks a live test must rule out:
  1. **Snapshot completeness** — does the 15-min idle auto-snapshot capture the FULL `/workspace`
     tree incl. the ~hundreds-of-MB conda prefix byte-for-byte? Large prefixes are exactly what a
     snapshot might truncate. Must verify cobc still runs **after a stop/resume cycle**, not just
     turn1→turn2 in quick succession.
  2. **Path/exec independence** — DO NOT rely on PATH/shell-activation that won't survive a fresh
     interaction. Always invoke the **absolute path** `/workspace/cobol/bin/cobc` (or
     `./bin/micromamba run -p /workspace/cobol cobc ...`). The recipes above already use absolute
     paths for this reason.

## Hand-off / open items (backend-eng to TEST in a real Ubuntu env or the sandbox)
- ✅ Confirmed by me: conda-forge `gnucobol` v3.2 linux-64 exists + provides working cobc; micromamba
  bootstrap one-liner; auto-pulled runtime deps. (I have no Docker/Linux here — could not run it.)
- ⏳ backend-eng: time the `micromamba create` cold pull (for the pre-warm budget) and confirm
  `echo "0050000.00" | /workspace/cobol/bin/payroll` prints `0038750.00` end-to-end in the sandbox.
- ⏳ **PERSISTENCE STOP/RESUME TEST (the deciding test, per researcher-agents):**
  (1) interaction A: install conda+gnucobol into `/workspace/cobol`, note `env_id`;
  (2) wait past the 15-min idle auto-snapshot/stop OR start a fresh interaction B with
      `extra_body={"environment": env_id}`;
  (3) run `/workspace/cobol/bin/cobc --version` and compile a `.cob` — assert it works with
      **NO reinstall and NO network**. If B passes after an idle/stop cycle → persistence CONFIRMED.
- ⏳ [UNVERIFIED] whether a C toolchain / gmp-dev is preinstalled (only matters for Recipe E;
  Recipe D doesn't need it).

## Sources (Option B-revised)
- conda-forge gnucobol recipe (v3.2, deps, source url+sha): https://github.com/conda-forge/gnucobol-feedstock/blob/main/recipe/meta.yaml
- conda-forge gnucobol build matrix + install commands (README): https://github.com/conda-forge/gnucobol-feedstock
- conda-forge gnucobol CI test (proves working cobc): https://github.com/conda-forge/gnucobol-feedstock/blob/main/recipe/test.sh
- micromamba standalone install: https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html · https://github.com/mamba-org/micromamba-releases
- GnuCOBOL 3.2 source tarball: https://ftp.gnu.org/gnu/gnucobol/gnucobol-3.2.tar.xz
- Binary-mount BLOCKED + env spec: docs/research/findings-agents.md (researcher-agents) ·
  https://ai.google.dev/gemini-api/docs/agent-environment.md.txt
