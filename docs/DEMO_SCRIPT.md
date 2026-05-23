# LAZARUS — Live Demo Script (strictly-live, multi-minute)

> Live Demo is **45%** of the score. This path is **genuinely live** — no recording, no replay.
> The value proposition is **not speed**: it's that a real agent does real work and ends in a
> **byte-for-byte proof against the real COBOL compiler**. A multi-minute runtime is a feature of
> authenticity, framed correctly — not a flaw to hide.
>
> **Measured reality (qa, real key):** an end-to-end live run is **~8–9 minutes** and variable
> (one run was 19 min before the tarball-gate fix; one was still on iteration 1 at 12+ min). The
> on-screen **elapsed timer** runs the whole time, the agent trace + `✓ ok` breadcrumbs accrue
> continuously, and the phase rail completes the full pipeline **in order** — so the screen is
> provably alive during the agent's longer silent stretches. (The rail beats light as the structured
> results land, mostly toward the end — it's a correct, complete sequence, not a live beat-by-beat
> march.) Plan the slot accordingly — do **not** promise a finish in two minutes.

## Roles during the demo
- **Driver** (Agent engineer): one machine, sandbox **pre-warmed** (env reused, GnuCOBOL already installed), drops the golden input.
- **Narrator** (BizDev/presenter): sets the multi-minute expectation up front, fills the run with impact/scale, delivers the closing line on the real result.
- **Safety** (Utility/QA): second laptop + hotspot; watches the clock; ready to cut over to a pre-started live run or — last resort — the **labeled** `?mock=1` cached run if the API dies.

## The script (beat-ordered — runs for however long the real migration takes, ~several min)

| Beat | On screen (REAL live run) | Narration |
|---|---|---|
| **Open** | App open, sandbox pre-warmed; drop `payroll.cob`; the run STARTS for real; **elapsed timer begins**. | "I'm going to run this for real, right now — no recording, no replay. **Fair warning: a genuine migration takes a few minutes, and you'll watch every step.** This COBOL ran a state unemployment system; in 2020 New Jersey's governor publicly called for volunteers who could still read it — claims had spiked 1,600% in a week." |
| **Recover** | Business-rules panel fills as the agent recovers them; trace + WORKING banner advance; elapsed time visible. | "It's reading the whole module and recovering the business rules — the institutional knowledge that retired with the people who wrote it. This is the real agent thinking, live." |
| **Translate** | Agent writes `payroll.py`; the COBOL↔Python diff appears side-by-side. | "Now it's writing idiomatic Python — original COBOL on the left, the agent's output on the right." |
| **Prove (the heart)** | It holds the Python to the **original COBOL's real GnuCOBOL output** — ground-truth bytes captured ahead of time — generating equivalence tests and running `pytest` against them. RED if a rounding idiom diverges. *(If the agent recompiles `cobc` live this run, narrate that as an opportunistic refresh — don't assert it if it doesn't fire.)* | "Here's what matters: it does **not** grade its own homework. The ground truth is the original COBOL's real output, captured from real GnuCOBOL — it diffs the Python against those exact bytes. Watch the cases." |
| **Forge (if it happens)** | Agent diagnoses the idiom (numeric `DISPLAY` zero-padding `0000775.00` + `ROUND-HALF-UP`), writes a `SKILL.md` — the diff animates in — and re-reads it on the next pass. | "Instead of failing, it teaches *itself* the missing rule and writes that skill into its own sandbox — live." |
| **GREEN + Download** | Byte-for-byte match → **GREEN**; **Download** arms with the agent's real `/workspace/payroll.py`; final elapsed time on screen. | "Red to green — proven equivalent to the mainframe, byte for byte. This is the real migrated module, pulled from the live sandbox. **That took N minutes — because it actually happened.**" |

> The closing line **owns** the runtime ("that took N minutes — because it actually happened")
> instead of apologizing for it. The elapsed timer on screen the whole time is the honesty anchor.

