# LAZARUS — 60-second launch video script

Target: ~150 words ≈ 60s at narration pace. 8 beats, one slide each (~7.5s).
Honesty bar (same as the project): every claim is true — proof is real, the
runtime is multi-minute (we never imply instant), Google features named accurately.

| # | t (s) | Slide (visual) | Narration |
|---|---|---|---|
| 1 | 0.0–7.5 | **The crisis** — huge "1,600%" in amber over a faint COBOL listing; "NJ, 2020" | "In 2020, New Jersey's unemployment system buckled under a sixteen-hundred-percent surge — and the governor publicly begged for volunteers who could still read COBOL." |
| 2 | 7.5–15 | **The scale** — "$2.4T" tech debt; icons: banks · benefits · hospitals | "Sixty years of critical code runs our banks, benefits, and hospitals — in a language almost no one speaks, with business rules nobody wrote down. The cost of that debt: two-point-four trillion dollars." |
| 3 | 15–24 | **LAZARUS** — stylized wordmark, "raising dead code back to life"; COBOL→Python | "Meet LAZARUS. Drop in legacy COBOL — it recovers the lost business rules and rewrites them as clean, modern Python." |
| 4 | 24–35 | **The proof** — RED→GREEN; "it does not grade its own homework"; diff vs real cobc | "But here's the difference: it does not grade its own homework. LAZARUS runs the original COBOL through a real compiler and proves its Python matches — byte for byte. Red, to green." |
| 5 | 35–43 | **FORGE** — a SKILL.md being authored, re-read arrow | "Meet an idiom it doesn't know? It writes itself a new skill mid-mission, re-reads it, and tries again — until the proof holds." |
| 6 | 43–52 | **Built on Google's newest** — Gemini 3.5 Flash (1M context) + Managed Agents API | "Built on Google's newest: Gemini 3.5 Flash — a million-token context that reads a fifty-thousand-line module whole — and the Managed Agents API, running real code in a live sandbox that persists the skills it forges." |
| 7 | 52–58 | **Where it runs** — government · banking · insurance · healthcare · tax | "Government benefits, banking, insurance, healthcare — anywhere dead code still runs the world." |
| 8 | 58–60 | **Close** — wordmark + tagline | "LAZARUS. Proven, autonomous modernization." |

## Slide design system
- Background `#06090b`; accent green `#54f0a6`; amber `#f2b657`; text `#d6e0d9`, muted `#93a79b`.
- Display face heavy sans (Archivo-like / system 900); mono for code (`IBM Plex Mono`-like).
- Each slide 1920×1080, generous whitespace, one idea per slide (matches the "calm console" brand).
- Motion: ffmpeg `zoompan` slow Ken-Burns push + 0.4s `xfade` crossfades; subtle riser/whoosh SFX on cuts.

## Honesty checks (devil's-advocate bar)
- "proves byte-for-byte / red to green" — TRUE (differential oracle vs real GnuCOBOL).
- "million-token context reads 50k-line module whole" — accurate to Gemini 3.5 Flash's 1M context.
- "live sandbox that persists the skills it forges" — accurate (env-reuse skill persistence; no mid-run hot-reload claim).
- No claim of instant/2-minute completion (a real run is ~8–9 min — not stated as fast).
