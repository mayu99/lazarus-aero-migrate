# LAZARUS — Live Trace Console (`web/`)

The demo surface. A CRT-phosphor ops console that renders the agent resurrecting
COBOL into tested Python, live. **Live Demo is 45% of the score — this UI is the
demo.**

## Two modes: LIVE (default) and the mock FALLBACK

**LIVE (default).** Drop a COBOL module → the UI POSTs it to the FastAPI backend
(`src/server.py`) → real Gemini Managed Agent stream → live-trace UI → real
download of the migrated module from the persistent sandbox. Requires the
backend running (and `GEMINI_API_KEY`). If the backend is unreachable, the UI
degrades gracefully: a clear error card in the trace, plus a hint to use the
fallback.

**FALLBACK — `?mock=1`.** Plays the bundled scripted run (`mock/mock-run.json`)
with no backend, no network, no API. This is the demo Safety net
(DEMO_SCRIPT.md de-risking — the "cached green run" the operator cuts to if the
live call stalls) and the offline rehearsal/contract-reference path. **Off by
default; never in the live path.**

## Run it

Zero build for the front-end. ES modules + `fetch` need `http://`, not
`file://`.

**Live (full pipeline):** start the backend, then open it:
```bash
# from repo root — backend serves the stream the UI consumes
export GEMINI_API_KEY=...
uvicorn src.server:app --port 8000      # see backend-eng / src/server.py
# open http://localhost:8000  (backend should serve web/ or set ENDPOINTS.base)
```

**Fallback / offline rehearsal (no backend):**
```bash
cd web
python3 -m http.server 8000
# open http://localhost:8000/?mock=1
```

Then click **"load golden sample · payroll.cob"** (or drop a `.cob` file). The
migration runs: business rules stream in → Python is written → the original
COBOL is compiled & run as the oracle → pytest goes **RED** → the agent
**forges a `SKILL.md`** (git diff types in) → re-reads it on the next pass (same env) → pytest goes **GREEN**
→ byte-for-byte equivalence → **Download** unlocks.

## Controls

LIVE: ▶ / `Space` (re)starts the run; ↺ / `r` restarts; download pulls the real
artifact. Timeline scrubber/speed/skip are hidden (a real stream has no fixed
length).

FALLBACK (`?mock=1`) — rehearsal transport:

| Key / button | Action |
|---|---|
| `Space` / ▶ | play / pause |
| `r` / ↺ | restart the run |
| `f` / ⇥ | skip to the end (fires all events instantly) |
| `0.5× 1× 2× 4×` | playback speed |

## What's where

| File | Role |
|---|---|
| `index.html` | panel layout (dropzone, trace, rules, diff, terminal, forge, download) |
| `style.css` | the "Mainframe Necromancy" aesthetic |
| `src/app.js` | entry: mode select (live default / `?mock=1`), drop-zone, controls, download |
| `src/live.js` | **live SSE client** — POST cobol → subscribe stream → push Events; real download URL |
| `src/player.js` | `MockPlayer` (timeline) / `LivePlayer` (push) — same renderer interface |
| `src/renderer.js` | turns canonical Events into DOM updates per panel |
| `src/adapter.js` | **the only file that knows real API field names** (`StreamAdapter` for live step.*) |
| `src/highlight.js` | tiny COBOL / Python / Bash syntax highlighter |
| `mock/mock-run.json` | the scripted RED→GREEN→forge→GREEN run (fallback + contract example) |
| `STREAM_CONTRACT.md` | the canonical event shape every panel consumes |

## Going live (when the real API is wired)

The renderer only ever sees the **canonical Event shape** in
[`STREAM_CONTRACT.md`](./STREAM_CONTRACT.md). To switch from mock to live:

1. researcher-agents sends the real `interaction.steps` JSON.
2. Update the mapping table + `adaptInteractionStep()` in `src/adapter.js`
   (the only place that references API field names — a ~20-line change).
3. Construct a `LivePlayer` instead of `MockPlayer` and `player.push(adapted)`
   for each step as it streams from SSE.

Nothing in `renderer.js` / `style.css` / `index.html` changes.
