#!/usr/bin/env python3
"""Generate the 8 launch-video slides as 1920x1080 HTML files (launch/slides/).

Reproducible: run `python3 launch/make_slides.py`, then render each to PNG with
headless Chrome (see launch/render.sh) and assemble with ffmpeg (launch/build_video.sh).
Brand: dark calm console (#06090b), accent #54f0a6, amber #f2b657 — matches web/.
"""
from pathlib import Path

OUT = Path(__file__).parent / "slides"
OUT.mkdir(parents=True, exist_ok=True)

HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800;900&family=Major+Mono+Display&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:1920px;height:1080px;overflow:hidden}
  body{
    background:#06090b; color:#d6e0d9;
    font-family:'Archivo',system-ui,sans-serif;
    background-image:
      radial-gradient(120% 70% at 50% -10%, rgba(84,240,166,.07), transparent 55%),
      radial-gradient(140% 120% at 50% 50%, transparent 60%, rgba(0,0,0,.6));
  }
  .slide{position:relative;width:1920px;height:1080px;padding:130px 150px;display:flex;
    flex-direction:column;justify-content:center}
  .wm{position:absolute;top:60px;left:150px;z-index:5;font-family:'Major Mono Display',monospace;
    font-size:26px;letter-spacing:3px;color:#54f0a6;opacity:.85}
  .wm .dot{color:#2c5e49}
  .tag{position:absolute;top:64px;right:150px;z-index:5;font-family:'IBM Plex Mono',monospace;
    font-size:20px;letter-spacing:2px;color:#5f7268;text-transform:uppercase}
  .kicker{font-family:'IBM Plex Mono',monospace;font-size:30px;letter-spacing:4px;
    text-transform:uppercase;color:#54f0a6;margin-bottom:34px}
  .kicker.amber{color:#f2b657}
  h1{font-weight:900;font-size:118px;line-height:.98;letter-spacing:-3px;color:#f1fbf6}
  h1.huge{font-size:340px;line-height:.85}
  h1.amber{color:#f2b657}
  h1.green{color:#54f0a6}
  .sub{font-size:46px;color:#93a79b;line-height:1.45;margin-top:40px;max-width:1500px}
  .sub b{color:#d6e0d9;font-weight:700}
  .sub .g{color:#54f0a6;font-weight:700}
  .sub .a{color:#f2b657;font-weight:700}
  .code-bg{position:absolute;inset:0;font-family:'IBM Plex Mono',monospace;font-size:30px;
    line-height:1.7;color:rgba(84,240,166,.06);white-space:pre;padding:80px 150px;
    pointer-events:none;overflow:hidden;z-index:0}
  .slide>.kicker,.slide>h1,.slide>.sub,.slide>.row,.slide>.cards,.slide>.rg,
  .slide>.flow,.slide>.uses,.slide>.lazmark{position:relative;z-index:2}
  .row{display:flex;gap:34px;margin-top:54px;flex-wrap:wrap}
  .pill{font-family:'IBM Plex Mono',monospace;font-size:34px;padding:18px 38px;border-radius:99px;
    border:1px solid #1c2a24;background:#0c1311;color:#d6e0d9}
  .pill .i{color:#54f0a6;margin-right:14px}
  .cards{display:flex;gap:46px;margin-top:60px}
  .card{flex:1;background:#0c1311;border:1px solid #1c2a24;border-radius:24px;padding:54px}
  .card h3{font-size:50px;font-weight:800;color:#eafff5;margin-bottom:10px}
  .card .lab{font-family:'IBM Plex Mono',monospace;font-size:24px;letter-spacing:2px;
    text-transform:uppercase;color:#54f0a6;margin-bottom:26px}
  .card ul{list-style:none}
  .card li{font-size:34px;color:#93a79b;line-height:1.7;padding-left:42px;position:relative}
  .card li::before{content:"›";position:absolute;left:0;color:#54f0a6;font-weight:700}
  .rg{display:flex;align-items:center;gap:50px;margin-top:60px}
  .term{font-family:'IBM Plex Mono',monospace;font-size:36px;padding:34px 44px;border-radius:18px;
    background:#0c1311;border:1px solid #1c2a24;min-width:520px}
  .term .ln{line-height:1.9}
  .term.red{border-color:#ff6b6b}
  .term.red .ln{color:#ff6b6b}
  .term.green{border-color:#54f0a6}
  .term.green .ln{color:#54f0a6}
  .arrow{font-size:90px;color:#54f0a6}
  .lazmark{font-family:'Major Mono Display',monospace;font-size:200px;letter-spacing:6px;
    color:#eafff5}
  .lazmark .x{color:#54f0a6}
  .flow{display:flex;align-items:center;gap:30px;margin-top:60px;font-family:'IBM Plex Mono',monospace;
    font-size:34px}
  .node{padding:22px 34px;border:1px solid #2c5e49;border-radius:14px;background:#0c1311;color:#d6e0d9}
  .node.on{border-color:#54f0a6;color:#54f0a6;box-shadow:0 0 30px rgba(84,240,166,.25)}
  .sep{color:#2c5e49;font-size:44px}
  .uses{display:flex;gap:30px;margin-top:64px;flex-wrap:wrap}
  .use{flex:1;min-width:300px;text-align:center;background:#0c1311;border:1px solid #1c2a24;
    border-radius:20px;padding:54px 30px}
  .use .ic{font-size:74px}
  .use .t{font-size:38px;font-weight:700;color:#eafff5;margin-top:18px}
  .center{align-items:center;text-align:center}
  .footnote{position:absolute;bottom:60px;left:150px;font-family:'IBM Plex Mono',monospace;
    font-size:22px;color:#5f7268}
</style></head><body>"""

FOOT = "</body></html>"

COBOL_BG = ("       IDENTIFICATION DIVISION.\n       PROGRAM-ID. PAYROLL.\n"
            "       DATA DIVISION.\n       WORKING-STORAGE SECTION.\n"
            "       01 WS-GROSS-PAY  PIC 9(7)V99 COMP-3.\n"
            "       01 WS-TAX-RATE   PIC V999 VALUE 0.225.\n"
            "       PROCEDURE DIVISION.\n           COMPUTE WS-TAX ROUNDED =\n"
            "               WS-GROSS-PAY * WS-TAX-RATE.\n           DISPLAY WS-NET.\n"
            "           STOP RUN.\n") * 4

def wm():
    return '<div class="wm">&#8734; LAZARUS</div>'

SLIDES = {
"01-crisis": f"""<div class="slide center">
  <div class="code-bg">{COBOL_BG}</div>
  {wm()}<div class="tag">New Jersey · 2020</div>
  <div class="kicker amber">when COBOL fails</div>
  <h1 class="huge amber">1,600%</h1>
  <div class="sub" style="margin-top:50px;text-align:center">surge in unemployment claims — and the governor publicly
    <b>asked for volunteers who could still read COBOL.</b></div>
</div>""",

"02-scale": f"""<div class="slide">
  {wm()}<div class="tag">the legacy debt</div>
  <div class="kicker">60-year-old code still runs the world</div>
  <h1><span class="amber">$2.4&nbsp;trillion</span><br>in U.S. software tech debt.</h1>
  <div class="row">
    <div class="pill"><span class="i">&#9632;</span>banks</div>
    <div class="pill"><span class="i">&#9632;</span>benefits</div>
    <div class="pill"><span class="i">&#9632;</span>hospitals</div>
  </div>
  <div class="sub">A language almost no one speaks — with business rules <b>nobody wrote down.</b></div>
</div>""",

"03-lazarus": f"""<div class="slide center">
  <div class="kicker">introducing</div>
  <div class="lazmark">la&#8203;z<span class="x">a</span>rus</div>
  <div class="sub" style="text-align:center;font-size:52px;margin-top:30px">Raising dead code <span class="g">back to life.</span></div>
  <div class="flow" style="justify-content:center">
    <div class="node">legacy COBOL</div><span class="sep">&#8594;</span>
    <div class="node">recover business rules</div><span class="sep">&#8594;</span>
    <div class="node on">tested Python</div>
  </div>
</div>""",

"04-proof": f"""<div class="slide">
  {wm()}<div class="tag">the differentiator</div>
  <div class="kicker">it does <b style="color:#f2b657">not</b> grade its own homework</div>
  <h1 style="font-size:92px">Proven against the <span class="green">real compiler</span>,<br>byte-for-byte.</h1>
  <div class="rg">
    <div class="term red"><div class="ln">FAIL test_net_pay[1.00]</div><div class="ln">3 failed</div></div>
    <span class="arrow">&#8594;</span>
    <div class="term green"><div class="ln">PASS · PASS · PASS</div><div class="ln">EQUIVALENT</div></div>
  </div>
  <div class="footnote">differential oracle · diffs Python vs real GnuCOBOL output as ground truth</div>
</div>""",

"05-forge": f"""<div class="slide">
  {wm()}<div class="tag">self-healing</div>
  <div class="kicker">FORGE — the agent upgrades itself</div>
  <h1 style="font-size:96px">Hits an unknown idiom?<br>It <span class="green">writes its own skill.</span></h1>
  <div class="cards">
    <div class="card"><div class="lab">+ authored mid-mission</div>
      <h3>SKILL.md</h3>
      <ul><li>numeric DISPLAY format</li><li>ROUND-HALF-UP equivalence</li></ul></div>
    <div class="card"><div class="lab">then</div>
      <h3>re-reads &amp; retries</h3>
      <ul><li>same live sandbox</li><li>until the proof holds &#8594; <b style="color:#54f0a6">GREEN</b></li></ul></div>
  </div>
</div>""",

"06-google": f"""<div class="slide">
  {wm()}<div class="tag">hackathon · Google I/O 2026</div>
  <div class="kicker">built on Google's newest</div>
  <div class="cards" style="margin-top:30px">
    <div class="card"><div class="lab">model</div><h3>Gemini 3.5 Flash</h3>
      <ul><li>1M-token context — reads a 50k-line module whole</li><li>agentic: multi-step, long-horizon</li><li>frontier intelligence, fast &amp; low-cost</li></ul></div>
    <div class="card"><div class="lab">runtime</div><h3>Managed Agents API</h3>
      <ul><li>real code in a live sandbox</li><li>file persistence + auto-discovered skills</li><li>one agent — no fragile orchestration</li></ul></div>
  </div>
</div>""",

"07-uses": f"""<div class="slide center">
  <div class="kicker">where dead code still runs the world</div>
  <div class="uses">
    <div class="use"><div class="ic">&#127963;</div><div class="t">Government<br>benefits</div></div>
    <div class="use"><div class="ic">&#127974;</div><div class="t">Banking</div></div>
    <div class="use"><div class="ic">&#128737;</div><div class="t">Insurance</div></div>
    <div class="use"><div class="ic">&#129658;</div><div class="t">Healthcare<br>claims</div></div>
    <div class="use"><div class="ic">&#128209;</div><div class="t">Tax<br>systems</div></div>
  </div>
</div>""",

"08-close": f"""<div class="slide center">
  <div class="lazmark" style="font-size:240px">la&#8203;z<span class="x">a</span>rus</div>
  <div class="sub" style="text-align:center;font-size:54px;margin-top:24px">Proven, autonomous modernization.</div>
  <div class="sub" style="text-align:center;font-size:34px;color:#5f7268;margin-top:18px">COBOL &#8594; tested Python · verified against the real compiler</div>
</div>""",
}

for name, body in SLIDES.items():
    (OUT / f"{name}.html").write_text(HEAD + body + FOOT, encoding="utf-8")
print(f"wrote {len(SLIDES)} slides to {OUT}")
