# CHALLENGES — Devil's Advocate Log (owner: devils-advocate)

> Every load-bearing assumption gets attacked here. For each: state the claim, the
> attack, evidence (with URL), and a verdict: **CONFIRMED** / **NEEDS FIX** / **FALSE —
> redesign** / **ACCEPTED RISK**. Escalate FALSE/NEEDS-FIX to the lead immediately.

**Posture:** assume a skeptical Google DeepMind judge AND a skeptical AI Futures Fund
investor are in the room and will fact-check every number and every platform claim.

---

## SCOREBOARD (read this first)

| # | Item | Severity | Verdict |
|---|---|---|---|
| C1 | Runtime self-authored `SKILL.md` is a real primitive | load-bearing ($5k) | **CONFIRMED (mechanism)** — but cross-run persistence is overclaimed (see C1b) |
| C1b | Forged skills "persist forever / accumulate across runs" | load-bearing (moat) | **NEEDS FIX** — fresh invocations fork clean |
| C2 | "computer_use / file_search NOT used (unsupported)" honesty claim | load-bearing (honesty) | **CONFIRMED** — both genuinely unsupported; seed premise was wrong |
| C3 | Base agent ID `antigravity-preview-05-2026` | load-bearing (it runs) | **CONFIRMED** — exact + only supported value |
| C4 | Agent compiles + runs real COBOL via GnuCOBOL live | load-bearing (#1 anti-objection) | **NEEDS FIX** (was FALSE; corrected). Only the "apt-get / pre-install into base_environment" WORDING is wrong. **Live-compile is VIABLE** (task #8): the AGENT micromamba/conda-forge-installs `gnucobol` (ships its OWN compiler+libcob+gmp, no system gcc, no root) at pre-warm into the reused env_id → no network needed live. golden_io.json = floor. Mounted-binary path REJECTED ("Binary file support is not yet available"). Falsifiability INTACT. |
| C5 | "byte-for-byte" diff is robust | load-bearing (demo) | **NEEDS FIX (TESTED)** — zero-pad format + half-up rounding fail naively; proven fix = Decimal/HALF_UP + `{:07d}.{:02d}` (9/9 byte-exact) |
| C6 | Sandbox spec (Python 3.12 / Node 22 / 4CPU·16GB / 15-min snapshot) | medium | **CONFIRMED (repo correct)** — lead fetched agent-environment.md.txt: "4 cores" + "16 GB" are VERBATIM-sourced; all repo specs (3.12 / Node 22 / 4 CPU / 16 GB / 15-min snapshot / 7-day retention / unrestricted network) VERIFIED. Hackathon hands out Gemini API keys → ai.google.dev governs. Do NOT edit. |
| C7 | NJ impact stats (1600%, 575k, "begged on live TV") | medium (Impact = 20%) | **RESOLVED** — 1600% CONFIRMED; 575k was unsourced → doc-keeper fixed to "362,000 in two weeks" (NJ DOL 4/2/2020; NOT "first week" — that's the 2-wk total) + "publicly called for volunteers." |
| C8 | $2.41T tech debt; 18–23% wasted; $30B market | medium (Impact = 20%) | **CONFIRMED** (with date caveats) |
| C9 | "1M-token context" relevance to a ~150-line module | low (framing) | **NEEDS FIX** — non-sequitur a judge will needle |
| C10 | `MAX_ITERATIONS = 4` "hard cap" + "visible counter" | medium (demo safety) | **RESOLVED (verified in code)** — agent.py now has a real `range(1, MAX_ITERATIONS+1)` loop + `emit_iteration` counter; server.py forwards it to the UI + `/api/health`. Orchestrator-enforced, not prompt-only. |
| C11 | agent.py streaming/SDK field names | medium (it runs) | **NEEDS FIX** — guessed schema; verify or it crashes |
| C12 | Demo determinism / cold-start | medium (Demo = 45%) | **ACCEPTED RISK** — mitigations exist; tighten |
| C13 | Demo blames "COMP-3" but COMP-3 isn't what fails | medium (signature beat honesty) | **NEEDS FIX (PROVEN) — NOT YET LANDED** — relabel still missing from mock-run.json (drives UI), STREAM_CONTRACT, DEMO, README, ARCHITECTURE, AGENTS.md, test_agent.py. Highest-priority remaining honesty fix. |
| C14 | BUILD_PLAN "install GnuCOBOL" + "no network" contradiction | medium (build day) | **NEEDS FIX** — impossible task + self-contradiction; resolve with C4 |
| C15 | `google-genai>=1.55.0` minimum version | low (it installs) | **RESOLVED for install; NEEDS FIX for 3 stale docs** — true floor is `>=2.4.0` (client.agents ships in 2.4.0, NOT 2.0.0). Pinned `>=2.6.0` is fine; but README L51 / ARCHITECTURE L77 / requirements.txt L8 still say "2.0.0" — bump to 2.4.0. |
| C16 | Demo UI says "hot-reloading agent" mid-interaction | medium ($5k beat honesty) | **NEEDS FIX — NOT LANDED** in web/ (mock-run.json L80/83, STREAM_CONTRACT L107/119/121). Mid-interaction hot-reload is UNVERIFIED; docs already say "re-discovery on next pass" — UI must match. Fix in the same C13 web/ pass. |

---

## Priority targets (the project dies if these are wrong)

### C1. Does `AGENTS.md` / `SKILL.md` self-authoring actually exist?  — CONFIRMED (mechanism)
- **Claim:** the agent writes a new `.agents/skills/<idiom>/SKILL.md` at runtime, it
  auto-loads, and persists — the demo's signature "agent upgrades itself" beat ($5k bonus).
- **Attack:** if SKILL.md is only read at `agents.create()` time, a file the agent writes
  mid-run never takes effect, and the centerpiece is fabricated.
- **Evidence:** AGENTS.md/SKILL.md are a real, documented primitive. Skills are
  *discovered automatically from the filesystem during execution*: "Skills loaded from
  `.agents/skills/` and `/.agents/skills/` are both discovered automatically." The
  custom-agent flow is "define everything in markdown files like AGENTS.md and SKILL.md."
  - https://ai.google.dev/gemini-api/docs/custom-agents
  - https://ai.google.dev/gemini-api/docs/antigravity-agent
  - https://blog.google/innovation-and-ai/technology/developers-tools/managed-agents-gemini-api/
- **Verdict: CONFIRMED (primitive) + RESOLVED as a TWO-TURN loop.** The open sub-question is
  now answered at primary source (researcher-agents, custom-agents.md.txt verbatim): skill
  discovery is a STARTUP/SCAN event — *"The Antigravity runtime scans `.agents/` … for these
  files"* / *"auto-discovers and registers them."* There is **NO** "during execution / on
  demand / mid-interaction" language anywhere in the API docs. So:
  - A SKILL.md the agent writes MID-RUN is **NOT** auto-registered within the same turn. (It
    can still be USED in-turn by reading the file directly via `code_execution` — it's on disk
    — but it isn't a registered managed skill until the next interaction's startup scan.)
  - **FORGE self-heal is a TWO-TURN loop:** Turn 1 → hit unknown idiom → write
    `.agents/skills/<idiom>/SKILL.md` (RED). Turn 2 → NEW interaction reusing the SAME
    `environment_id` → startup scan registers the new skill → retry → GREEN.
  - **This is REAL and demoable** — just honestly a 2-turn loop, not a single "hot-reload
    mid-thought." Any wording implying single-turn in-flight hot-reload = OVERCLAIM (see C16).
  - **Already handled in code:** `src/agent.py` implements the SAFE pattern — the forge retry
    reuses `environment_id` and the retry prompt EXPLICITLY re-reads `.agents/skills/` rather
    than assuming auto-reload (docstring: "do NOT rely on silent mid-run auto-reload … which
    is UNVERIFIED"). Good. The remaining gap is the DEMO/UI surface (C13/C16) implying one
    continuous beat — show the second turn, or narrate "write → next pass (same env) → green."

### C1b. Do forged skills "persist forever" and "accumulate across runs"?  — NEEDS FIX
- **Claim:** README Q&A "the persistent environment + forged skills accumulate dialect
  coverage across runs"; AGENTS.md step 5 "These persist for future runs"; the investor
  moat = "accumulated dialect skills."
- **Attack:** persistence is scoped to ONE environment lineage, not the saved agent.
- **Evidence — TWO code paths, both verbatim from quickstart.md.txt (researcher-agents
  reconciled my "forks clean" with their "files persist" — they're different paths):**
  - **Invoke a SAVED agent BY ID** → *"Each invocation forks the base environment, so every
    run starts clean."* The forged skill is GONE. To bank it permanently it must be mounted
    in `base_environment` (re-register the agent).
  - **Reuse an EXPLICIT `environment_id`** (`environment=<env_id>`) → *"Files from turn 1
    persist in turn 2."* Installs + files persist in the SAME sandbox.
  - https://ai.google.dev/gemini-api/docs/managed-agents-quickstart
- **Verdict: NEEDS FIX.** Reword the moat/persistence claims to state BOTH paths precisely so
  a judge probing "does it really persist?" gets the exact answer: "a forged skill persists
  for the life of the reused `environment_id` (same-sandbox turn-to-turn); a fresh invocation
  of the saved agent forks clean — to bank a skill permanently we re-register the agent with
  it mounted in `base_environment`. No 'persists forever / accumulates across runs.'"
- **DEPENDENCY for C4:** the GnuCOBOL pre-warm install only survives onto the demo run if the
  code uses the **explicit-`environment_id`-reuse** path (one long-lived env for the whole
  session), NOT invoke-by-saved-agent-id (which forks clean and would lose the install).
  backend-eng must honor env-id reuse. (Flagged consistent with researcher-agents.)

### C2. Is the "single-agent / no computer_use / no file_search" honesty claim true?  — CONFIRMED
- **Claim:** ARCHITECTURE §4 lists `computer_use`, `file_search`, `mcp`,
  `function_calling`, sub-agents as "Explicitly NOT used / unsupported."
- **Attack (from seed):** "the live agents tool list INCLUDES Computer Use and File
  Search" → honesty framing would be misleading.
- **Evidence:** the seed premise is **WRONG**. Antigravity agent doc, verbatim:
  *"Unavailable tools: `file_search`, `computer_use`, `google_maps`, `function_calling`
  and `mcp` are not yet supported."* Defaults are `code_execution`, `google_search`,
  `url_context`; filesystem auto-enabled by the `environment` param. There is no
  sub-agent deployment in the Managed Agents API (that's Antigravity 2.0 / ADK).
  - https://ai.google.dev/gemini-api/docs/antigravity-agent
- **Verdict: CONFIRMED.** Our honesty framing is accurate and is actually a *strength*
  with a DeepMind judge. No fix to the tools framing.
  - **CORRECTION (I had this backwards earlier).** `structured output` IS genuinely
    unsupported by the Antigravity agent — researcher-agents quotes the doc: "Also
    unsupported: temperature/top_p/top_k/stop_sequences/max_output_tokens, **structured
    outputs**, audio/video/doc inputs (text+image only)." So the agent.py comment is CORRECT
    to list it. My earlier "drop structured output as unsourced" instruction to doc-keeper was
    WRONG — do NOT drop it. The only precision point: it's an OUTPUT/generation-config
    limitation, NOT a *tool*, so it shouldn't sit inside the unsupported-*tools* line; list it
    separately (e.g. "also unsupported: structured outputs, custom generation config,
    audio/video inputs"). This is a strength too — it shows we read the limits carefully.

### C3. Is the base agent ID real?  — CONFIRMED
- **Claim:** `antigravity-preview-05-2026`.
- **Attack:** the `-preview-05-2026` suffix could be invented; a wrong ID = nothing runs.
- **Evidence:** doc, verbatim: *"Only `antigravity-preview-05-2026` is supported as
  `base_agent`."* Used consistently across all code examples. Powered by Gemini 3.5 Flash.
  - https://ai.google.dev/gemini-api/docs/antigravity-agent
- **Verdict: CONFIRMED.** Exact string is right and is the only accepted value.

### C4. Can the agent compile + run REAL COBOL via GnuCOBOL in the sandbox?  — NEEDS FIX (was FALSE; re-scoped after product correction)
- **Claim:** README §2.4 "compiles & runs the *original* COBOL via GnuCOBOL inside the
  sandbox"; ARCHITECTURE "GnuCOBOL pre-warmed / pre-installed into base_environment";
  DEMO 0:35 "compiles & runs the original COBOL via GnuCOBOL." This is the **#1
  anti-objection**: "we run the real program, not self-graded tests."
- **Attack:** GnuCOBOL (`cobc`) is a system binary normally installed via `apt`. Question is
  whether the **Gemini API** sandbox permits that (network + apt + root).
- **SELF-CORRECTION (the lead caught a product mix-up — important).** My first pass cited
  `docs.cloud.google.com` (**Enterprise Agent Platform**), which says network is *disabled by
  default* and there's *no root*. That is the WRONG product. The hackathon uses the **Gemini
  API** at `ai.google.dev`, where the facts are materially different:
  - **Network is ON by default:** *"By default, environments have unrestricted outbound
    network access."* (Opposite of what I first reported.) So a network-gated apt is NOT the
    blocker on this product.
  - Runtime install is documented only as `pip install` / `npm install`.
  - **apt / sudo / root: absent** (task #8). So `apt-get install gnucobol` can't run — BUT a
    USERLAND install works: `micromamba`/`conda install -c conda-forge gnucobol` at pre-warm
    (no root, network on, persists in the env). Live compile is recoverable this way. (Mounting
    a precompiled binary is NOT an option — "Binary file support is not yet available.")
  - Preinstalled list: Python 3.12, Node 22, **4 cores / 16 GB**, `git` preinstalled, Unix
    tools (curl/jq/gcloud/ripgrep/…), google-genai, numpy, pandas. **`cobc` is NOT in it.**
  - https://ai.google.dev/gemini-api/docs/agent-environment
  - https://ai.google.dev/gemini-api/docs/antigravity-agent
- **Verdict: NEEDS FIX (was FALSE; corrected after product fix + lead source-check).** The
  ONLY genuinely-wrong thing is the **mechanism**: "`apt-get install gnucobol` / GnuCOBOL
  **pre-installed/pre-warmed in base_environment**." cobc is NOT in the preinstalled list,
  there's no base-image customization, and apt/root are undocumented (absent). Fix that
  wording. The "**run real COBOL live**" BEAT is RECOVERABLE and the falsifiability is INTACT.
  Paths:
  - **LIVE-COMPILE IS VIABLE — THE AGENT INSTALLS GnuCOBOL ITSELF (lead + task #8 verified;
    FINAL mechanism):** at PRE-WARM the agent installs GnuCOBOL into the sandbox via a
    **userland package manager** — `micromamba` / `conda install -c conda-forge gnucobol` into
    the long-lived environment. KEY FACT: the conda-forge `gnucobol` package pulls its OWN
    compiler + `libcob` + `gmp`, so it works with NO system `gcc` and NO root. Network is ON by
    default; the install persists in the `environment_id`, which is REUSED on stage → NO network
    needed during the live run. The agent then compiles + runs the REAL COBOL live. Full "live
    compile" beat recovered without apt/root. (researcher-gemini has a bundle-`libcob` backup recipe.)
  - **FALLBACK FLOOR (DE-RISKED TODAY):** `golden_io.json` captured from REAL GnuCOBOL
    pre-event (I cross-verified backend-eng's, 10/10 byte-exact — see C5). Falsifiable,
    deterministic, network-free. Keep as the cached fallback.
  - **REJECTED — mounted precompiled binary:** ai.google.dev states verbatim *"Binary file
    support is not yet available"* (sources are inline-text / git / gcs only, and a committed
    binary in a repo source is not reliably executable). Do NOT use this path. (My earlier
    "mount a static cobc binary" suggestion is SUPERSEDED.)
  - **REJECTED — live apt:** apt needs root; root is absent. Use the userland conda install.
  - **RESIDUAL RISKS to verify live before stage (NEEDS-VERIFY, per researcher-agents):**
    (a) root/sudo undocumented → apt unreliable, so the conda path is mandatory not optional;
    (b) the conda-forge package shipping its own compiler+libcob+gmp is the reason no system
    `gcc`/`gmp` is needed — but the actual `micromamba install` + `cobc` run must be smoke-tested
    in a real sandbox the morning of (task #8/#9); (c) keep golden_io.json as the captured-output
    fallback so the differential oracle stays honest if the live install flakes on stage.
  - **Honesty bottom line:** falsifiability is INTACT — it's the real compiler's output whether
    live (conda-installed cobc) or pre-captured (golden_io.json). The docs only need the
    **mechanism** corrected: drop "apt-get / pre-install into base_environment"; say "the agent
    micromamba/conda-forge-installs GnuCOBOL at pre-warm into the reused environment, then
    compiles + runs the real COBOL live." The #1 anti-objection ("we run the real program") survives fully.

### C5. Is the "byte-for-byte" diff robust, or does it fail for formatting reasons?  — NEEDS FIX
> **EMPIRICALLY TESTED** — I compiled `src/sample/payroll.cob` with the real GnuCOBOL 3.2.0
> (`cobc -x`) and ran it against naive + correct Python. Outputs below are real bytes, not
> speculation. (Workspace: `/tmp/lazarus_oracle_test`.)
- **Claim:** ARCHITECTURE §3 + oracle code assert `python_output == cobol_output`
  byte-for-byte; a non-zero diff is shown as RED on stage.
- **TWO independent failure layers, both REPRODUCED:**
  1. **FORMAT (fails on EVERY input).** `DISPLAY WS-NET` (PIC `9(7)V99`) emits the full
     PICTURE width: 7 integer digits **zero-padded**, the decimal point, 2 decimals, then
     `\n`. Measured bytes: gross 1000.00 → `0000775.00\n`; gross 0.01 → `0000000.01\n`;
     gross 999999.99 → `0774999.99\n`. Naive Python `print(net)` emits `775.0`. Never
     byte-equal. (CORRECTION to an earlier note in this log: GnuCOBOL 3.2 *does* print the
     `.` for this PIC — the divergence is the **zero-padding + the `775.0` vs `775.00`
     decimals**, not a missing point.)
  2. **ROUNDING (fails on half-cent inputs).** `COMPUTE WS-TAX ROUNDED` = round-half-UP.
     Python's default `round()` = banker's (half-EVEN). On `gross=5.00`: tax_raw =
     1.12500 → COBOL tax 1.13 → net **`0000003.87`**; naive Python `round()` → tax 1.12 →
     net **`3.88`**. The VALUES differ by a cent (not just format). Reproduced for gross ∈
     {0.20, 1.00, 1.80, 2.60, 3.40, 4.20, 5.00, …} (any gross where gross×0.225 lands on an
     exact half-cent).
- **THREE more divergence sources REPRODUCED** (will go RED if the input battery isn't curated):
  - **Silent high-order truncation:** the field is `9(7)` so values > 9999999.99 wrap.
    gross 12345678.99 → COBOL uses `2345678.99`, net `1817901.22`. Naive Python wouldn't truncate.
  - **Unsigned field eats the sign:** field has no `S`. gross `-100.00` → COBOL net
    `0000077.50` (same as +100.00). Naive Python would produce a negative number.
  - **`NUMVAL` of garbage → 0:** input `abc` or empty → COBOL `0000000.00`. Naive Python
    `Decimal("abc")` raises. Battery must be clean numeric strings.
- **Bonus (kills C13):** I compiled a `USAGE DISPLAY` variant (COMP-3 removed) — DISPLAY
  output is **byte-identical** to the COMP-3 version. So COMP-3 storage has ZERO effect on
  the diff (see C13).
- **Evidence:** local GnuCOBOL 3.2.0 run, hexdumped. Corroborating:
  - https://gnucobol.sourceforge.io/HTML/gnucobpg.html
  - COBOL `ROUNDED` defaults to ROUND-HALF-UP; Python `round()` is round-half-even.
    https://www.ibm.com/docs/en/cobol-zos (arithmetic / ROUNDED); Python docs `round()`.
- **Verdict: NEEDS FIX.** The diff IS falsifiable (good) but brittle. **PROVEN-CORRECT
  oracle pattern (I verified 9/9 byte-exact):**
  1. Python math in `decimal.Decimal`, `.quantize(Decimal("0.01"), ROUND_HALF_UP)` for the
     tax (matches COBOL `ROUNDED`). NEVER float / default `round()`.
  2. Format Python to the COBOL PICTURE: `f"{int(net):07d}.{cents:02d}"` so it emits
     `0000775.00`. Then byte-for-byte `==` against COBOL stdout passes exactly.
  3. Compare with the trailing `\n` included, or `.rstrip("\n")` both sides and SAY so.
  4. **Curate the input battery** to non-negative values ≤ 9999999.99 with clean numeric
     strings — OR have the Python replicate truncation/abs/NUMVAL-zero semantics (harder).
     The current battery (`1000.00`, `0.01`, `999999.99`) is safe; do NOT add overflow /
     negative / garbage unless intentionally demonstrating those idioms.
  5. The RED→GREEN beat should be the rounding-mode + zero-pad-format fix (the real idiom,
     see C13), NOT "COMP-3". Rehearse that the forged SKILL.md content produces exactly this.
  (Sent backend-eng the proven pattern + battery guidance.)
- **INDEPENDENT VERIFICATION (2026-05-23, devils-advocate) — C5 oracle RESOLVED.**
  backend-eng committed `src/sample/golden_io.json` (10 cases) + `payroll.py`. I compiled the
  committed `payroll.cob` with MY OWN GnuCOBOL 3.2.0 and cross-checked:
  - All **10/10** committed `golden_io.json` `cobol` byte-strings MATCH my independent
    captures byte-for-byte (incl. ties 1.00→`0000000.77`, 5.00→`0000003.87`, and
    9999999.99→`7749999.99`). Ground truth is genuinely REAL, not computed.
  - `payroll.py` is **byte-equivalent to the real COBOL 10/10** (`Decimal`+`ROUND_HALF_UP` +
    `{:07d}.{frac:02d}`, exactly as recommended).
  - The UI mock failing-case (`99999.99` → COBOL `0077499.99`, naive Python `0077500.00`) is a
    REAL divergence, verified against the binary.
  - The byte-exact comparison is correct and independently confirmed.

---

## New challenges (found while attacking)

### C6. Sandbox spec drift  — ~~NEEDS FIX~~ → **CONFIRMED (repo is CORRECT)**
> **RESOLVED — the repo's numbers are right; my original critique was wrong-product.** The
> lead verified at the source (`ai.google.dev/gemini-api/docs/agent-environment.md.txt`).
> My first-pass evidence came from `docs.cloud.google.com` (**Gemini Enterprise Agent
> Platform** — a DIFFERENT product). The hackathon uses the **Gemini API** Antigravity agent.
- **Claim:** ARCHITECTURE §4: "Python 3.12, Node 22"; "4 CPU / 16 GB"; "Sandboxes
  auto-snapshot after 15 min idle and are retained 7 days."
- **Evidence (CORRECT product — ai.google.dev Gemini API, lead-verified verbatim):**
  - Python **3.12**, Node.js **22**, **4 cores, 16 GB** — **MATCHES the repo. All correct.**
  - Lifecycle: Idle "Auto-snapshot after 15 min"; Offline "Retained 7 days since last
    active." **MATCHES the repo.**
  - Network is ON by default ("unrestricted outbound network access"); `git` is preinstalled;
    repository sources can mount arbitrary files; `pip`/`npm` install available at runtime.
  - https://ai.google.dev/gemini-api/docs/agent-environment
- **Verdict: CONFIRMED.** Do NOT change the env-spec numbers — the 3.11/Node20/7-day-TTL
  edits I floated earlier would INTRODUCE errors. Optional one-liner: add a note that the
  conflicting `docs.cloud.google.com` numbers belong to a different product, so a judge who
  Googles them isn't confused.
- **LESSON (recorded in memory):** source every sandbox/network/spec fact to `ai.google.dev`
  (Gemini API), NOT `docs.cloud.google.com` (Enterprise Agent Platform). The docs are
  genuinely confusing — same-sounding products, different specs.

### C7. New Jersey impact stats  — MIXED (one number unverified)
- **Claim:** README §1 "1,600% surge" + "575,000+ filings backlogged in weeks" + governor
  "publicly begged"; DEMO 0:00 "the governor *begged* on live TV."
- **Evidence:**
  - **1,600% surge — CONFIRMED.** Widely reported; "1,600% increase in volume in
    unemployment claims" first week.
    - https://www.govtech.com/computing/As-Unemployment-Claims-Spike-New-Jersey-Seeks-COBOL-Coders.html
    - https://whyy.org/articles/why-n-j-wants-coders-fluent-in-a-60-year-old-language-in-the-middle-of-a-pandemic/
  - **Governor's COBOL call — CONFIRMED** (Murphy press briefing; many volunteers responded).
    - https://www.cnbc.com/2020/04/06/new-jersey-seeks-cobol-programmers-to-fix-unemployment-system.html
  - **"575,000+ backlogged in weeks" — UNVERIFIED / no source.** I found NO source for
    "575,000 backlogged." (CORRECTION to my own earlier note: I'd suggested "362,000 in the
    first week" as the replacement — that is ALSO WRONG. doc-keeper found the NJ DOL primary
    source: **362,000 is the TWO-WEEK total** (week ending 3/28 = 206,253; prior week =
    155,815). First week alone was ~206K, not 362K.)
    - https://www.nj.gov/labor/lwdhome/press/2020/20200402_unemployment.shtml
  - **"begged on live TV" — EMBELLISHED.** It was a press briefing / news appeal, not a
    dramatic live-TV plea. Minor, but a journalist-minded judge could call it.
- **Verdict: MIXED → NEEDS FIX on the 575k number (RESOLVED by doc-keeper).** doc-keeper
  applied the correct sourced figure: "over **362,000** new claims in **two weeks**" (NJ DOL,
  4/2/2020) and "publicly called for volunteers." Do NOT use "362,000 first week" (that's the
  two-week total) or "575,000" (unsourced). This one is now landed correctly in the docs.

### C8. Macro impact stats  — CONFIRMED (with date caveats)
- **$2.41T tech debt — CONFIRMED.** CISQ/Synopsys "Cost of Poor Software Quality in the
  US: A 2022 Report" — exact figure $2.41T (of which ~$1.52T is accumulated tech debt).
  Caveat: it's a **2022 total annual estimate**, so "~$2.41T/year" is fair but cite the year.
  - https://www.it-cisq.org/the-cost-of-poor-quality-software-in-the-us-a-2022-report/
  - https://news.synopsys.com/2022-12-06-Software-Quality-Issues-in-the-U-S-Cost-an-Estimated-2-41-Trillion-in-2022
- **18–23% time on bad code — CONFIRMED.** Stripe 2018 "Developer Coefficient" report.
  Caveat: 2018 data; say "Stripe found."
  - https://stripe.com/files/reports/the-developer-coefficient.pdf
- **$30B+ modernization market — CONFIRMED.** Mordor: $29.39B (2026); Grand View ~$30B
  (2026); convergent across 5 firms. "$30B+" is accurate.
  - https://www.mordorintelligence.com/industry-reports/legacy-modernization-market
- **Verdict: CONFIRMED.** Add the source/year inline so a judge's spot-check passes.

### C9. "1M-token context" used on a ~150-line module  — NEEDS FIX (framing)
- **Claim:** README/DEMO repeatedly tout reading "the entire module using the 1M-token
  context window." Gemini 3.5 Flash's 1,048,576-token context is real (CONFIRMED) — but the
  golden demo module is **~150 lines (~600 tokens)** per ARCHITECTURE §7 / DEMO checklist.
- **Attack:** Touting a 1M context for a 600-token file is a non-sequitur. A sharp DeepMind
  judge asks "why does 1M context matter for 150 lines?" and the live demo can't show it.
- **Verdict: NEEDS FIX (framing).** Either (a) demote the 1M line in the *demo* narration
  and reposition it as the *scalability* answer ("the SAME loop ingests a 50k-line module in
  one shot"), with a real large-file artifact to point to; or (b) drop the claim from the
  live beats entirely. Don't lead the demo with a feature the demo doesn't exercise.

### C10. `MAX_ITERATIONS = 4` "hard cap" + "visible counter"  — NEEDS FIX
- **Claim:** ARCHITECTURE §7 + DEMO checklist: "Hard-cap iterations at 4 with a visible
  counter — an infinite loop on stage is death."
- **Attack:** in `src/agent.py`, `MAX_ITERATIONS = 4` is only **string-interpolated into the
  prompt** ("Stop ... after 4 iterations"). There is NO orchestrator-side loop, NO counter,
  NO kill switch. The model can ignore the instruction and loop; the "visible counter" UI
  does not exist. The single safety net the demo leans on is not actually enforced.
- **Verdict: ~~NEEDS FIX~~ → RESOLVED (verified in code 2026-05-23).** backend-eng now
  enforces it: `src/agent.py` has a real `for iteration in range(1, MAX_ITERATIONS + 1)` loop
  with a per-turn `emit_iteration(current, total)` counter (docstring: "The MAX_ITERATIONS cap
  is ENFORCED here in code (C10) … the loop hard-stops at MAX_ITERATIONS"). `src/server.py`
  forwards it as a `phase` event with `iteration`/`iteration_cap` to the UI, and `/api/health`
  exposes `max_iterations`. Orchestrator-side loop + visible counter + hard stop — exactly the
  fix. No longer a prompt-only suggestion.

### C11. agent.py uses unverified SDK / streaming field names  — NEEDS FIX
- **Claim:** agent.py reads `event.event_type == "step.delta"`, `event.delta`, `delta.type
  == "text"`, `delta.text`, and `interaction.environment_id` / `.output_text` / `.steps`.
- **Attack:** these field/enum names are guessed, not quoted from the SDK. If the real SSE
  schema differs (e.g. `event.type`, `chunk.text`, a different terminal-event shape), the UI
  shows nothing or the script crashes at 0:12 on stage. Also `client.agents.create` is shown
  with `base_environment=` — confirm the param name (some docs show `environment` for runs vs
  `base_environment` for create) and that `interactions.create` accepts `environment="remote"`.
- **Evidence:** the public examples emphasize `interaction.steps` and `environment_id`
  reuse, but the exact streaming event/delta schema must be read from the live SDK reference.
  - https://ai.google.dev/gemini-api/docs/managed-agents-quickstart
  - https://ai.google.dev/gemini-api/docs/custom-agents
- **Verdict: NEEDS FIX (verify).** backend-eng/researcher-agents must reconcile every field
  name against the live `google-genai` reference before the UI is wired. Don't ship guessed
  attribute names into the 45%-weighted live demo. (This overlaps task #5.)

### C12. Demo determinism + cold-start  — ACCEPTED RISK (tighten)
- **Claim:** "Deterministic, single sandbox call, no network." DEMO mitigations: pre-warm,
  pin seed, cached fallback, backup video.
- **Attack:** LLM agents are NOT deterministic even with a fixed seed once tool-use branches;
  "pin seed" does not guarantee identical tool sequences. Cold-start (~fresh sandbox) +
  model latency can blow the 1:55 budget. "No network" conflicts with C4 if the agent must
  `pip install` anything (network must be ON for that) — pick one story.
- **Verdict: ACCEPTED RISK,** *given* the cached-green fallback + backup video are real and
  rehearsed. Tighten: (1) rehearse 10× and MEASURE p95 runtime vs the 1:55 budget; (2) make
  the Safety cutover to cached-green instant and visually identical; (3) resolve the
  "no network" vs "pip install" contradiction (if the oracle is golden_io.json + a mounted
  binary, you genuinely need no network — say that). The fallback being indistinguishable
  from the live run is doing the real de-risking here; protect it.

### C13. The demo's central beat MISATTRIBUTES why the test fails  — NEEDS FIX (narrative honesty)
- **Claim:** DEMO 0:55 + payroll.cob header + ARCHITECTURE §7: the agent "diagnoses:
  unsupported `COMP-3` packed-decimal" as the reason tests are RED, then forges a COMP-3
  SKILL.md to fix it. COMP-3 is presented as "the unknown idiom that triggers the forge."
- **Attack:** COMP-3 is a *storage* encoding (BCD packed). A competent translator just reads
  a COMP-3 field as a decimal — the packed representation never leaves the COBOL runtime and
  has NO effect on `DISPLAY` output. GnuCOBOL `DISPLAY` of an unedited numeric **de-edits**
  the value to its raw PICTURE form identically whether it's `COMP-3` or `USAGE DISPLAY`. So
  the ACTUAL cause of a RED diff on payroll.cob is (i) DISPLAY de-editing (`0077500` vs
  `775.00`/`775.0`) and (ii) ROUNDED rounding-mode mismatch — NOT "we don't understand
  COMP-3." A DeepMind/COBOL-literate judge asking "is COMP-3 really what broke it?" punctures
  the story.
- **Evidence — EMPIRICALLY PROVEN.** I compiled `payroll.cob` twice with real GnuCOBOL
  3.2.0: once as-is (COMP-3) and once with `COMP-3` stripped (`USAGE DISPLAY`). The DISPLAY
  output is **byte-identical** across both (gross 1000.00 → `0000775.00` either way; gross
  5.00 → `0000003.87` either way). The packed storage has ZERO effect on what DISPLAY emits.
  The real RED comes from format + rounding (see C5), which COMP-3 does not cause.
  Corroborating sources:
  - https://www.mainframestechhelp.com/tutorials/cobol/comp-3.htm
  - https://gnucobol.sourceforge.io/HTML/gnucobpg.html
  - http://www.simotime.com/datapk01.htm
- **Verdict: NEEDS FIX (narrative honesty) — NOT YET LANDED as of 2026-05-23.** Recommended
  fix (lead-confirmed): re-label the forged skill to the TRUE idiom — "COBOL numeric DISPLAY
  format (zero-pad/de-edit) + ROUND-HALF-UP equivalence." The forge beat survives intact; only
  the idiom LABEL changes to one that's actually true. **STATUS: the relabel has NOT been
  applied — "COMP-3 is what fails" still pervades the demo-facing files.** Exact occurrences a
  COBOL-literate judge would catch (audited 2026-05-23):
  - `web/mock/mock-run.json` (DRIVES the on-stage UI): line 22 business_rule "COMP-3 half-up
    rounding on tax" / "tax is ROUNDED into a packed-decimal field"; line 44 fail message
    "byte mismatch — COMP-3 ROUNDED is half-up"; lines 51–78 forge `.agents/skills/comp-3/
    SKILL.md` titled "COMP-3 packed-decimal rounding"; lines 80,83 "comp-3 skill". **Highest
    priority — this is the literal demo script.**
  - `web/STREAM_CONTRACT.md` lines 93,110,111,115,121 (comp-3 skill path + reason).
  - `docs/DEMO_SCRIPT.md` line 17 "Agent diagnoses: unsupported `COMP-3` packed-decimal."
  - `README.md` line 28; `docs/ARCHITECTURE.md` lines 44,94; `.agents/AGENTS.md` line 21;
    `tests/test_agent.py` lines 156,160,209,210 (assert "comp-3" in the forge path).
  - **Caveat — the COBOL itself legitimately USES `COMP-3`** (`src/sample/payroll.cob` lines
    11,13,14 declare `PIC 9(7)V99 COMP-3`). Keeping COMP-3 as a *data type present in the
    source* is fine and authentic. What's WRONG is claiming COMP-3 is the *cause of the test
    failure / the thing the forged skill fixes*. The skill should be named/described for the
    rounding+format idiom; the COBOL can still contain COMP-3 fields.
  - Owners: backend-eng (skill name/path + test_agent.py), frontend-eng/doc-keeper
    (mock-run.json, STREAM_CONTRACT.md, DEMO_SCRIPT, README, ARCHITECTURE, AGENTS.md).

### C14. BUILD_PLAN / requirements assume the impossible install + a self-contradiction  — NEEDS FIX
- **Claim:** BUILD_PLAN.md 11:00–11:30 "install + pin GnuCOBOL into `base_environment`;
  verify it persists." requirements.txt line 6: "`apt-get install -y gnucobol`." DEMO/BUILD
  also insist "**No network** in the demo path."
- **Attack:** (1) Same as C4 — apt install of a system package can't run (no root, network off
  by default, no documented base_environment pre-bake). The 11:00–11:30 milestone is a task
  that cannot complete; it will silently eat 30 min on the build day. (2) **Internal
  contradiction:** "install gnucobol at runtime" REQUIRES network ON; "no network in the
  demo path" REQUIRES it OFF. You can't have both. If GnuCOBOL must be installed live, the
  demo is NOT network-free; if the demo is network-free, GnuCOBOL must already be present
  (which the docs don't support).
- **Evidence:** see C4. **Resolved with C4:** apt/root are absent, so the *apt* form of the
  milestone can't run; but the Gemini API sandbox has network ON by default, so a USERLAND
  install (no root) at pre-warm IS viable.
- **Verdict: NEEDS FIX (resolved via C4).** Rewrite the BUILD_PLAN "apt-get install + pin
  GnuCOBOL into base_environment" milestone to the FINAL mechanism: **the agent userland-installs
  GnuCOBOL at pre-warm** — `micromamba`/`conda install -c conda-forge gnucobol` (network on, no
  root; persists in the env for the session). requirements.txt line 6 (`apt-get install -y
  gnucobol`) -> drop/replace with a comment about the conda pre-warm install. (NOT a mounted
  binary — "Binary file support is not yet available"; NOT apt — no root.) NOTE: the pre-warm
  install needs network DURING pre-warm; the demo runs network-free AFTER, since the package
  persists in the reused env — so reword "no network in demo path" to "no network during the
  live demo run (deps installed at pre-warm)" to remove the apparent contradiction.
  golden_io.json (real-cobc capture) is the cached fallback.

### C15. `google-genai>=1.55.0` version pin is unverified  — VERIFY
- **Claim:** agent.py + requirements.txt assert the Interactions API needs
  `google-genai >= 1.55.0`.
- **Attack:** if the real minimum differs, `pip install -r requirements.txt` could pull a
  version missing `client.interactions` / `client.agents`, and nothing runs. The number
  reads precise but I have not seen it in a primary source.
- **Verdict: RESOLVED for the install; NEEDS FIX for 3 stale doc references.** The catch was
  correct AND the true floor is higher than I first recorded. Per the official SDK CHANGELOG
  (researcher-agents, verbatim): interactions debuted in 1.55.0; the `step.*` /
  `interaction.completed` SSE schema is 2.0.0 (BREAKING rename); `interaction.output_text` is
  2.3.0; and **`client.agents` (Agent + Environment APIs) ships in 2.4.0 (2026-05-17)**. So the
  EXACT minimum for THIS project (we use `client.agents` + environment sources + the step.* SSE
  schema) is **`google-genai >= 2.4.0`** — NOT 2.0.0 (which lacks `client.agents`).
  - **Install is FINE:** `requirements.txt` pins `>=2.6.0,<3.0.0` and `agent.py` `>=2.6.0` —
    both already satisfy `>=2.4.0`. Nothing breaks.
  - **NEEDS FIX (doc accuracy):** three places still state the wrong minimum "**>= 2.0.0**" —
    README L51, ARCHITECTURE L77, requirements.txt L8 (comment). 2.0.0 predates `client.agents`
    by two minors; a judge checking the changelog catches it. Change those three "2.0.0" → "2.4.0"
    (or just say "2.6.0 pinned"). doc-keeper/backend-eng lane.

### C16. Demo UI claims "hot-reloading agent" mid-interaction  — NEEDS FIX (NOT LANDED in web/)
- **Claim:** the web/ demo surface says the agent **hot-reloads** the skill it just authored,
  live, mid-run. `web/STREAM_CONTRACT.md` L107 "the agent writes itself a new skill and
  **hot-reloads**", L119 "`reload` — agent **hot-reloads** with the new skill", L121 label
  "**Hot-reloading** agent…"; `web/mock/mock-run.json` L80 "**Hot-reloading** agent…", L83
  "**Reloaded.** The … skill is now active."
- **Attack:** mid-interaction hot-reload of an agent-authored SKILL.md is **UNVERIFIED** —
  researcher-agents found ZERO doc language for "re-scanned mid-interaction"; auto-discovery is
  a **STARTUP/scan** event. Files persist on disk (verbatim: "Packages installed during an
  interaction persist when you reuse the same environment_id"), so the honest claim is
  persist-to-disk + **re-discovery on the next pass** (reuse `environment_id`), NOT a live
  in-flight reload. A DeepMind judge who knows the API will ask "does it really hot-reload
  mid-thought?" — and the honest answer is no.
- **Evidence:** docs/research/findings-agents.md (researcher-agents, verbatim quotes);
  custom-agents.md.txt describes startup auto-load. Our OWN docs already say this correctly:
  README L28 / ARCHITECTURE L53 / BUILD_PLAN L22 / AGENTS.md L47 all state "no mid-run
  hot-reload; re-discovery on the next pass." Only the web/ surface contradicts them.
- **Verdict: NEEDS FIX — NOT LANDED in web/.** Reword the UI: "reload" step → "**re-discovers
  the skill on the next pass (same environment)**", drop "Hot-reloading"/"hot-reloads". Same
  files as C13 (mock-run.json + STREAM_CONTRACT) — fold into the one web/ rewrite pass.
  (Docs lane already compliant; this is purely the demo surface.)

---

## Summary for the lead  (updated after the product correction)

> **Product note (drives everything below):** all sandbox/network/spec facts must be sourced
> to the **Gemini API** (`ai.google.dev`), NOT the **Enterprise Agent Platform**
> (`docs.cloud.google.com`). I initially mixed them; the lead caught it. On the Gemini API:
> network is ON by default, Python 3.12 / Node 22, 15-min idle snapshot / 7-day retention.

- **C5 (TESTED) — RESOLVED + INDEPENDENTLY VERIFIED.** The byte-exact comparison is correct:
  I compiled the committed `payroll.cob` with my own GnuCOBOL 3.2.0 and confirmed backend-eng's
  `golden_io.json` (10/10) AND `payroll.py` (10/10) are byte-for-byte equivalent to the real
  COBOL, including the half-cent tie cases. Nothing more to do here.
- **#1 REMAINING FIX — C13 (PROVEN) — NOT YET LANDED.** The signature forge beat still blames
  "COMP-3," which is empirically false (COMP-3 and USAGE-DISPLAY give byte-identical output;
  the real cause is rounding + zero-pad format). Still present in `web/mock/mock-run.json` (the
  literal on-stage UI script), `web/STREAM_CONTRACT.md`, `DEMO_SCRIPT.md`, `README.md`,
  `ARCHITECTURE.md`, `.agents/AGENTS.md`, `tests/test_agent.py`. Re-label the forged skill to
  "numeric DISPLAY format + ROUND-HALF-UP." (The COBOL keeping COMP-3 *fields* is fine — just
  stop claiming COMP-3 is what FAILS.) This is now the highest-priority honesty item.
- **C4 — NEEDS FIX (was FALSE; finalized).** Falsifiability INTACT. Only the MECHANISM is
  wrong: "apt-get / pre-install GnuCOBOL into base_environment." **Live-compile SURVIVES**
  (lead/task #8): the AGENT userland-installs `micromamba`/`conda install -c conda-forge
  gnucobol` at pre-warm (ships its own compiler+libcob+gmp, no root) into the reused env_id
  (no network needed live). golden_io.json (real-cobc capture, cross-verified) = cached
  fallback. (Mounted-binary path REJECTED — "Binary file support is not yet available.")
- **Other honesty fixes (a DeepMind judge will catch):** **C1b** (forged skills don't persist
  across fresh agent invocations — "forks clean"), **C7** (NJ "575k backlogged" unsourced;
  1600% IS confirmed), **C9** (1M context irrelevant to a 150-line demo file).
- **Engineering gaps:** **C10** (the "hard cap at 4 + counter" isn't enforced in code, only in
  the prompt), **C11** (guessed SDK/streaming field names). **C15 RESOLVED** — my catch was
  right (floor is `>=2.0.0`, not 1.55.0); repo already bumped to `>=2.6.0,<3.0.0`.
- **RETRACTED — my errors, corrected:** **C6 → CONFIRMED** (lead verified at the source: the
  repo's Python 3.12 / Node 22 / **4 cores / 16 GB** / 15-min-snapshot / 7-day-retention are
  ALL correct for the Gemini API; I'd cited the Enterprise Agent Platform). Do NOT edit those
  numbers — the changes I floated earlier would introduce errors.
- **Holding up well — lean into these:** **C2** (honesty framing genuinely accurate —
  computer_use/file_search really are unsupported), **C3** (correct agent ID), **C8** (macro
  stats $2.41T / 18-23% / $30B all check out — add inline cites), **C1 mechanism** (runtime
  skill discovery is real). The differential-oracle CONCEPT is sound and falsifiable; the work
  is in the byte-exact comparison (C5) and a few honest wording fixes.
