# LAZARUS — Judging Strategy

## Scoring map

| Criterion | Weight | How LAZARUS scores | Target |
|---|---|---|---|
| **Live Demo** | 45% | Deterministic RED→GREEN, self-authored skill, verifiable oracle diff, single sandbox call, zero live network. | 8.5/10 |
| **Creativity / Originality** | 35% | Business-rule recovery + differential equivalence + live self-authoring lifts it above the generic SWE-agent loop. | 7/10 |
| **Impact** | 20% | $2.41T tech debt, NJ unemployment crisis, $30B+ modernization market. Best on the board. | 9.5/10 |
| **$5k Managed Agents bonus** | — | Model writes & runs its own code, persists files, forges its own skills — all in the hosted sandbox. | Primary target |

**Weighted ≈ 8.2 / 10.**

## Know your judges (Ultimate Guide §III)

This panel is a mix — tailor to **both**:

- **Google DeepMind (technical / CTO judges):** will probe correctness, where it breaks, scalability. → Lead with the **GnuCOBOL differential oracle** (real correctness, not self-graded tests) and the honest single-agent architecture. Be ready for "is this actually Managed Agents?" — yes, code execution + persistent files + `SKILL.md`. And for "how does GnuCOBOL even get into the sandbox without root?" — the agent installs it itself via **micromamba/conda-forge userland** at pre-warm (the conda package ships its own compiler + `libcob` + `gmp`; no `apt`, no root), into a reused environment so the demo run needs no network. In both the live and `golden_io.json`-fallback paths, the oracle is **real GnuCOBOL output, never agent-invented** — the falsifiability claim holds either way.
- **AI Futures Fund deal team (investor judges):** 1st place includes a 30-min call with them. They ask "could this be a company?" → Frame LAZARUS as eating the **$30B+ legacy-modernization services budget** with a defensible moat: a **growing library of forged dialect skills** (each migration authors `SKILL.md`s we re-register into the base agent, so coverage compounds across *jobs* — not automatically across runs, but by design), plus regulated-trust and a translation/equivalence corpus.

**Hard rule:** fake nothing. The rules disqualify undisclosed/faked work, and DeepMind judges will catch it.

## The pitch (Ultimate Guide §VII format)

1. **Problem** — NJ 2020: the governor publicly called for volunteer COBOL programmers; claims spiked 1,600% (over 362,000 in two weeks).
2. **Solution** — an agent that migrates *and proves* legacy code, teaching itself missing skills.
3. **Demo** — the 2-minute RED→GREEN run (see `DEMO_SCRIPT.md`).
4. **Impact / Market** — $2.41T debt; $30B+ services market; banks, gov, insurance.
5. **Why now / why us** — Gemini 3.5 Flash 1M context + Managed Agents make autonomous, *verified* migration possible for the first time.
6. **Team** — (names on nametags; don't waste seconds).

## The investor objection to pre-empt
> "Translation correctness in regulated systems is existential — one wrong financial calc and you're uninsurable."

Answer: that's exactly why we built the **differential oracle** — equivalence is proven against the original program's real output, not asserted. The moat is trust + verification, not just translation.

## $5k Managed Agents bonus — checklist
- [x] Uses the Managed Agents API (Antigravity base agent), not a plain `generateContent` loop.
- [x] Model writes AND executes its own code in the hosted sandbox.
- [x] Files (the conda-installed GnuCOBOL, forged skills, migrated output) persist across turns in the reused environment.
- [x] Custom agent defined via `AGENTS.md` / `SKILL.md`; new skills authored at runtime.
- [x] No reliance on unsupported features (`mcp`, `computer_use`, sub-agents).
