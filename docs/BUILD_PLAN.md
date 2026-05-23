# LAZARUS — Build Plan (6.5 hrs, team of 4)

Hackathon clock: hacking starts **10:30 AM**, submissions due **5:00 PM** → ~6.5 hours. Lock the idea fast, build one killer path, reserve the last 2 hours for the demo.

## Roles (per the Ultimate Guide — front-end is non-negotiable)

| Person | Role | Owns |
|---|---|---|
| **A** | Front-end engineer | The live trace UI (steps + COBOL↔Python diff + pytest terminal + git-diff panel). *This UI is the demo; it gets the most polish.* |
| **B** | Agent/back-end engineer | Managed Agent setup, the write→run→prove loop, the FORGE self-authoring mechanism. |
| **C** | Differential-oracle + QA | GnuCOBOL harness, golden COBOL module + input battery, fallback cache, backup video. |
| **D** | BizDev / presenter | Narrative, the impact framing (NJ/$2.41T), judge Q&A, runs all rehearsals. |

## Timeline

| Time | Milestone | Who |
|---|---|---|
| 10:30–11:00 | Lock scope + codename. "Hello world" Managed Agent: `interactions.create`, render one `interaction.step`. | B, A |
| 11:00–11:30 | **PRE-WARM:** agent installs **real GnuCOBOL via `micromamba`/conda-forge userland** (no root; network on) into ONE long-lived `environment_id` that's reused on stage (so the live run needs no network); verify `cobc --version` survives reconnect. Capture `golden_io.json` from a real `cobc` run as the deterministic fallback. Pick golden COBOL module. | C |
| 11:30–13:00 | Core loop: ingest → translate → write Python → run COBOL oracle → gen tests → pytest. Get a real RED→GREEN once. | B |
| 11:30–13:00 | UI in parallel: stream steps, render diff + terminal. | A |
| 13:00–14:00 | **Lunch / keep building.** FORGE mechanism: detect unknown idiom → write `SKILL.md` into the env → next pass reuses the same `environment_id` and re-reads `.agents/skills/` → re-run. (No mid-run hot-reload; re-discovery happens on the next pass.) | B |
| 14:00–14:45 | Business-rule recovery panel (plain-English logic output). Wire git-diff animation for the forged skill. | A, B |
| 14:45–15:15 | Integrate oracle + fallback `golden_io.json`. Lock the golden input battery. | C |
| 15:15–16:00 | End-to-end dry run on the golden path. Fix the loop's non-determinism (cap iterations, pin seed). | All |
| **16:00–17:00** | **Demo hardening only — no new features.** Pre-warm script, fallback cache toggle, record backup video, rehearse 10×. | All |
| 17:00 | **Submit:** flip repo to **public**, push final, record 1-min submission video, add all teammates to the submission. | D |

## Definition of "done" for the demo path
1. Drop golden COBOL → plain-English rules appear (<25s).
2. Python written + COBOL oracle run + pytest RED (real failure).
3. Agent forges a `SKILL.md` (visible git diff) → next pass re-reads it from the reused env.
4. pytest GREEN, byte-for-byte equivalence shown.
5. Download the migrated module from the persistent sandbox.
6. Fallback cache verified to look identical if the live call stalls.

## Scope discipline (what we will NOT build)
- No multi-file/whole-repo migration. **One module.**
- No GitHub push over WiFi. Local repo, shown on screen.
- No `google_search`/`url_context` in the demo path.
- No second language target. COBOL→Python only.
- No auth/login screens (Ultimate Guide §V: skip them).
