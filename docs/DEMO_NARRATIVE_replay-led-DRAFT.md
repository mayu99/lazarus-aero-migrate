# LAZARUS — Honest replay-led 2-minute demo narrative (DRAFT — SUPERSEDED)

> **STATUS: SUPERSEDED — the user chose STRICTLY LIVE in-slot (no mock lead), accepting the
> multi-minute reality.** This replay-led draft is NOT the demo vehicle. It is kept ONLY for
> decision-history and because the "If the user insists on live" section below + the honesty
> guardrails still inform the live narrative. The live narrative lives in
> `DEMO_NARRATIVE_live-DRAFT.md`. Do NOT hand this file to doc-keeper.
>
> ---
>
> **Original status (now moot):** DRAFT by devils-advocate, requested by team-lead, pending the
> USER's vehicle decision (the user earlier said "no mock, fully live by default"; qa's wall-clock
> data — live runs take 8–12+ min with minutes of blank screen — makes leading a *timed 2-min slot*
> with a live run impractical). If the user picks pre-warmed-live or strictly-live instead, we
> adapt (see "If the user insists on live" at the bottom).
>
> **Why this draft exists:** the current `docs/DEMO_SCRIPT.md` narrates a *live* run completing
> RED→GREEN→Download in 1:55. Per qa (3 real-key runs: ~8.3 min to >12 min), that timeline is
> not achievable live. Presenting it as live-in-2-min would be false. This draft keeps the same
> beats + impact lines but makes the VEHICLE and TIMELINE honest.

---

## The core honesty principle (non-negotiable)

The thing on screen during the 2-min slot is a **faithful replay of a real run** (`?mock=1`),
NOT a live run. We say so, plainly, once — and we make it trivially checkable:

- The replay is **built from REAL artifacts**: the COBOL outputs in `mock-run.json` are real
  GnuCOBOL bytes (`golden_io.json`), and the migrated module + skill mirror a real LAZARUS run.
- The UI **already labels it** ("BREAK-GLASS · cached run", clock reads "cached") — we do not
  hide it.
- We **prove it's real, live**, in the same slot: a pre-warmed live run finishing in the
  background, or the real `Download` artifact + `EQUIVALENT` verdict from a live run we kicked
  off before the slot. qa confirmed a real live run ends EQUIVALENT with the agent's real module.

**The line we never cross:** we do NOT call the replay "live," do NOT say "watch it run live in
two minutes," and do NOT let a judge believe the 22-second on-screen run is happening live. A
judge who times it would catch a live run's minutes of blank screen — so we get ahead of it.

---

## The script (target 1:55) — replay-led, honestly framed

| Time | On screen (the `?mock=1` replay, ~22s scripted, paced for narration) | Narration |
|---|---|---|
| **0:00–0:12** | Open the app. Drop `payroll.cob`. | "This COBOL ran a state unemployment system. In 2020 New Jersey's governor publicly called for volunteers who could still read it — claims had spiked 1,600%. **What you're about to see is a faithful replay of a real LAZARUS run — built from real GnuCOBOL output. I kicked off a genuine live run before this slot; it's finishing in the background and I'll show you its real result at the end.**" |
| **0:12–0:35** | Plain-English business-rules panel fills in (the rounding rule, the tax edge-case). | "First it recovers the rules — the institutional knowledge that retired with the people who wrote it." |
| **0:35–0:55** | Agent writes `payroll.py`; the differential oracle diffs Python against the **real COBOL bytes**; terminal goes **RED**. | "It doesn't grade its own homework — it diffs against the *real* COBOL's output as ground truth. Right now they don't match." |
| **0:55–1:25** | Agent diagnoses the true idiom — **COBOL numeric `DISPLAY` formatting (zero-padded `0000775.00`) + `ROUND-HALF-UP`** — and **writes a new `SKILL.md`** (git diff animates), re-read on the next pass. | "Instead of failing, it teaches *itself* the missing rule — how COBOL formats and rounds money — writes that skill into its sandbox, and re-runs with it." |
| **1:25–1:45** | Re-run → Python matches COBOL **byte-for-byte → GREEN**; COBOL↔Python diff shown. | "Red to green. Proven equivalent to the mainframe — not approximated." |
| **1:45–1:55** | **Cut to the live proof:** the background live run's real `Download` (the agent's actual `/workspace/payroll.py`) + `EQUIVALENT` verdict. | "And that wasn't theater — here's the *live* run I started before this slot: same result, the real migrated module, pulled from the real sandbox. Sixty years of code, modernized *and verified*. A $2.4-trillion problem, solved autonomously." |

> Timeline note: the replay's intrinsic length is ~22s; we PACE it (scrubber/auto-advance) to
> fill 1:55 with narration. The live proof at 1:45 is the honesty anchor — it converts "replay"
> from a weakness into a credibility move.

---

## Why this is STRONGER than pretending it's live

1. **It survives a judge timing it.** The #1 risk with a "live in 2 min" claim is the judge who
   notices the live run can't actually do that. Leading with an honest replay + a real live proof
   removes that trap entirely.
2. **The honesty IS the pitch with a DeepMind judge.** "We show you a faithful replay, and here's
   the live system proving it's real" reads as rigor, not weakness — same posture as the
   differential-oracle ("we don't grade our own homework").
3. **The artifacts are genuinely real**, so nothing in the replay is fabricated — it's a
   time-compression of real work, clearly labeled.

---

## If the user insists on live (alternatives, ranked)

The user's "no mock, fully live by default" stands as the PRODUCT default; for a *timed slot*:

- **Best live option — pre-warmed + pre-started:** start the live run BEFORE the slot (it needs
  ~8–12 min). During the slot, narrate the architecture against the already-progressing/finished
  live UI, and end on its real Download + EQUIVALENT. Honest, fully live, fits the slot — but
  depends on the pre-start completing and on stable latency (qa saw one run still on iteration 1
  at 12+ min, so even a pre-start has variance — keep the replay as the safety net).
- **Live with a long blank window (NOT recommended for a 2-min slot):** drop the file and watch it
  live from zero. qa's data says minutes of blank/working screen first; you will not reach RED→GREEN
  in the slot. Only viable in an untimed booth setting.
- Whatever the choice: keep the replay as the rehearsed safety net (the existing DEMO_SCRIPT
  "Safety cuts to cached green" line), and never relabel a replay as live.

---

## Concrete edits doc-keeper should make to `docs/DEMO_SCRIPT.md` (once vehicle chosen)

1. Retitle "2-Minute **Live** Demo Script" → "2-Minute Demo Script (replay-led, live-proven)".
2. 0:00 beat: add the one-sentence "this is a faithful replay of a real run, live proof at the
   end" framing.
3. Replace the implicit "this is happening live now" tone in 0:35–1:45 with replay-accurate verbs
   ("the replay shows…") — the BEATS and IMPACT LINES stay; only the vehicle framing changes.
4. 1:45 beat: make the live-proof cut explicit (background live run's real Download + EQUIVALENT).
5. De-risking checklist: promote the cached run from "break-glass if pytest stalls" to the PRIMARY
   in-slot vehicle; add "live run pre-started before the slot for the end proof."
6. Add a wall-clock honesty note: live end-to-end is ~8–12 min (qa-measured); the slot uses the
   replay + a pre-started live proof.
