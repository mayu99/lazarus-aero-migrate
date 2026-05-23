# LAZARUS — Live Trace Stream Contract (v1)

The UI is driven entirely by an **ordered sequence of JSON events**. The same
renderer consumes (a) the bundled `mock/mock-run.json` for offline rehearsal and
(b) the live `interaction.steps` SSE stream from the Managed Agents API.

Field names below are the UI's **internal canonical shape**. The live API's
`interaction.steps` will differ; do NOT change the renderer to match the API.
Instead, map the API shape to this contract in **one place**:
`src/adapter.js`. That is the only file that should know the real API field
names. (researcher-agents: send me the real `interaction.steps` JSON and I'll
write the mapping there — it's a ~20-line change.)

---

## Top-level run object

```jsonc
{
  "version": 1,
  "meta": {
    "agent": "lazarus",
    "base_agent": "antigravity-preview-05-2026",
    "module": "payroll.cob",
    "started_at": "2026-05-23T10:42:00Z",
    "iteration_cap": 4            // hard cap shown in the UI counter
  },
  "events": [ /* ordered Event[] — see below */ ]
}
```

Each event carries a `t` (milliseconds from run start) used by the mock player to
schedule playback on a timer. The live adapter ignores `t` (events arrive when
they arrive) — it is only meaningful for the scripted mock.

---

## Event types

Every event is `{ "type": "<type>", "t": <ms>, ... }`.

### 1. `phase` — drives the top status rail / which beat we're in
```jsonc
{ "type": "phase", "t": 0,
  "phase": "ingest|recover|translate|oracle|test|diagnose|forge|reload|verify|done",
  "label": "Recovering business rules",
  "iteration": 1 }            // current loop iteration (for the counter)
```

### 2. `step` — a single line in the "AGENT WORKING" trace panel (b)
The agent's observable `interaction.steps`: thoughts, tool calls, code, output.
```jsonc
{ "type": "step", "t": 1200,
  "kind": "thought|tool_call|code|output|status",
  "title": "Reading payroll.cob",      // optional, shown as a header chip
  "tool": "code_execution",            // for kind=tool_call
  "lang": "bash|python|cobol",         // for kind=code (syntax hint)
  "text": "cobc -x payroll.cob -o payroll.bin",
  "status": "running|ok|error",        // optional badge
  "duration_ms": 340 }                 // optional, rendered as a timing pill
```

### 3. `business_rule` — one recovered rule for the BUSINESS RULES panel (c)
The "archaeology" beat. Streamed one at a time so they type in dramatically.
```jsonc
{ "type": "business_rule", "t": 4000,
  "id": "tax-progressive",
  "title": "Progressive tax withholding",
  "plain": "22.5% of gross pay is withheld as tax before computing net.",
  "cobol_ref": "COMPUTE WS-TAX ROUNDED = WS-GROSS-PAY * WS-TAX-RATE",
  "severity": "rule|edge_case|gotcha" }   // gotcha = highlighted (e.g. rounding)
```

### 4. `diff` — populates the COBOL↔Python side-by-side viewer (d)
Sent once Python is written; may be re-sent after the forge with updated Python.
```jsonc
{ "type": "diff", "t": 9000,
  "left":  { "lang": "cobol",  "name": "payroll.cob", "code": "...full source..." },
  "right": { "lang": "python", "name": "payroll.py",  "code": "...full source..." },
  // optional line-level mapping for the connector lines / highlighting:
  "links": [ { "left": [21,21], "right": [14,18], "kind": "rule|gotcha" } ] }
```

### 5. `pytest` — drives the test terminal (e), RED → GREEN
```jsonc
{ "type": "pytest", "t": 11000,
  "result": "red|green|running",
  "iteration": 1,
  "summary": "3 failed, 0 passed in 0.42s",
  "cases": [
    { "name": "test_net_pay[12000.00]", "status": "fail|pass",
      "cobol": "0009300.00", "python": "0009300.05",   // the oracle diff!
      "message": "AssertionError: byte mismatch (COBOL ROUND-HALF-UP vs banker's)" }
  ] }
```

### 6. `oracle` — the differential-oracle banner (the #1 money shot)
Shows that ground truth is REAL COBOL output, not agent-invented assertions.
```jsonc
{ "type": "oracle", "t": 10500,
  "compiler": "GnuCOBOL cobc 3.2",
  "inputs": ["12000.00", "00345.67", "99999.99"],
  "note": "Canonical outputs captured from the original binary." }
```

### 7. `forge` — the self-authored SKILL.md / git-diff panel (f)
The "$5k" beat: the agent writes itself a new skill, then re-reads it on the next
pass within the same reused environment (no mid-run hot-reload — that's unverified).
```jsonc
{ "type": "forge", "t": 14000,
  "skill": ".agents/skills/numeric-display-rounding/SKILL.md",
  "reason": "Unknown idiom: COBOL numeric DISPLAY format + ROUND-HALF-UP.",
  "git": {
    "status": "A",                       // A=added, M=modified
    "additions": [ "line of new file", "..." ],   // rendered green, typed in
    "commit": "forge: add numeric DISPLAY + half-up rounding skill"
  } }
```

### 8. `reload` — agent re-reads the new skill on the next pass (same env)
```jsonc
{ "type": "reload", "t": 17000, "label": "Re-reading numeric-display-rounding skill in the reused environment" }
```

### 9. `download` — enables the Download button with a ready artifact (g)
```jsonc
{ "type": "download", "t": 21000,
  "name": "payroll.py",
  "mime": "text/x-python",
  "content": "...full migrated module source..." }
```

### 10. `done` — terminal event; stops the player, fires the success state
```jsonc
{ "type": "done", "t": 22000,
  "verdict": "EQUIVALENT",
  "summary": "Byte-for-byte equivalent to the mainframe across 3 inputs." }
```

---

## Adapter contract (live API → this shape) — WIRED to the verified API

`src/adapter.js` is the ONLY place that references real API field names. The
renderer never sees a raw API object. The mapping is now keyed to the verified
Managed Agents shape (researcher-agents):

**Streaming events** (`event.event_type`): `step.start` · `step.delta` ·
`step.stop` · `interaction.created` · `interaction.completed` ·
`interaction.status_update` · `error`.

The live trace is a **3-event lifecycle per step**: `step.start` opens a card,
`step.delta` streams text into it (`event.delta.text`, only when
`event.delta.type === "text"`), `step.stop` finalizes it. The renderer renders
one finalized card per step, so drive it with the stateful **`StreamAdapter`**:

```js
const sa = new StreamAdapter();
for await (const event of sseStream) {
  for (const ev of sa.ingest(event)) livePlayer.push(ev);
}
```

`StreamAdapter` accumulates `step.delta` text against the open step (keyed by
`event.index`) and emits the canonical Event on `step.stop`, preferring the
step's own text but falling back to accumulated deltas (the `step.stop` payload
may omit the streamed text).

⚠️ Two API caveats baked into the adapter:
1. `step.stop` may not carry the full streamed text → accumulate deltas (done).
2. `interaction.completed` arrives "with empty outputs to reduce payload" → do
   NOT read final text/steps from it; we already have everything from the
   stream. For the authoritative final object (e.g. `environment_id`, full
   steps) the orchestrator calls `client.interactions.get(interaction_id)`.

**Step objects** (`event.step.type`) map to the trace as:

| API `step.type` | canonical `kind` | text source |
|---|---|---|
| `thought` | `thought` | `summary[].text` |
| `code_execution_call` | `code` | `arguments.code` (+ `arguments.language`) |
| `code_execution_result` | `output` | `result` (`is_error` → `status:"error"`) |
| `model_output` | `output` | `content[].text` |
| `user_input` | `status` | `content[].text` |

Exports: `StreamAdapter` (live SSE lifecycle — preferred), `adaptStreamEvent(event)`
(stateless single-event convenience, no delta accumulation), `adaptStep(step)`
(one Step object), `adaptInteractionStep(raw)` (back-compat alias),
`normalizeRun(run)` (mock passthrough + non-streamed payloads).

**Still pending alignment with backend-eng** (these are NOT raw `interaction.steps`):
the `business_rule`, `diff`, `pytest`, `oracle`, `forge`, `reload`, and
`download` events. These are derived by the orchestrator from tool outputs
(pytest stdout, `git diff`, the written SKILL.md, the migrated module) and
should be emitted as structured canonical events alongside the adapted steps —
or parsed out of `code_execution_result` text. Either way, the renderer already
consumes them; only the producer side (orchestrator) needs to emit them.
