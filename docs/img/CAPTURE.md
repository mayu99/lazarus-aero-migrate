# Demo screenshots

Drop four PNGs here to give the README a visual front door. They take ~2 minutes
to capture from the cached replay — no API key needed.

## How to capture

```bash
cd web && python3 -m http.server 8080
# open http://127.0.0.1:8080/index.html?mock=1  →  click "use the sample — payroll.cob"
```

Let the 22-second replay run, then screenshot each panel and save with these names:

| File | Panel | What to frame |
|---|---|---|
| `01-hero.png`    | Landing | The "Raising dead code back to life" hero + the stylized LAZARUS wordmark (top-left) |
| `02-rules.png`   | Business rules recovered | The phase rail + the 4 rule cards incl. the **DISPLAY de-editing GOTCHA** |
| `03-diff.png`    | COBOL → Python | The side-by-side diff (payroll.cob ↔ payroll.py) under the **GREEN** proof badge |
| `04-proof.png`   | Proof / FORGE | The differential-oracle banner + `PASS` cases, and the forged `SKILL.md` |

## Then embed them

Add this block to the README's **Demo** section (replacing the text walkthrough or
alongside it):

```markdown
![Hero](docs/img/01-hero.png)
![Business rules recovered](docs/img/02-rules.png)
![COBOL → Python, proven GREEN](docs/img/03-diff.png)
![Differential-oracle proof + forged skill](docs/img/04-proof.png)
```

> Tip: a short labeled GIF of the full 22-second replay (e.g. `00-run.gif`) makes an
> even stronger header image. Record the `?mock=1` run and label it "cached replay."
