# CHALLENGES v2 — Devil's Advocate on the LIVE demo (owner: devils-advocate)

> Scope: the v2 completion plan (docs/plans/2026-05-23-completion-v2.md). A skeptical
> DeepMind judge AND an investor watch the 2-minute LIVE run on the real key and fact-check
> everything. The question is not "does the mock look done" — it's "does a LIVE run on the
> provisioned key drive EVERY panel from REAL agent work, honestly."
>
> Format per item: **claim / attack / evidence / verdict** (CONFIRMED · NEEDS FIX · FALSE).
> Stop-the-line items go to team-lead immediately.
>
> v1 challenges C1–C16 live in CHALLENGES.md and are not re-litigated here unless the live
> path changes the verdict.

---

## SCOREBOARD

> **UPDATE — wiring now COMMITTED (64d8579 "Wire LIVE path to populate all panels").** Verified
> HEAD's server.py carries the wiring (not reverted). Two follow-on improvements landed (working
> tree) that close my two minor nits: (a) `to_pytest_event` now sets `source:"agent_pytest"` so
> the UI distinguishes the agent's own marker-pytest from the orchestrator's `differential_oracle`
> harness — honest symmetry; (b) `.agents/AGENTS.md` reinforces the L8 path pin ("write the final
> module to /workspace/payroll.py … writing it elsewhere leaves those panels empty"). 77/77 pass.
>
> **UPDATE 18:37 — the wiring LANDED (uncommitted working tree).** server.py grew 277→419
> lines; integration-eng wired every helper. All of L1/L3/L4/L7/L8 are now FIXED IN CODE and
> covered by 10 new tests (77/77 pass). The only remaining gate is LIVE EVIDENCE (L2/L6),
> which I cannot produce (no key). Verdicts below updated; the original NEEDS-FIX analysis is
> kept for the record under each item.

| # | Item | Severity | Verdict |
|---|---|---|---|
| L1 | LIVE run populates EVERY panel (not just the mock) | stop-the-line | **FIXED IN CODE (pending live)** — server.py now emits `diff`, runs the local differential-oracle pytest fallback, fallback rules, and progressive phases. Tested by test_safety_net_populates_every_panel_without_markers (no markers → diff + 10-case oracle pytest + ≥3 rules + banner). |
| L2 | Downloaded payroll.py is the agent's REAL sandbox output (Files API) | load-bearing (honesty) | **GAP FOUND (qa) → MITIGATED + mechanism VERIFIED; pending end-to-end live stream.** Live Files-API tarball TIMED OUT → diff+download blanked (see L9). Committed fallback (49cc1d9) scrapes the agent's echoed module (source="model_output"). qa + I independently confirmed the scrape recovers the real module + passes oracle 10/10. Awaiting qa's full live stream (diff fires + download returns it + budget). |
| L3 | Local-oracle pytest presented truthfully (orchestrator IS the harness) | load-bearing (honesty) | **CONFIRMED + WIRED** — server.py:308 uses `oracle_harness_pytest_event` (source="differential_oracle", `oracle_equivalence[...]` case names, honest summary). NOT framed as the agent's own pytest. Tested. |
| L4 | Phase progression is REAL (agent milestones), not faked timing | medium | **FIXED IN CODE (pending live)** — `phase_for_text` drives a forward-only, dedup'd rail off the streamed step text; the iteration counter no longer jumps the rail to TEST. Tested by test_phase_rail_advances_progressively (monotonic). |
| L5 | golden_io.json (local truth) vs agent's own cobc — conflated? | load-bearing (honesty) | **CONFIRMED honest** — golden is the PRIMARY ground truth; agent live-refresh is opportunistic; prompt + oracle code keep them distinct. No conflation. |
| L6 | 2-minute story legible for a judge | demo (45%) | **RESOLVED via L10 → STRICTLY LIVE (user's call).** Not a 2-min story; reframed as "watch a real multi-minute migration + byte-for-byte proof." Live narrative drafted (DEMO_NARRATIVE_live-DRAFT.md). Legibility now hinges on L11 (UI must visibly progress). |
| L10 | LIVE latency (8–12+ min) vs the "2-minute" framing | demo (45%, decisive) | **RESOLVED (user decision): STRICTLY LIVE in-slot, no mock lead** — user accepts the multi-minute reality; value = real work + proof, not speed. Honest live narrative drafted. Mock stays `?mock=1` break-glass only. |
| L11 | Does the live UI visibly PROGRESS during the long run, or look FROZEN? | demo (45%, decisive) | **OPEN — #1 risk for strictly-live.** If the agent streams step text, the banner/trace move (alive). If silent until the end-burst, the screen looks hung for minutes → "watch it work" collapses. qa to confirm; if frozen, add live-progress surfacing (elapsed timer + step.delta streaming) BEFORE the slot. |
| L7 | Missing `diff` made the COBOL→Python card VANISH (reveal-gated) | demo (45%) | **FIXED IN CODE** — `diff_event(cobol, migrated)` emitted from real sources → translate card reveals. Tested (diff right-side == the agent's real module). |
| L8 | Live download/diff/oracle depended on an UNPINNED payroll.py path | load-bearing (honesty) | **FIXED IN CODE (pending live)** — agent.py:136 now pins "write the final module to /workspace/payroll.py", matching the extractor. qa to confirm the agent honors it live. |

### THE falsifiability guarantee — now ENFORCED + TESTED
`test_safety_net_goes_red_when_module_diverges`: a naive port (banker's rounding) that FAILS the
tie cases makes the orchestrator's differential oracle go **RED** with per-case bytes and the
verdict **INCOMPLETE** — *even when the agent's prose claims "all tests pass."* The verdict is
gated on the orchestrator's real byte-comparison (server.py:312, `passed = pytest_ev["result"]
== "green"`), not the agent's self-report. This is the project's core honesty claim, and it is
now provably true: the agent cannot fake equivalence past the oracle. STRONG.

---

## L1 — Does the LIVE run populate EVERY panel, or only the mock?  — NEEDS FIX (STOP-THE-LINE)

- **Claim (v2 plan, Definition of Done):** "A single LIVE run on the real key drives the whole
  UI — phases advance; rules, diff, oracle, per-case RED→GREEN, forge, and Download all
  populate from REAL agent work."
- **Attack:** read what `src/server.py::_run_migration` actually pushes on the live path, panel
  by panel, and find the ones that stay empty when the agent doesn't print perfect markers.
- **Evidence (committed `src/server.py`, lines 116–195, verified against disk):**
  - **`diff` (COBOL↔Python viewer): NEVER EMITTED.** No `diff` event is pushed anywhere in
    `_run_migration`. `event_transform.diff_event()` exists (event_transform.py:147) but is not
    called. The renderer has a full `on_diff` panel (renderer.js:218) and STREAM_CONTRACT §4
    documents it — so on a live run this panel sits EMPTY. This is plan root-cause #4, unfixed.
  - **`pytest` per-case: marker-only, EMPTY fallback.** server.py:166–174 builds the structured
    pytest ONLY from the agent's `LAZARUS_ORACLE_JSON` marker. If the agent omits it (the plan
    itself says the agent "doesn't reliably print" markers), the fallback pushes
    `{"result": ..., "cases": []}` — an EMPTY test terminal with no RED→GREEN. The local
    differential-oracle fallback the plan mandates ("run differential_oracle locally against
    golden_io.json to produce the structured pytest + diff deterministically") is NOT wired.
    `oracle_harness_pytest_event()` exists for exactly this but is uncalled.
  - **`business_rule`: marker-only.** server.py:148–150 emits rules only from `LAZARUS_RULE`
    markers. `business_rules_fallback()` (event_transform.py:209, ≥3 real rules) is NOT called,
    so the archaeology panel is empty if the agent omits markers.
  - **`phase` progression: not progressive.** Only `ingest` (server.py:136) + a per-iteration
    `test` phase (server.py:130) fire. `recover / translate / oracle / forge / done` never
    advance off the stream. `phase_for_text()` exists (event_transform.py:135) but is unwired.
    This is plan root-causes #1 and #3, unfixed.
  - **What IS wired and real:** the `oracle` banner (from golden_io.json), `forge`/`reload`
    (when the agent prints a SKILL.md path), the Files-API `download`, and `done`.
- **Verdict: NEEDS FIX — STOP-THE-LINE.** The honest, deterministic building blocks integration-eng
  wrote in `event_transform.py` (diff_event, oracle_harness_pytest_event, phase_for_text,
  business_rules_fallback) are correct and truthful — but `src/server.py` does not call them.
  As committed, a LIVE run with an imperfect-marker agent shows: empty diff panel, empty (or
  prose-only) test terminal, possibly empty rules, and a phase rail that jumps to "test". That
  is the mock looking complete while the live run is not. Wiring required in `_run_migration`:
  (1) fetch payroll.py (already have `_download_migrated`), emit `diff_event(cobol, payroll.py)`;
  (2) run `differential_oracle.prove_equivalence(payroll.py, golden_io.json)` and emit
  `oracle_harness_pytest_event(records)` as the deterministic pytest (markers stay the fast path);
  (3) `business_rules_fallback()` when no markers; (4) drive `phase_for_text()` from the streamed
  step text for progressive phases. Escalated to team-lead / integration-eng (task #1).

## L3 — Is the local-oracle pytest presented HONESTLY (not as the agent's own test run)?  — CONFIRMED (design), UNWIRED

- **Claim (my brief #3):** integration-eng will derive the structured pytest by running the
  differential oracle LOCALLY (agent's python vs golden_io.json real-cobc bytes). Is that
  truthful (the orchestrator IS the oracle harness) or misleadingly framed as the agent's own
  test run?
- **Attack:** if the UI labels orchestrator-run results as "the agent ran pytest and got
  RED→GREEN," that's a fabricated provenance a judge can puncture.
- **Evidence:** `event_transform.oracle_harness_pytest_event()` (event_transform.py:160) is
  written for exactly this and is HONEST:
  - case names → `oracle_equivalence[...]` (not `test_...`, so it doesn't masquerade as the
    agent's pytest);
  - sets `ev["source"] = "differential_oracle"`;
  - summary appends "(differential oracle: agent python vs real-cobc golden bytes)".
  - Its docstring states the intent verbatim: "these records come from src/differential_oracle.py
    running the agent's payroll.py against the real-cobc golden bytes, NOT from the agent's own
    pytest stdout. Truthful labeling keeps the demo honest."
- **Verdict: CONFIRMED honest BY DESIGN — but UNWIRED (see L1) and the UI must SHOW the
  provenance.** Two conditions for sign-off: (a) server.py actually calls this function (not
  `to_pytest_event`, which uses generic `test_equivalence[...]` names with no source label);
  (b) the renderer surfaces `source`/the honest summary so a judge SEES it's the oracle harness,
  not a claimed agent self-test. Today renderer.js `on_pytest` ignores `ev.source` — it would
  render `oracle_equivalence[...]` rows (good) but drop the "differential oracle" provenance
  unless it's in `summary` (it is — the summary carries it). Acceptable if server.py uses the
  harness event; flag to frontend-eng to keep the summary visible. No overclaim found in code;
  the risk is purely that the wrong (unlabeled) event ships.

## L5 — golden_io.json (local truth) vs the agent's own cobc — conflated? Is "differential oracle = real COBOL" still honest?  — CONFIRMED honest

- **Claim:** golden_io.json is LOCAL pre-captured ground truth; the agent independently installs
  cobc + generates its own. My brief asks whether these are conflated and whether the end-to-end
  "real COBOL" claim survives.
- **Evidence:**
  - golden_io.json self-documents its role unambiguously: "PRIMARY ORACLE GROUND TRUTH … does
    NOT require a live compiler … When cobc OR a mounted Linux binary IS available,
    verify_golden_against_binary() re-confirms these bytes are fresh — but the equivalence diff
    never depends on it." capture_status: "REAL — compiled + run with live cobc, not computed."
  - The agent prompt (agent.py:137–146) keeps them distinct: PRIMARY = golden_io.json as ground
    truth; LIVE REFRESH = micromamba/conda-forge gnucobol to "confirm golden_io.json is still
    fresh — but the equivalence check stays byte-for-byte against the golden bytes."
  - v1 C5 independently verified all 10 golden cases byte-for-byte against a real GnuCOBOL 3.2.0
    compile, and payroll.py 10/10 byte-equivalent. (CHALLENGES.md C5.)
- **Verdict: CONFIRMED honest.** No conflation: golden is the deterministic floor (real cobc
  bytes captured ahead of time); a live cobc run is opportunistic freshness only. The
  "differential oracle = real COBOL output" claim is true either way — the bytes ARE real
  compiler output, captured earlier or refreshed live. This is the project's strongest honesty
  position; protect it. (One residual: if the live run claims "the agent just compiled COBOL in
  the sandbox," that needs qa live evidence — L2-adjacent — since the demo's deterministic path
  is golden, not a live compile.)

---

## PENDING — require qa-verifier LIVE evidence (no GEMINI_API_KEY on the devils-advocate box)

- **L2 (download is the agent's real sandbox output):** `_download_migrated` →
  `_fetch_env_tarball` (Files-API `environment-<id>:download`) → `_extract_migrated_from_tar`
  looks for `workspace/payroll.py`. Real path, never run on a key. Need: qa confirms
  GET /api/download/{run_id} returns a runnable payroll.py pulled from the sandbox, and that the
  agent actually wrote it to `/workspace/payroll.py` (the prompt says "write payroll.py" but does
  NOT pin `/workspace/` — possible path mismatch with the extractor's `workspace/` filter).
- **L4 (phase realness):** confirm live phases advance through recover/translate/oracle/forge,
  not just ingest+test — contingent on the L1 wiring landing.
- **L6 (2-min legibility + weakest moment):** assessed once a real run exists.

> I cannot run the live path (no key). All PENDING items need qa-verifier's captured live stream.

---

## L7 — The missing `diff` event makes the headline panel VANISH (not just empty)  — NEEDS FIX

- **Claim:** the UI degrades gracefully — empty panels just don't show.
- **Attack:** trace what the progressive-reveal renderer does when an event never arrives.
- **Evidence:** `renderer.js` reveals a flow card only when its handler fires `_revealCard`:
  `on_diff` → `_revealCard('translate')` (renderer.js:269); `on_business_rule` → `'recover'`
  (263); `on_pytest`/`on_oracle` → `'test'` (303/350); `on_forge` → `'forge'` (363). Because
  server.py never emits `diff`, `on_diff` never fires, so the **`card-translate` (COBOL→Python
  side-by-side) never reveals at all** — the single most compelling "migration" beat is ABSENT
  from a live run, while it's front-and-center in the mock. Same mechanism shrinks the rules and
  proof cards when markers are absent.
- **Verdict: NEEDS FIX.** This is the concrete demo-coherence cost of L1: the live demo is not
  just "a bit empty," it's MISSING its headline translation panel. The reveal logic itself is
  honest (no faked empty cards) — the fix is to actually emit `diff` (L1).

## L8 — Live download/diff/oracle all depend on an UNPINNED payroll.py path  — NEEDS FIX (cheap)

- **Claim:** the downloaded payroll.py is the agent's real sandbox output (Files API).
- **Attack:** the extractor (`_extract_migrated_from_tar`, server.py:91–93) looks for
  `workspace/payroll.py` (or `.../workspace/.../payroll.py`). But the agent prompt (agent.py:136)
  only says "Translate to Python (write payroll.py)" — it does NOT pin `/workspace/payroll.py`,
  and `.agents/AGENTS.md` doesn't either. The only `/workspace` reference in the prompt is the
  conda env path. If the agent writes payroll.py to its CWD (which may not be `/workspace`) or a
  repo subdir, the extractor's `"workspace" in path` requirement fails → `_download_migrated`
  returns None → Download stays un-armed AND (once L1 lands) the local oracle + diff have no
  payroll.py to run against → those panels stay empty for the WRONG reason.
- **Verdict: NEEDS FIX (cheap, high-leverage).** Pin the path in the prompt + AGENTS.md: "write
  the migration to `/workspace/payroll.py`." Then download, diff, and the local oracle all find
  the real artifact deterministically. qa to confirm live the agent honors it (NEEDS-VERIFY).

---

## L9 — LIVE Files-API tarball TIMES OUT → diff + download blank (qa-found)  — MITIGATED + VERIFIED, pending live stream

- **EVIDENCE (qa-verifier, TWO live runs on the real key, runs 5561f1cf / 1ccbf78f, pre-fix):**
  `_fetch_env_tarball()` TIMED OUT — the whole-environment tarball is too large/slow (30s hard
  timeout failed; even 180s+ never returned). At that commit, on a LIVE demo: `diff` + `download`
  BOTH failed to fire → COBOL↔Python panel EMPTY, Download never armed, GET /api/download → 404.
  Root cause is fundamental: the Files API only documents the WHOLE-ENV tarball
  (`environment-{id}:download`); NO per-file helper (findings-agents.md), and the agent installs a
  conda gnucobol prefix into /workspace, bloating the tarball. qa's read is correct: HONEST failure
  (empty panels), NOT fake success — the module IS correct in the sandbox, just not retrievable.
- **MITIGATION (integration-eng, COMMITTED 49cc1d9 + tested):** tarball-None now falls back to
  `event_transform.python_module_from_output(output)` — the largest python-ish fenced ```python
  block the agent echoes in its own output — tagged `source="model_output"` (honest provenance:
  the agent's REAL code, from its output stream, not the disk image). Files-API tarball stays
  PRIMARY (`source="files_api"`). diff + oracle pytest + download all repopulate. Tests:
  `test_tarball_timeout_falls_back_to_model_output`, `test_tarball_and_output_both_empty_keeps_panels_honest`.
- **INDEPENDENTLY VERIFIED (devils-advocate + qa, deterministic, no key):** qa confirmed the LIVE
  agent echoes a complete 38-line module (Decimal+ROUND_HALF_UP+__main__) and the scrape recovers
  it + passes the oracle 10/10. I REPRODUCED it with the exact server functions: sample module in a
  fenced ```python block amid prose → `python_module_from_output` recovers 55/55 lines byte-identical
  → `prove_equivalence` 10/10 byte-for-byte vs golden → pytest green, source=differential_oracle.
  Negative control: a 3-line truncated block is correctly NOT scraped (≥5-line guard).
- **Verdict: MITIGATED + mechanism VERIFIED — pending only qa's END-TO-END live stream.** The
  scrape works on the agent's REAL echoed output (not just the synthetic test). Remaining: qa's
  in-flight full live stream confirming diff fires + download returns the module + source label +
  wall-clock on the real key. Belt-and-suspenders option if ever flaky: an explicit
  `LAZARUS_MODULE:` marker so recovery doesn't depend on incidental echo; and/or install gnucobol
  outside /workspace to shrink the tarball.

---

## L10 — LIVE latency (8–12+ min) vs the "2-minute" framing  — RESOLVED: STRICTLY LIVE (user's call)

> **DECISION (user, via team-lead):** STRICTLY LIVE in-slot, no mock lead. The user accepts the
> multi-minute reality (consistent with their original "no mock" stance). The value is reframed
> from speed to authenticity: watch a real agent do real work, ending in a byte-for-byte proof.
> The replay-led draft is SUPERSEDED; the honest live narrative is in
> `docs/DEMO_NARRATIVE_live-DRAFT.md`. This is a LEGITIMATE, honest choice — arguably MORE honest
> than replay-led (zero risk of a replay being mistaken for live). The new risk it creates is L11
> (the UI must visibly progress, not look frozen). Mock stays `?mock=1` break-glass ONLY.

- **Claim (v2 plan, throughout):** a "2-minute LIVE demo" on the real key; "Live default;
  `?mock=1` break-glass only" (web/index.html `mode-live`, app.js, mock note).
- **EVIDENCE (qa-verifier, 3 live runs on the real key):** the live end-to-end is NOT a 2-minute
  experience. Measured: run #1 events burst ~444s / done ~501s (~8.3 min); run #3 still on
  iteration 1 at 12+ min. Time-to-first-panel is SEVERAL MINUTES of an empty/working screen (the
  agent runs one long silent interaction, then the panels burst at the end). The scripted
  `mock-run.json` timeline is 22.2s total — it fits a 2-min slot; a live run does not.
- **Verdict: NEEDS FIX — but it's DEMO STRATEGY, not code, and the honest fix already exists.**
  For a timed 2-min slot the realistic vehicle is the `?mock=1` cached replay. This is HONEST
  *iff* it's narrated as what it is — the mock self-documents ("Break-glass fallback... mirrors a
  real LAZARUS migration"), is derived from REAL GnuCOBOL golden bytes (golden_io.json), and the
  UI labels it "BREAK-GLASS · cached run" / clock "cached". So:
  - DO: lead the timed demo with the cached replay, narrated as "a replay of a real run," and show
    the live system as PROOF it's real (e.g. a pre-warmed live run finishing in the background, or
    the live download/verdict shown as evidence). qa already confirmed a real live run ends
    EQUIVALENT with the agent's real module — that's the proof.
  - DON'T: present the cached replay AS a live run, or promise "watch it run live in 2 minutes" —
    the latency makes that false and a judge timing it would catch the empty screen.
  - INVERT the framing in the demo narrative: "live by default" is the right PRODUCT default but
    the WRONG demo-slot default. The README/DEMO_SCRIPT should say the 2-min demo uses the cached
    replay of a real run, with the live path runnable on request (it just takes ~8–12 min).
- **Owners:** team-lead / doc-keeper (demo narrative + DEMO_SCRIPT framing). [Resolved — the
  decision is strictly-live; doc-keeper applies `DEMO_NARRATIVE_live-DRAFT.md` to DEMO_SCRIPT.]

## L11 — Does the live UI visibly PROGRESS during the long run, or look FROZEN?  — OPEN (#1 strictly-live risk)

- **Why this is now decisive:** with the strictly-live decision (L10), the demo IS the multi-minute
  live run. The "watch a real agent work" narrative HOLDS ONLY IF the screen visibly moves during
  the run. qa observed the agent does "one long silent interaction, then bursts at the end."
- **Attack:** if that means the WORKING banner sits on one line for minutes with no movement, a
  judge sees a HUNG app, not a working agent — the whole strictly-live value prop collapses into
  "staring at a frozen screen."
- **Code reality:** server.py's `emit_step` pushes a `step` event per streamed chunk and updates
  `_setWorking({action})`; the renderer advances the banner + trace + phase rail off that. So the
  UI moves IFF the AGENT streams intermediate `step.delta` text during the run. If the agent goes
  dark until the end, the UI is stuck regardless of the wiring.
- **CONFIRMED FROZEN (qa's full live stream + my raw-stream analysis) → FIX LANDING (task #6).**
  I analyzed `/tmp/sse_full.jsonl` (153 events, 19-min run): the 134 `step` events are all chunks
  of ONE end-block message ("I have completed the recovery, translation, verification, and skill
  forging…") — the agent streams NOTHING incrementally, then bursts at the end. Phases emitted:
  only `ingest, ingest, forge, forge, forge, reload, done` (no recover/translate/oracle/test). So
  the screen WAS effectively frozen for ~19 min, then everything appeared at once. L11 = REAL.
  - **FIX (frontend-eng, working tree, task #6):** the WORKING banner now has an always-advancing
    elapsed timer (`_startHeartbeat`/`_tickHeartbeat`, 1s setInterval, pure clock — renderer.js:136)
    + a reassurance line after 6s of silence ("Real migrations take a few minutes — the agent is
    working in a live sandbox"). HONEST: it doesn't fake phase progress; it proves the app is alive
    with a real clock. The code comment cites this exact root cause.
- **Verdict: RESOLVED (frozen-screen bar cleared) — with an honest caveat.** The heartbeat clears
  the "looks hung" risk (the hard requirement). CAVEAT: it makes the screen ALIVE, not the run
  watchable — the agent genuinely emits no incremental progress, so the experience is ~minutes of
  [spinner + ticking timer + reassurance + static "Iteration 1/4"] then an end-burst. That's honest
  (not frozen, not faked), but it's a long low-information stretch; the "breadcrumbs" half of task #6
  + the narration talk-track must carry it. Acceptable for sign-off IF the heartbeat lands and the
  demo narrative sets the expectation. (A deeper fix — getting the agent to stream incremental
  milestones — is out of scope for the slot; the prompt could ask it to print progress markers, but
  that's not guaranteed.)

## L12 — GET /api/download/{run_id} returns 404 after the stream ends  — CONTAINED (inline path works)

- **EVIDENCE (qa):** server.py:470 pops `_RUNS[run_id]` when the SSE stream completes (one-subscriber
  cleanup, pre-existing design). So after the run, GET /api/download/{run_id} → 404. qa confirmed
  the live UI does NOT hit that endpoint — `live.js` prefers the INLINE `content` carried on the
  `download` event (verified: 2078B inline, byte-identical to the diff's right side), so the Download
  button arms from the event, not the endpoint.
- **Verdict: CONTAINED, not blocking.** The demo's download works (inline). But the endpoint being
  dead post-stream is a latent fragility: any path that relies on GET /api/download (e.g. a judge
  hitting the URL, or contract-B clients) gets 404. Cheap fix if desired: keep `run["download"]` in
  a short-TTL cache after `_RUNS.pop`, or don't pop until download is fetched. Flagging for the
  record; not a sign-off blocker since the live UI uses inline content.

---

## Honesty WINS confirmed this pass (lean into these with the judge)

- **C13 (COMP-3) — LANDED CORRECTLY in the live surface.** The #1 v1 honesty fix is done:
  `web/mock/mock-run.json:49` now states verbatim "(COMP-3 storage is irrelevant — DISPLAY
  de-edits identically regardless.)" and attributes the RED to banker's-vs-half-up rounding.
  The forge is named `numeric-display-rounding`. server.py:160 + agent.py:154 carry the same
  honest framing. Remaining COMP-3 mentions are legitimate (the COBOL source genuinely declares
  COMP-3 fields; the syntax highlighter lists it as a keyword) — not the false "COMP-3 is what
  fails" claim. Verified by grep across web/ + src/ + docs.
- **C16 (hot-reload) — GONE from the live surface.** STREAM_CONTRACT.md:108 now says "(no
  mid-run hot-reload — that's unverified)"; README:28 explicitly disclaims "mid-run hot-reload
  or cross-run accumulation." No "Hot-reloading" label remains in the UI path.
- **Test suite is HONESTLY scoped.** All 67 tests pass. test_server.py is explicit: "all
  runnable WITHOUT a key … The live Gemini path itself is validated by scripts/smoke_test.py."
  Crucially, the tests do NOT falsely assert the diff/local-oracle fallback works — they only
  exercise the marker path that server.py actually implements. So a green test run does NOT
  imply a complete live path (the gap in L1 is real, not hidden by a passing test).
- **L3/L5 oracle honesty (design) is sound** — the orchestrator-as-harness labeling and the
  golden-vs-live distinction are both truthful; the only risk is shipping the unlabeled event
  (L1 wiring must use `oracle_harness_pytest_event`, not `to_pytest_event`).

---

## INDEPENDENT DRIVE (devils-advocate, no API key) — the wired path, verified by my own hand

I drove the wired server.py end-to-end myself via TestClient, stubbing ONLY the network
boundary (genai client + agent.migrate + Files-API fetch); diff/oracle/phases/rules/download
all ran the REAL server code. Two runs:

1. **No-marker safety net** (agent prints no LAZARUS_* markers, ships the correct sample
   payroll.py): event stream =
   `phase×ingest, step…, recover, translate, oracle, test, business_rule×3, oracle, diff, pytest,
   download, done`. Phases advance ingest→recover→translate→oracle→test→done. `diff` present
   with the agent's real module on the right. `pytest`: result=green, source="differential_oracle",
   10 cases, summary "10 passed, 0 failed (differential oracle: agent python vs real-cobc golden
   bytes)". download = the agent module. verdict EQUIVALENT. EVERY panel populated from real
   output with ZERO markers — the mock-only-completeness risk is gone.

2. **Falsifiability (the one that matters)** — agent OVER-claims "All equivalence tests pass"
   but ships a banker's-rounding module: oracle result=**RED** (source=differential_oracle),
   failing cases `oracle_equivalence[1.00]` (0000000.77 vs 0000000.78) and
   `oracle_equivalence[5.00]` (0000003.87 vs 0000003.88), verdict **INCOMPLETE**. The verdict
   follows the ORACLE, not the agent's claim. **The agent cannot fake equivalence past the
   oracle.** This is the project's strongest honesty position, verified independently.

3. **Crash path now HONEST (my nit #1 closed) — verified + COMMITTED (cdafd8c).** Agent
   over-claims "All equivalence tests pass" but ships a module that RAISES on run:
   `_run_oracle_pytest` now returns an EXPLICIT RED ("differential oracle could not run the
   agent's payroll.py: …", source=differential_oracle) instead of None→coarse-prose-verdict,
   so verdict=**INCOMPLETE**. None is now reserved ONLY for an unreadable golden capture. I
   independently drove it (crash module + agent claiming pass → RED + INCOMPLETE). Test:
   `test_crashing_module_goes_red_not_falsely_green`.

4. **Provenance symmetry (my nit #2 closed) — COMMITTED (cdafd8c).** `to_pytest_event` now
   tags `source="agent_pytest"` (names `test_equivalence[...]`); `oracle_harness_pytest_event`
   overrides to `source="differential_oracle"` (names `oracle_equivalence[...]`). UI can
   distinguish the two on BOTH paths. Tests: `test_agent_marker_pytest_is_labeled_agent_source`,
   `test_to_pytest_event_labels_agent_source`.

**Final backend state:** HEAD f6e568f (L8 AGENTS.md pin) atop cdafd8c (both nits). Python
working tree clean; 80/80 tests pass. All of L1-L8 + both nits resolved and COMMITTED. Only
remaining gate: qa's live evidence (L2/L6).

## Bottom line for sign-off (devils-advocate, task #4)

**GATE 1 — WIRING — CLEARED.** server.py now emits diff + local-oracle pytest + fallback rules
+ progressive phases; the prompt pins /workspace/payroll.py. 77/77 tests pass and I independently
drove BOTH the happy path (every panel populates, no markers needed) and the falsifiability path
(over-claiming agent + wrong module → oracle RED → verdict INCOMPLETE). Code is complete AND honest.

**GATE 2 — LIVE EVIDENCE — STILL OPEN (the only thing between here and sign-off).** qa-verifier
must run on the real key (post-wiring) and show: the full ordered stream with a real `diff`,
populated `pytest` cases, and a real downloaded `/workspace/payroll.py` pulled via the Files API,
within the 2-min budget. I have NO key; my drive stubs the network boundary, so it proves the
ORCHESTRATION is correct but NOT that the live Gemini agent honors the contract. Residual
live-only risks: L2 (real download), L8 (agent honors the pinned path), L6 (2-min legibility +
weakest moment).

Honesty posture is STRONG: C13/C16 landed; oracle framing truthful and provenance-labeled; the
verdict provably follows the oracle, not the agent's claim; tests honestly scoped.

---

## FINAL SIGN-OFF (devils-advocate, task #4) — SPLIT: CODE/DoD signed; DEMO open

Split per team-lead, and it matches my own verification cleanly:

**✅ CODE / DEFINITION-OF-DONE — SIGNED OFF (2026-05-23).** A completed real-key live run
drives EVERY panel from REAL agent work: business rules, oracle banner, COBOL↔Python diff
(right-side == download, byte-identical), structured pytest (GREEN, real per-case cases),
forge+reload, download of the agent's REAL runnable module (Decimal+ROUND_HALF_UP; qa ran it →
exact COBOL bytes), verdict EQUIVALENT.
**RUN-ID CORRECTION (per qa):** the DECISIVE fully-populated run to cite is **f9e71470** (env
2b01d46d, on **ea6fe12** — post the tarball-independent fix), confirmed by qa + my independent read
of /tmp/sse_full4.jsonl. An EARLIER run **2f307f10** (pre-ea6fe12) had diff/download EMPTY due to
the tarball gate — do NOT cite it as the complete run. My L11 frozen-screen analysis used a
pre-fix run's raw stream (still valid for that finding); the COMPLETENESS sign-off rests on
f9e71470. Honesty is verified
from every angle: the verdict tracks the differential oracle, NOT the agent's self-report (wrong
module → RED; crash → explicit RED; both tested + independently driven by me); provenance is
truthfully labeled (agent_pytest / differential_oracle / model_output / files_api); no panel shows
fabricated data; C13/C16 honesty fixes hold. The DoD ("a single live run drives the whole UI …
ends EQUIVALENT with a downloadable, runnable payroll.py") is MET. **Nothing material is missing
or misleading on the code/data path.**

**⏳ DEMO READINESS — SIGN-OFF OPEN, pending two in-flight items:**
1. **L11 heartbeat (task #6) — FULLY VERIFIED end-to-end by me (2 servers); just needs COMMIT.**
   Test 1 (:8141, isolated): drove the committed heartbeat logic against the live DOM — timer
   advances once/sec ("0:09" at 9s) and the reassurance line ("Real migrations take a few minutes
   — the agent is working in a live sandbox") reveals after the 6s quiet threshold. Test 2 (:8777,
   team-lead's server, FULL run lifecycle): clicked "use the sample", sampled every 500ms — timer
   ticked the whole run (0:00→0:01→…→0:21, every second present) while WORKING showed, and on `done`
   the WORKING banner + timer HID (workingVisible→false) and the verdict badge showed EQUIVALENT.
   So both (a) ticks at 1s cadence during WORKING and (b) stops on done are CONFIRMED. Clears the
   L11 "looks frozen / hung app" bar honestly (real clock, no faked phase progress). My answer to
   "is the heartbeat sufficient for L11?": YES, verified. Breadcrumbs + phase-rail advancement are
   Phase-2 (engagement), not required for the frozen bar. Only remaining gate: COMMIT the fix.
2. **DEMO_SCRIPT honest strictly-live rewrite (task #7):** must set the multi-minute expectation
   up front, show elapsed time, never fake speed (content in DEMO_NARRATIVE_live-DRAFT.md).

**Non-blocking, flagged → Phase 2:** L12 (GET /api/download 404s after stream; live UI uses inline
content, so contained) + the breadcrumbs/phase-rail enhancement. Neither is a Phase-1 blocker.

**PHASE-1 SCOPE (per team-lead):** the heartbeat satisfies L11; breadcrumbs + L12 are Phase 2
(separate branch, own re-verify). I will convert the DEMO sign-off to ✅ once #6 is COMMITTED
(heartbeat now visually verified) and #7 lands. No unresolved honesty or completeness gaps remain.

---

## L13 — DEMO_SCRIPT claims a LIVE GnuCOBOL compile, but the verified run's ground truth was the PRE-CAPTURED golden bytes  — NEEDS FIX (script honesty; blocks my full DEMO sign-off)

- **Claim (docs/DEMO_SCRIPT.md, ce3de81):** Prove beat — "It compiles & runs the **original COBOL
  with real GnuCOBOL**, captures its real output, generates equivalence tests"; Q&A — "We compile
  and run the original COBOL with real GnuCOBOL in the sandbox and assert byte-for-byte equivalence
  against its output." Presented as happening LIVE on stage.
- **EVIDENCE (my read of qa's shipping run /tmp/sse_full4.jsonl):** on the verified live run the
  UI's ground truth did NOT come from a live in-sandbox compile:
  - the `oracle` event's `compiler`/`note` is the **golden_io.json header** ("Canonical outputs
    captured from the original COBOL binary (ground truth)") — i.e. the PRE-CAPTURED golden bytes,
    not a live compile;
  - the `pytest` is `source="agent_pytest"` (the agent's own marker, cross-checked vs golden by
    qa) — NOT a live `differential_oracle` harness run;
  - the agent's step text shows it only INVESTIGATED a compiler ("I will check if a COBOL compiler
    `cobc` is already installed… check if micromamba or conda are pre-installed") and searched for
    `golden_io.json`; no evidence a live `cobc` compile SUCCEEDED and produced the on-screen oracle.
- **Why it matters:** for a STRICTLY-LIVE demo where the judge watches the actual run, narrating
  "it compiles & runs the original COBOL with real GnuCOBOL" while the on-screen oracle banner is
  actually the pre-captured golden header is a judge-catchable overclaim (same class as C4/C13). A
  COBOL-literate DeepMind judge asking "did it compile that live, or is that cached?" exposes it.
- **It's STILL honest if reworded:** the golden bytes ARE real GnuCOBOL output (captured ahead of
  time = the falsifiable floor, per C4/C5); a live compile, if it happens, is an opportunistic
  refresh. The fix is to match the script to that reality, NOT to claim a guaranteed live compile.
- **Verdict: NEEDS FIX (script wording) — blocks my FULL demo sign-off.** Recommended rewording:
  Prove beat → "It proves equivalence against the **original COBOL's real GnuCOBOL output** (the
  ground-truth bytes), diffing the Python against them byte-for-byte" — and, if the agent does
  install/compile cobc live this run, narrate THAT as the refresh; otherwise don't assert it. Q&A
  "How do you know it's correct?" → "ground truth is the real COBOL's output — captured from real
  GnuCOBOL; the agent also tries to recompile it live in the sandbox to refresh it." Keep it
  truthful to whichever path actually fires on stage. Owner: team-lead/doc-keeper, BEFORE the push.

---

## L13 — RESOLVED (687ca26). FULL DEMO SIGN-OFF GRANTED.

Verified the 687ca26 diff: the Prove beat now says "holds the Python to the original COBOL's real
GnuCOBOL output — ground-truth bytes captured ahead of time" + "(if the agent recompiles cobc live
this run, narrate that as an opportunistic refresh — don't assert it if it doesn't fire)"; both Q&A
answers reworded to "ground truth = the original COBOL's real output captured from real GnuCOBOL;
verdict tracks that oracle, not our tests; live recompile is an opportunistic refresh, not
guaranteed"; de-risking checklist states "ground truth = golden_io.json; the demo does not depend
on a live compile." No remaining claim of a guaranteed live compile producing the on-screen proof.
Honest and accurate to qa's verified run. L13 CLEARED.

## ✅✅ FINAL SIGN-OFF (devils-advocate, task #4) — BOTH parts GRANTED

- **CODE / DoD ✅** — every panel populates from REAL agent work on a completed real-key live run;
  verdict tracks the differential oracle, not the agent (wrong/crash → RED, tested + driven by me);
  diff.right == download (the agent's real runnable module); honest provenance labels; no fabricated
  data. DoD met.
- **DEMO ✅** — strictly-live narrative is honest: multi-minute expectation set up front; measured
  ~8–9 min stated (not "2 min"); elapsed-timer heartbeat (visually verified ticking + stopping on
  done) keeps the screen provably alive; ground-truth/oracle framing accurate (L13 fixed); guardrails
  forbid faked speed; mock is break-glass only, labeled. No overclaims remain.

Honesty posture is STRONG and was made stronger by this review (C13/C16 held; oracle falsifiability
enforced + tested; L13 overclaim caught + fixed pre-push). Phase-2 items (breadcrumbs/phase-rail
dedup, L12 download-endpoint TTL) are correctly deferred and are NOT blockers. team-lead is clear to
push main (HEAD 687ca26, 88/88 green).

---

## L9 — STRENGTHENED post-sign-off (ea6fe12 LAZARUS_MODULE marker) — verified, no reopen

After my Phase-1 sign-off, qa noted (and I verified in code) that ea6fe12 "Make module recovery
tarball-independent" added the explicit `LAZARUS_MODULE:` belt-and-suspenders I'd recommended:
- agent.py:168 instructs the agent to print `LAZARUS_MODULE:` + a single fenced ```python block;
- event_transform.py: `_MODULE_MARKER = "LAZARUS_MODULE:"`; `python_module_from_output` now resolves
  DETERMINISTICALLY (the marker) first, then falls back to the largest fenced block.
So module recovery for diff/download no longer depends on incidental echo. qa empirically confirmed
(live run f9e71470, /tmp/sse_full4.jsonl, which I independently read) the live agent echoes a
complete runnable module that passes the oracle 10/10. L9 is solid on BOTH the deterministic-marker
and scrape-fallback paths. No reopen — this only strengthens the resolution I signed off. L12
(download-404 post-stream) → Phase-2 fix 8f1e7ea (_COMPLETED_DOWNLOADS LRU), qa to confirm on the
Phase-2 run; correctly deferred, not a Phase-1 blocker. Sign-off stands.

---

## RUN-ID CRUX — SETTLED two independent ways (qa + my own git/data check). Sign-off maximally grounded.

The one thing I most wanted certainty on — was the completeness sign-off based on a COMPLETED,
POST-fix, real-key run (not the mechanism alone, not a pre-fix run)? — is now settled definitively.
I verified BOTH of qa's proofs myself:
1. LINEAGE: `git merge-base --is-ancestor ea6fe12 6b0b89d` = YES → 6b0b89d (which f9e71470 ran on)
   contains the model_output fix → f9e71470 is POST-fix.
2. DATA: f9e71470's stream (/tmp/sse_full4.jsonl) contains `"source": "model_output"` — a label
   only the post-fix `python_module_from_output` path can emit. The run data itself proves the fix
   fired on that run.
Earlier pre-fix run 1ccbf78f had diff/download EMPTY (that empty result IS the evidence it predated
the fix). So: f9e71470 = a completed, provably-post-fix, real-key run where diff+download populated
with the agent's real module (oracle 10/10, EQUIVALENT, ~514s). My sign-off rests on real live
evidence, confirmed two ways. Nothing left to verify. DEVIL'S-ADVOCATE REVIEW CLOSED.

---

## L11 — CONFIRMED ALIVE in-browser (qa direct observation) + honest Phase-2 nuance recorded

qa drove a live run in Chrome and observed directly (not inferred): the heartbeat elapsed timer
ticked 0:04 → 0:45 → 0:56 across screenshots; the reassurance line rendered during the silent
stretch; the activity panel populated with real COBOL source; screen visibly alive from ~4s. Backend
cadence on the in-flight run: new `✓ ok` breadcrumb lines streamed at 11/13/21/27/32/39/44/53/55/57/
65/89s — the trace accrues, not stuck on one line. This is the in-browser confirmation behind my
heartbeat sign-off (I'd verified the timer mechanism on :8141/:8777; qa confirms it in a real run).

HONEST NUANCE (qa-disclosed, recorded so it's not a surprise to a judge):
- There is one ~30–60s FLAT stretch on a heavy compute step with no new trace line — but the
  heartbeat keeps ticking + the reassurance line is up, so it reads "working," not "dead." This is
  exactly why the heartbeat (not breadcrumbs) was the load-bearing L11 fix.
- The phase rail does NOT richly march beat-by-beat live — most beats light near the END (it
  advances off end-block prose). The streamed breadcrumbs are only `✓ ok` with NO command text, so
  they can't drive `phase_for_text`. This is the precise Phase-2 limitation (consistent with my L10
  shipping-run note that the rail over-emits oracle / skips recover/translate/test). A Phase-2 fix
  would forward `code_execution_call` command text as breadcrumbs so the rail marches live.
NET: a strictly-live judge sees a live, ticking, accruing screen — not frozen. Phase-1 L11 bar
(never looks hung) is MET in-browser. Richer beat-by-beat progression is Phase-2, not a blocker.

---

## L11 — Phase-2 improvement (8f1e7ea breadcrumbs): trace now accrues incrementally (qa, in-flight)

Phase-2 (8f1e7ea) adds tool breadcrumbs; qa's in-flight run shows 12 `✓ ok` breadcrumbs streaming
at 11/13/21/27/32/39/44/53/55/57/65/89s — the activity log now gets NEW lines THROUGHOUT the run,
not just one end-block burst. So L11 mitigation is now TWO layers: (1) heartbeat timer + reassurance
(browser-confirmed), (2) incremental `✓ ok` breadcrumbs. Strictly better than the run I analyzed for
the original frozen finding.

HONEST LIMITATION (qa-disclosed, recorded): the breadcrumbs are ONLY `✓ ok`
(code_execution_result) — ZERO `$ <command>` (code_execution_call) breadcrumbs. So they show
"something happened" but not WHAT, and `✓ ok` matches no phase keyword so it can't drive the rail
(rail still advances off end-block prose). Net: "agent is doing things," not a rich
play-by-play of the cobc commands. The precise Phase-2 follow-on is to forward code_execution_call
command text as breadcrumbs. This is Phase-2 polish (task #8) — does NOT reopen the Phase-1
sign-off; it improves beyond it. My review remains CLOSED.

---

## L12 — FULLY CLOSED (8f1e7ea merged to main; verified two ways)

qa proved the fix through the REAL server: drove server.py via FastAPI TestClient reproducing the
exact post-stream condition I flagged (POST → drain SSE to completion → _RUNS popped → GET
/api/download/{run_id}) → HTTP 200, text/x-python, served the module. Stronger than a mocked unit —
the full request/stream/teardown/re-request cycle.

I independently confirmed the fix is on MAIN (not just the Phase-2 branch): server.py:72-84 add
`_COMPLETED_DOWNLOADS` (OrderedDict, 32-entry LRU cap, oldest evicted) populated with the module
content; line 519 the download endpoint falls back to `_COMPLETED_DOWNLOADS.get(run_id)` when the
run's _RUNS entry is gone post-stream. Memory-bounded + correct fallback. So GET /api/download now
returns 200 after the stream ends. L12 CLOSED. (Note: 8f1e7ea "Phase 2: live tool breadcrumbs +
post-run download retention" is merged to main — the download-retention half is live; the
breadcrumb/phase-rail polish continues per qa.)

## ALL FINDINGS RESOLVED — devil's-advocate review fully closed
L1–L13 + L12: every item is CONFIRMED, FIXED+verified, or honestly deferred-with-note. Nothing
open that affects honesty or completeness. Phase-1 shipped + signed off; the only continuing work
is Phase-2 phase-rail/breadcrumb polish (engagement, not correctness). Sign-off stands.

---

## L12 — confirmed THREE ways (final): real-key live curl 200. + phase-rail run-to-run inconsistency noted

qa's Phase-2 live run (6467773 on 8f1e7ea) completed; they curled its REAL run_id post-stream →
GET /api/download → HTTP 200, 3031B, real module. So L12 is now confirmed three independent ways:
(1) my read of the merged _COMPLETED_DOWNLOADS LRU on main, (2) qa's real-server TestClient cycle,
(3) qa's real-key live run_id curl. Fully closed. That run also reconfirmed completeness (all 10
types, diff.right == download 3031B, pytest green source=agent_pytest 19 cases, EQUIVALENT).

NEW DATA POINT (phase rail, sharpens the L10 precision note): this 2nd run's live rail was
ingest→recover→forge→reload→done — DIFFERENT from f9e71470's ingest→oracle→forge→reload→done, and
still skips translate/oracle/test. So the rail isn't merely over-emitting one phase; it's
INCONSISTENT run-to-run AND skips beats, because it's prose-driven (end-block) not activity-driven
(the `✓ ok` breadcrumbs carry no command text). This strengthens the case for the Phase-2 fix
(broaden + dedup phase_for_text patterns / forward code_execution_call command text). Phase-2 polish,
not a Phase-1 blocker; sign-off unaffected. Review remains fully closed.

---

## L14 — DEMO_SCRIPT "rail completes the full pipeline in order, verified on real runs" is FALSE on the captured runs (rail still skips translate/oracle/test) — NEEDS FIX

- **Claim (DEMO_SCRIPT, 5d99443, intro + de-risking):** "the phase rail completes the full pipeline
  **in order** (ingest→recover→translate→oracle→test→forge→reload→done — driven by the ordered
  structured events, **verified on real captured runs**)."
- **EVIDENCE — FALSE on every capture, including the POST-fix one.** I checked the actual streams:
  - f9e71470 (pre-87a5572): rail = ingest→oracle→forge→reload→done (skips recover/translate/test).
  - sse_full5.jsonl (captured 21:21, AFTER 87a5572's 21:19 commit): rail =
    ingest→recover→**forge**→reload→done — skips **translate, oracle, test**. The diff/oracle/pytest
    EVENTS all fired (panels populated, EQUIVALENT), but their phase-rail beats did NOT.
- **ROOT CAUSE (found in the trace):** `emit_phase` is forward-only (`if idx < progress.idx:
  return`). The `forge` phase is emitted EARLY from the agent's streamed prose (phase_for_text on the
  step text mentions the skill/forge right after recover) — index 5 — which advances progress.idx
  past translate(2)/oracle(3)/test(4). The later unconditional emit_phase("translate"/"oracle"/
  "test") calls are then SUPPRESSED by the forward-only guard. So 87a5572 fixed the structured
  emission but a SECOND prose-driven forge emission still eats the middle beats.
- **Verdict: NEEDS FIX (script overclaim + a real rail bug).** Two honest options:
  1. CODE FIX (preferred): stop emitting `forge`/any later beat from prose (phase_for_text) — drive
     the rail ONLY from the ordered structured events (the diff→translate, oracle, pytest→test,
     skill→forge emissions), so the forward-only guard sees them in order and the rail actually
     completes ingest→recover→translate→oracle→test→forge→reload→done. THEN the script claim becomes
     true and a fresh capture verifies it.
  2. SCRIPT FIX (if code won't change before ship): reword to the TRUTH — "the rail lights a partial,
     run-variable subset of beats (it currently skips some, e.g. translate/oracle/test, because a
     prose-emitted forge advances the forward-only rail past them); during-run liveness is the
     elapsed timer + ✓ ok breadcrumbs + trace, NOT the rail." Drop "completes the full pipeline in
     order, verified on real captured runs" — that's not what the captures show.
- Owner: integration-eng (the emit_phase/prose bug) + team-lead/doc-keeper (the script line). This
  is the one remaining honesty overclaim; flagging before it's read by a judge. NOT a Phase-1 code
  blocker (panels still populate; verdict honest) — it's a DEMO_SCRIPT accuracy blocker.

---

## L14 — RETRACTED (FALSE POSITIVE). My error: I analyzed a STALE-SERVER capture.

I was WRONG. integration-eng's rebuttal is correct and I verified it two ways myself:
1. The SHIPPED `emit_step` (origin/main 5d99443) has ZERO `phase_for_text` references — it only
   pushes the step; the prose-driven phase emission was removed in 87a5572 (the comment even says
   "DO NOT advance the phase rail from prose"). So the "two phase sources fighting" root cause I
   described does NOT exist on main.
2. I replayed the EXACT sse_full5 prose (the capture I cited as proof of the skip) through the
   SHIPPED code: RAIL = ingest → recover → translate → oracle → test → forge → reload → done,
   forge count = 1, translate/oracle/test ALL present. The full in-order pipeline.
ROOT CAUSE OF MY ERROR: sse_full5.jsonl was captured from a STALE uvicorn started before the
87a5572 fix (commit 21:19; capture mtime 21:21; a server started <21:19 still served OLD code).
Its 4×-forge signature is the OLD-code fingerprint — impossible under shipped code (single
emit_phase per beat). I treated the capture as authoritative WITHOUT confirming the server's commit
— the exact "verify the provenance before claiming" discipline I'd applied elsewhere, not applied
here. My fault.
CONCLUSION: the DEMO_SCRIPT "phase rail completes the full pipeline in order" claim is TRUE against
shipped code (verified by my own replay + integration-eng's replay + qa's TestClient on real
server.py). NO overclaim. NO code change needed (87a5572 already did exactly the fix I'd proposed).
L14 is WITHDRAWN. Lesson recorded: a captured stream is only evidence for the code the capturing
server was running — confirm the server's commit before drawing conclusions from a capture.

---

## L14 — FINAL DISPOSITION (both parts resolved on main; verified)

team-lead split L14 correctly and it's fully resolved on origin/main:
- WORDING (valid catch): "verified on real captured runs" WAS unsupported (no post-fix capture
  exists). FIXED in 72dcbce (in main's history; I confirmed `git merge-base --is-ancestor 72dcbce
  main` = YES). The DEMO_SCRIPT now says the rail completes in order "because the server emits these
  phases in fixed sequence from the ordered structured events, NEVER from prose … deterministic +
  unit-tested" and notes "earlier live captures predate this fix." Honest + accurate.
- RAIL-SKIP (my error): retracted. I re-confirmed on origin/main server.py: `phase_for_text` count
  = 0; the 8 emit_phase calls are hardcoded in fixed order ingest(333)→recover(353)→translate(379)
  →oracle(386)→test(394)→forge(417)→reload(423)→done(430); emit_step (312–319) pushes ONLY a step,
  no phase. Rail is clean by construction. My skip evidence (sse_full5) was probe5/6467773 output
  on 8f1e7ea — PRE the 87a5572 rail fix. Stale capture, my mistake (see
  [[captures-need-commit-provenance]]).
NET: no overclaim remains; the DEMO_SCRIPT rail line is honest; shipped code produces the in-order
rail (my replay + integration's replay + qa's TestClient all agree). Optional: a fresh
rehearsal capture from a confirmed-current server would document it, but the order is deterministic.
L14 CLOSED. ALL findings (L1–L14) now resolved/fixed/retracted — devil's-advocate review complete.

---

## L15 (task #11) — interest.cob golden is GENUINE — independently verified by devils-advocate

Co-owned with qa. I verified the second sample's golden is REAL (not computed/fabricated), zero-key,
by compiling it MYSELF with cobc 3.2.0 (non-circular — compares committed golden vs a fresh binary,
not vs the reference .py):
1. GOLDEN REAL: compiled src/sample/interest.cob with my own cobc 3.2.0; ran all 10 committed
   golden inputs through MY fresh binary → 10/10 byte-for-byte match (incl. truncation cases
   9999999.99→0374999.99, 13.33→0000000.49, 1.00→0000000.03, 50000.50→0001875.01).
2. REFERENCE EQUIVALENT: committed interest.py (Decimal + ROUND_DOWN) → 10/10 match golden.
3. FALSIFIABLE + DISTINCT IDIOM: a naive round() port FAILS exactly 4/10 — the 4 truncation cases
   above (round gives 375000.00/0.50/0.04/1875.02). A naive port CANNOT pass → the idiom is real
   and the OPPOSITE of payroll's ROUND-HALF-UP (payroll naive-round came out too LOW; here too HIGH).
CONCLUSION: no honesty gap. The golden is genuine real-cobc output; the second sample legitimately
demonstrates the differential oracle generalizes to a DIFFERENT idiom (not pattern-matching one
file). The README §2.4 claim ("two samples exercise opposite idioms, each proven against real
GnuCOBOL, each breaks a naive round() port") is INDEPENDENTLY VERIFIED, not just asserted. Matches
qa's verification exactly. L15/task#11 CONFIRMED.

## L15 — CORROBORATION: golden verified GENUINE by THREE independent paths
1. devils-advocate (me): compiled interest.cob with my own cobc 3.2.0 → committed golden == fresh
   binary 10/10 (non-circular); naive round() fails 4/10.
2. qa-verifier: build_samples.sh + independent naive-port falsifiability (4/10).
3. team-lead: ran build_samples.sh on a cobc-equipped box → committed golden == live cobc AND
   reference py == live cobc, 10/10 for BOTH payroll + interest. Shipped origin/main d265bbb, 99
   tests, CI green. Reproducible check: `bash src/sample/build_samples.sh` (read-only).
No fabricated golden. The second-sample honesty bar holds three ways. Task #11 fully CONFIRMED.
