# LAZARUS — Honest STRICTLY-LIVE demo narrative (DRAFT)

> **Status:** DRAFT by devils-advocate, requested by team-lead. The USER chose STRICTLY LIVE
> in-slot (no mock lead), accepting the multi-minute reality. Hand to doc-keeper for DEMO_SCRIPT.
> Supersedes `DEMO_NARRATIVE_replay-led-DRAFT.md`.
>
> **The pivot:** the value proposition is NOT speed — it's that this GENUINELY runs live, and you
> watch a real agent do real work, ending in a byte-for-byte proof against the real compiler. A
> multi-minute runtime is a feature of authenticity, framed correctly, not a bug to hide.

---

## ⚠️ HARD DEPENDENCY (must verify before this narrative is viable) — the UI must visibly PROGRESS

The entire "watch it work" story collapses if the screen looks FROZEN during the long run. qa
observed the live agent does "one long silent interaction, then bursts at the end" — if that means
the WORKING banner sits on the same line for minutes with no movement, a judge sees a hung app, not
a working agent. **Before committing to strictly-live, qa must confirm whether the live UI visibly
progresses** (streamed step text advancing the WORKING banner + trace, phase rail moving) DURING
the run, not only at the end.

- If it PROGRESSES: this narrative works as written.
- If it LOOKS FROZEN: we need live-progress surfacing FIRST (e.g. surface the agent's
  `step.delta` chunks as they arrive into the trace + banner; an elapsed timer; a heartbeat/"still
  working — N s elapsed" so the screen is provably alive). server.py already forwards `step` events
  per chunk and updates `_setWorking({action})` — so this hinges on whether the AGENT streams
  intermediate text, or goes dark. team-lead is chasing this with qa; resolve it before the slot.

This is the #1 risk for a strictly-live demo. Everything below assumes it's resolved (UI moves).

---

## The script (live, multi-minute — expectation set up front)

| Beat | On screen (REAL live run) | Narration |
|---|---|---|
| **Open (0:00)** | App open, sandbox pre-warmed (env reused; GnuCOBOL already installed). Drop `payroll.cob`; the run STARTS for real; elapsed timer begins. | "I'm going to run this for real, right now — no recording, no replay. **Fair warning: a genuine migration takes a few minutes, and you'll watch every step.** This COBOL ran a state unemployment system; in 2020 New Jersey's governor publicly called for volunteers who could still read it — claims had spiked 1,600%." |
| **Recover** | Business-rules panel fills as the agent recovers them; trace + WORKING banner advance; elapsed time visible. | "It's reading the whole module and recovering the business rules — the institutional knowledge that retired with the people who wrote it. This is the real agent thinking, live." |
| **Translate** | Agent writes `payroll.py`; COBOL↔Python diff appears. | "Now it's writing idiomatic Python — and here's the original COBOL beside the agent's output." |
| **Prove (the heart)** | Differential oracle diffs Python vs the **real COBOL bytes**; per-case pytest. RED if a rounding idiom diverges. | "Here's the part that matters: it does NOT grade its own homework. It diffs against the real COBOL's actual output as ground truth. Watch the cases." |
| **Forge (if it happens)** | Agent diagnoses the idiom (numeric DISPLAY format + ROUND-HALF-UP), writes a `SKILL.md`, re-reads it on the next pass. | "Instead of failing, it teaches itself the missing rule and writes it into its own sandbox — live." |
| **GREEN + Download** | Byte-for-byte match → GREEN; `Download` arms with the agent's real `/workspace/payroll.py`; final elapsed time shown. | "Red to green — proven equivalent to the mainframe, byte for byte. And this is the real migrated module, pulled from the live sandbox. That took N minutes — because it actually happened." |

> The closing line OWNS the runtime ("that took N minutes — because it actually happened") instead
> of apologizing for it. The elapsed timer on screen the whole time is the honesty anchor.

---

## Honesty guardrails (team-lead's constraints — reversed from the replay case)

1. **Set the multi-minute expectation UP FRONT** (first sentence). Never imply it's fast.
2. **Show elapsed time, don't hide it.** A visible timer makes "this is really running" checkable.
3. **No faked speed.** No cuts, no time-skips, no editing presented as real-time. If you must talk
   over a slow stretch, narrate the architecture / impact / Q&A-bait — but the clock keeps running
   honestly. (If a recorded video is ever used, label it "recording" — never imply live.)
4. **Mock stays `?mock=1` break-glass ONLY** — the true fallback if the live API dies mid-demo,
   never the lead, and if cut to, say so ("the live API just dropped — here's a cached run of the
   same migration").
5. **If the run exceeds the slot or the API stalls:** have the cutover plan rehearsed (to a
   pre-started live run that's further along, or — last resort — the labeled cached run). Decide
   the cutoff in advance; don't improvise on stage.

---

## What makes this honest AND strong with a judge

- Zero risk of "is this actually live?" — it demonstrably is, with a running clock.
- The differential-oracle proof is the payoff and it's REAL (qa cross-verified the agent's bytes
  against independent golden ground truth; the verdict tracks the oracle, not the agent's claims).
- "It's slow because it's real" reframes the one weakness into the core credibility claim — the
  same posture as "we don't grade our own homework."

---

## Practical de-risking for a multi-minute LIVE slot

- **Pre-warm + reuse the environment_id** so 0:00 isn't a cold start and GnuCOBOL is already
  installed (no live network needed).
- **Pre-start a second live run** before the slot as the cutover target if the on-stage one
  stalls (qa: latency is variable — one run was still on iteration 1 at 12+ min).
- **Confirm live-progress surfacing** (the HARD DEPENDENCY above) so the screen visibly moves.
- **Have a known cutoff + rehearsed `?mock=1` break-glass** if the API dies — labeled as cached.
- **Budget the talk track** to fill multi-minute gaps with impact/scale/Q&A-bait, clock running.

---

## Edits doc-keeper should make to `docs/DEMO_SCRIPT.md`

1. Retitle to reflect a real multi-minute live run (drop the implied 1:55 completion).
2. Add the up-front multi-minute expectation line + a visible elapsed timer to every beat.
3. Replace the "target 1:55" fixed timeline with a beat-ordered (not time-boxed) flow; total is
   "however long the real run takes (~several min)."
4. Keep the impact lines (NJ 1600%, "doesn't grade its own homework", red→green, $2.4T).
5. Reframe the de-risking checklist: pre-warm + pre-started cutover run + confirmed live-progress
   surfacing + `?mock=1` strictly as break-glass (labeled if used).
6. Add the honesty guardrails verbatim (no faked speed; elapsed shown; mock labeled if cut to).