## The three "money shots" (make sure each is unmistakable)
1. **The oracle diff** — real COBOL output vs Python output (kills the verifiability objection before it's asked).
2. **The self-authored `SKILL.md`** — the agent visibly upgrading itself.
3. **RED → GREEN** — binary, legible, no explanation needed.

## Honesty guardrails (non-negotiable)
1. **Set the multi-minute expectation UP FRONT** (first sentence). Never imply it's fast.
2. **Show elapsed time, don't hide it.** The visible timer makes "this is really running" checkable.
3. **No faked speed.** No cuts, no time-skips, no editing presented as real-time. Talk over the slow stretches with architecture/impact/Q&A-bait — the clock keeps running honestly. If a recorded video is ever used as a fallback, label it "recording" — never imply live.
4. **Mock stays `?mock=1` break-glass ONLY** — the true fallback if the live API dies mid-demo, never the lead. If you cut to it, **say so**: "the live API just dropped — here's a cached run of the same migration."
5. **If the run exceeds the slot or the API stalls:** cut to a **pre-started** live run that's further along; last resort is the labeled cached run. Decide the cutoff in advance; don't improvise on stage.

## De-risking checklist (lock in the final 2 hours)
- [ ] **Ground truth = `golden_io.json`** (real GnuCOBOL output, captured + verified ahead of time — the falsifiable floor). The demo does **not** depend on a live compile succeeding on stage.
- [ ] **Pre-warm + reuse the `environment_id`** so 0:00 isn't a cold start; the agent installs GnuCOBOL via micromamba in the reused env to recompile live as an *opportunistic refresh* (verify `cobc --version` after reconnect — but don't narrate a live compile unless it actually fires).
- [ ] **Pre-start a SECOND live run** before the slot as the cutover target if the on-stage one stalls (latency is variable — budget for it).
- [ ] **Confirm live-progress surfacing:** during-run liveness = the WORKING-banner **elapsed timer** (ticks 1s, stops on done) + the agent trace + `✓ ok` breadcrumbs accruing. On a successful run the **phase rail completes the full pipeline in order** (ingest→recover→translate→oracle→test→forge→reload→done — the server emits these phases in fixed sequence from the ordered structured events, NEVER from prose: see server.py `_run_migration`; deterministic + unit-tested). Its beats light as those results land (toward the end), NOT beat-by-beat live — don't narrate it as a live march. (Earlier live captures predate this fix; a fresh rehearsal capture will show the in-order rail end-to-end.)
- [ ] **Golden COBOL module** hand-picked: ~150 lines, one reproducible idiom (decimal/rounding) the model resolves in 1–2 iterations. Rehearse **10×** end-to-end (real timing).
- [ ] **Hard-cap iterations at 4** with a visible counter.
- [ ] **Pin** model + thinking level; disable silent auto-retries that can hang.
- [ ] **Break-glass:** `?mock=1` replays the cached run (real GnuCOBOL golden bytes) — labeled "cached" in the UI; only cut to it if the API dies, and announce it.
- [ ] **Backup video** of a clean full run recorded the morning of, in case the laptop dies — labeled "recording" if shown.

## Q&A prep (judges WILL ask)
- **"Why does it take a few minutes?"** → "Because it's real. It provisions a live sandbox, recovers the rules, writes the Python, and proves it equivalent to the original COBOL's real output, byte for byte. The runtime is the proof it isn't a canned animation."
- **"How do you know the translation is correct?"** → "The ground truth is the original COBOL's real output — captured from real GnuCOBOL — and we assert the Python is byte-for-byte equivalent to those bytes. The verdict tracks that oracle, not our own tests. The agent also installs GnuCOBOL and tries to recompile the COBOL live in the sandbox to refresh that ground truth." *(Honest: the captured golden bytes are the falsifiable floor; a successful live recompile is an opportunistic refresh, not a guarantee every run.)*
- **"Is this multi-agent?"** → "No — one Managed Agent in one sandbox. We deliberately avoided unsupported sub-agent orchestration."
- **"What did you build today vs the platform?"** → "The migration loop, the differential oracle harness, the live trace UI, and the self-authoring skill mechanism. Gemini provides the model + sandbox."
- **"Does it scale to a real mainframe?"** → "Gemini 3.5 Flash's 1M-token context ingests a 50k-line module in one shot — the demo is a curated slice, but the same loop runs at full scale. And within a migration the forged skills stay live in the environment; to carry a dialect skill into future jobs we re-register the agent with it mounted, so a real deployment builds a reusable skill library over time." *(Honest scope: skills persist for the life of the reused environment; a fresh run forks clean unless we re-register — we don't claim automatic cross-run accumulation.)*
