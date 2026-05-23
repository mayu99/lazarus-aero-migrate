# LAZARUS — Completion v2: make the LIVE demo genuinely complete

> Date 2026-05-23 · Owner: team-lead (Claude) · Goal: the LIVE run (real key) must
> drive EVERY panel from real agent output, end-to-end, looking complete and clean —
> not just the scripted mock. Verified with the provisioned key + signed off by the
> devil's advocate.

## Root causes (assessed from src/server.py + the live screenshot)
1. **Events arrive only at the END.** `_run_migration` streams raw `step` text during
   the (multi-minute) run, but pushes `business_rule / diff / oracle / pytest / forge /
   download / done` only AFTER `migrate()` returns. During the run the UI shows just the
   raw log → looks empty.
2. **Structured panels depend on markers the agent doesn't reliably emit.**
   `parse_oracle_records` / `business_rules_from_text` need `LAZARUS_ORACLE_JSON` /
   `LAZARUS_RULE` lines; the live agent does its own thing, so panels stay empty.
3. **Only `ingest` + `test` phases are emitted live** (no recover/translate/oracle/forge),
   so the single-focus UI only ever shows the empty TEST card.
4. **The `diff` (COBOL↔Python) panel is never emitted on the live path at all.**
5. **UI hides everything except the active card** → completed artifacts vanish → "missing."
6. Misc: `LAZARUS` wordmark barely legible (Major Mono Display); download visibility;
   verify the Files-API download returns a real payroll.py live.

## Workstreams

### A. integration-eng (backend/live wiring) — the core fix
- Drive structured events **progressively** from the live `step.*` stream, not at the end:
  map agent milestones → `phase` events (recovering rules→recover, writing payroll.py→
  translate, cobc/compile/run→oracle, pytest/equivalence→test, SKILL.md→forge, done→done).
- **Guarantee the panels populate even when the agent skips markers**: after the agent
  produces `payroll.py`, fetch it via the Files API and (a) emit a `diff` event (COBOL in /
  payroll.py out) and (b) run the differential oracle locally against `golden_io.json` to
  emit a STRUCTURED `pytest` event (per-case COBOL-vs-Python). Markers remain the fast path;
  the local oracle is the deterministic fallback so the demo never looks empty.
- Emit `business_rule` events from markers if present, else parse the agent's recovered-rules
  text into ≥3 rules. Emit the `oracle` banner from golden_io.json (already done).
- Keep golden_io.json (real cobc) as ground truth; emit `forge` from the detected SKILL path.
- Tighten the agent prompt so it emits the markers + writes payroll.py to a known path.

### B. frontend-eng (UI completeness)
- **Progressive reveal, not hide-all:** completed step cards STAY visible (accumulate) in a
  clean vertical flow; the active one is emphasized; the screen is never empty. Keep it
  calm (one ambient layer, whitespace) but show the journey.
- Graceful long-run waiting state (progress + latest action) — refine.
- Fix the `LAZARUS` wordmark legibility; ensure the Download button is always visible and
  arms on `download`; clean error states (no-key / backend-down); remove visual artifacts.
- Live default; `?mock=1` break-glass only.

### C. qa-verifier — end-to-end with the real key
- Run a live migration (provisioned key). Confirm EVERY panel populates from real output:
  phases progress, business rules, COBOL↔Python diff, oracle banner, per-case pytest
  RED→GREEN, forge, verdict EQUIVALENT, and Download yields a real `payroll.py`.
- Report any panel that stays empty + timing; capture the final state.

### D. devils-advocate
- Challenge: does LIVE truly populate everything, or only the mock? What would a DeepMind
  judge see as missing/broken? Is the downloaded module real (from the sandbox)? Any honesty
  gaps (e.g. golden-derived pytest presented as the agent's own)? Is the 2-min demo coherent?

## Definition of done
A single LIVE run on the real key drives the whole UI — phases advance; rules, diff, oracle,
per-case RED→GREEN, forge, and Download all populate from REAL agent work; ends EQUIVALENT
with a downloadable, runnable `payroll.py`. qa-verifier confirms on the live key; devils-
advocate signs off that nothing material is missing or misleading.
