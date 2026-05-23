// renderer.js — turns canonical Events into DOM updates across all panels.
// Subscribes to a player's bus; knows nothing about mock vs live.

import { highlight } from './highlight.js';

const PHASES = [
  ['ingest', 'INGEST'],
  ['recover', 'RECOVER'],
  ['translate', 'TRANSLATE'],
  ['oracle', 'ORACLE'],
  ['test', 'TEST'],
  ['diagnose', 'DIAGNOSE'],
  ['forge', 'FORGE'],
  ['reload', 'RELOAD'],
  ['verify', 'VERIFY'],
  ['done', 'DONE'],
];

const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};
const escapeText = (s) => (s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export class Renderer {
  constructor(root = document) {
    this.root = root;
    this.refs = {
      rail: $('#phase-rail', root),
      trace: $('#trace-stream', root),
      rules: $('#rules-list', root),
      ruleCount: $('#rules-count', root),
      diffLeft: $('#diff-left', root),
      diffRight: $('#diff-right', root),
      diffLeftName: $('#diff-left-name', root),
      diffRightName: $('#diff-right-name', root),
      term: $('#pytest-body', root),
      termVerdict: $('#pytest-verdict', root),
      forge: $('#forge-body', root),
      forgeReason: $('#forge-reason', root),
      iterCounter: $('#iter-counter', root),
      iterCap: $('#iter-cap', root),
      downloadBtn: $('#download-btn', root),
      oracleBanner: $('#oracle-banner', root),
      verdictBadge: $('#verdict-badge', root),
      stage: $('#stage', root),
      // progressive-reveal scaffolding
      flow: $('#flow', root),
      flowIdle: $('#flow-idle', root),
      working: $('#working', root),
      workingPhase: $('#working-phase', root),
      workingAction: $('#working-action', root),
      workingIter: $('#working-iter', root),
      workingReassure: $('#working-reassure', root),
      workingElapsed: $('#working-elapsed', root),
      workingElapsedTime: $('#working-elapsed-time', root),
    };
    this.artifact = null;
    // live heartbeat: an always-advancing elapsed timer so a long, silent
    // tool-execution stretch never reads as frozen. See _startHeartbeat.
    this._hbInterval = null;   // setInterval id
    this._hbStart = 0;         // run start (ms)
    this._lastActionAt = 0;    // when the action line last changed (ms)
  }

  // --- progressive reveal helpers -----------------------------------------
  // Map a phase key to the card it should emphasize. Several phases share a
  // card (e.g. oracle/diagnose surface in the proof card); these mark the
  // active beat so the right card glows, without revealing empty cards.
  static PHASE_CARD = {
    recover: 'recover', translate: 'translate', oracle: 'test', test: 'test',
    diagnose: 'test', forge: 'forge', reload: 'forge',
  };

  /** Reveal a step card (it now has real data) and accumulate it in the flow. */
  _revealCard(when) {
    const card = $(`.card[data-when="${when}"]`, this.root);
    if (card && !card.classList.contains('has-data')) {
      card.classList.add('has-data');
      requestAnimationFrame(() => card.classList.add('in'));
    }
    if (this.refs.flowIdle) this.refs.flowIdle.classList.add('gone');
  }

  /** Emphasize the card for the current phase; quiet the others. */
  _setActiveCard(phase) {
    const want = Renderer.PHASE_CARD[phase] || null;
    for (const card of this.refs.flow.querySelectorAll('.card')) {
      card.classList.toggle('active', card.dataset.when === want);
    }
  }

  /** Update the persistent WORKING banner (current phase + latest action).
   *  The banner already says "agent working", so retire the idle placeholder
   *  once it's up — but keep any revealed cards. Never a blank screen. */
  _setWorking({ phase, action, iteration } = {}) {
    const r = this.refs;
    if (!r.working) return;
    r.working.hidden = false;
    if (r.flowIdle) r.flowIdle.classList.add('gone');
    // first time the banner shows in this run → start the always-advancing clock
    if (!this._hbInterval) this._startHeartbeat();
    if (phase != null) r.workingPhase.textContent = phase;
    if (action != null) {
      r.workingAction.textContent = action;
      this._lastActionAt = Date.now();   // fresh agent activity → reset the quiet timer
      if (r.workingReassure) r.workingReassure.hidden = true;
    }
    if (iteration != null) r.workingIter.textContent = iteration ? `iter ${iteration}` : '';
  }

  /** Stop the WORKING banner (run finished or errored). */
  _stopWorking() {
    this._stopHeartbeat();
    if (this.refs.working) this.refs.working.hidden = true;
    this._setActiveCard(null);
  }

  // --- live heartbeat ------------------------------------------------------
  // agent.py only forwards step.delta text; during multi-minute tool stretches
  // (conda install / compile / pytest) no text arrives, so the action line +
  // rail sit static. The elapsed timer below ALWAYS advances, and after a quiet
  // stretch a calm reassurance line appears — so a live run never reads as
  // frozen. Pure clock; no API dependency.
  _QUIET_MS = 6000;   // action line silent this long → show reassurance

  _fmtElapsed(ms) {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    return `${m}:${String(s % 60).padStart(2, '0')}`;
  }

  _startHeartbeat() {
    const r = this.refs;
    if (!r.workingElapsed) return;
    this._hbStart = Date.now();
    this._lastActionAt = this._hbStart;
    r.workingElapsed.hidden = false;
    r.workingElapsedTime.textContent = '0:00';
    if (this._hbInterval) clearInterval(this._hbInterval);
    this._hbInterval = setInterval(() => this._tickHeartbeat(), 1000);
  }

  _tickHeartbeat() {
    const r = this.refs;
    const now = Date.now();
    r.workingElapsedTime.textContent = this._fmtElapsed(now - this._hbStart);
    // reveal the reassurance line once the agent has been quiet for a while
    if (r.workingReassure && now - this._lastActionAt > this._QUIET_MS) {
      r.workingReassure.hidden = false;
    }
  }

  _stopHeartbeat() {
    if (this._hbInterval) { clearInterval(this._hbInterval); this._hbInterval = null; }
    const r = this.refs;
    if (r.workingElapsed) r.workingElapsed.hidden = true;
    if (r.workingReassure) r.workingReassure.hidden = true;
  }

  /** Surface a fatal error front-and-center in the flow so the main area is
   *  never blank — even if it arrives before any panel got data. */
  _showFlowError(title, text) {
    const r = this.refs;
    if (!r.flowIdle) return;
    const hasCards = r.flow.querySelector('.card.has-data');
    if (hasCards) return;   // cards already tell the story; the trace shows the error
    r.flowIdle.classList.remove('gone', 'is-error');
    r.flowIdle.classList.add('is-error');
    r.flowIdle.innerHTML =
      `<div class="flow-error">` +
      `<div class="flow-error-title">${escapeText(title || 'run failed')}</div>` +
      (text ? `<div class="flow-error-text">${escapeText(text)}</div>` : '') +
      `</div>`;
  }

  /** Wire to a player; returns an unsubscribe fn. */
  attach(player) {
    const offs = [
      player.on('reset', (p) => this.reset(p.meta)),
      player.on('event', (ev) => this.handle(ev)),
    ];
    return () => offs.forEach((f) => f());
  }

  reset(meta = {}) {
    if (this._forgeTimer) {
      clearTimeout(this._forgeTimer);
      this._forgeTimer = null;
    }
    const r = this.refs;
    r.trace.innerHTML = '';
    r.rules.innerHTML = '';
    r.ruleCount.textContent = '0';
    r.diffLeft.innerHTML = '';
    r.diffRight.innerHTML = '';
    r.diffLeftName.textContent = '—';
    r.diffRightName.textContent = '—';
    r.term.innerHTML = '<div class="term-idle">$ awaiting equivalence run…</div>';
    r.termVerdict.textContent = '';
    r.termVerdict.className = 'term-verdict';
    r.forge.innerHTML = '<div class="forge-idle">no skill forged yet — agent uses only its seed skills</div>';
    r.forgeReason.textContent = '';
    r.iterCounter.textContent = '0';
    r.iterCap.textContent = meta.iteration_cap ?? '4';
    r.downloadBtn.setAttribute('disabled', '');
    r.downloadBtn.classList.remove('ready');
    r.oracleBanner.classList.remove('show');
    r.verdictBadge.classList.remove('show', 'good');
    r.verdictBadge.textContent = '';
    r.stage.dataset.phase = '';
    this.artifact = null;
    // reset progressive reveal: hide every card until it has real data
    for (const card of r.flow.querySelectorAll('.card')) {
      card.classList.remove('has-data', 'in', 'active', 'pulse-green', 'pulse-red', 'forging', 'reloaded');
    }
    if (r.flowIdle) {
      r.flowIdle.classList.remove('gone', 'is-error');
      r.flowIdle.innerHTML =
        '<span class="spinner" aria-hidden="true"></span>' +
        '<span>Agent waking up in a live sandbox…</span>';
    }
    // stop any prior heartbeat so a re-run starts a fresh clock from 0:00
    this._stopHeartbeat();
    if (r.working) {
      r.working.hidden = true;
      r.workingPhase.textContent = 'working…';
      r.workingAction.textContent = '';
      r.workingIter.textContent = '';
      if (r.workingElapsedTime) r.workingElapsedTime.textContent = '0:00';
    }
    this._buildRail();
  }

  _buildRail() {
    const r = this.refs;
    r.rail.innerHTML = '';
    for (const [key, label] of PHASES) {
      const node = el('div', 'rail-step', `<span class="rail-dot"></span><span class="rail-label">${label}</span>`);
      node.dataset.phase = key;
      r.rail.appendChild(node);
    }
  }

  handle(ev) {
    const fn = this['on_' + ev.type];
    if (fn) fn.call(this, ev);
  }

  // --- phase rail ----------------------------------------------------------
  on_phase(ev) {
    const r = this.refs;
    r.stage.dataset.phase = ev.phase;
    let active = false;
    for (const node of r.rail.children) {
      if (node.dataset.phase === ev.phase) {
        node.classList.add('active');
        node.classList.remove('past');
        active = true;
      } else if (!active) {
        node.classList.add('past');
        node.classList.remove('active');
      } else {
        node.classList.remove('active', 'past');
      }
    }
    if (ev.iteration != null) r.iterCounter.textContent = ev.iteration;
    // progressive reveal: emphasize the card for this phase + drive the WORKING banner
    this._setActiveCard(ev.phase);
    this._setWorking({ phase: ev.label || ev.phase, iteration: ev.iteration });
  }

  // --- (b) agent-working trace --------------------------------------------
  on_step(ev) {
    const r = this.refs;
    const card = el('div', `trace-card kind-${ev.kind}`);
    const head = el('div', 'trace-head');
    head.appendChild(el('span', 'trace-kind', ev.kind.replace('_', ' ')));
    if (ev.tool) head.appendChild(el('span', 'trace-tool', escapeText(ev.tool)));
    if (ev.title) head.appendChild(el('span', 'trace-title', escapeText(ev.title)));
    if (ev.status) head.appendChild(el('span', `trace-status st-${ev.status}`, ev.status));
    if (ev.duration_ms != null) head.appendChild(el('span', 'trace-dur', `${ev.duration_ms}ms`));
    card.appendChild(head);

    if (ev.text) {
      if (ev.kind === 'code' || ev.kind === 'output' || ev.kind === 'tool_call') {
        const lang = ev.lang || (ev.kind === 'output' ? 'bash' : '');
        const pre = el('pre', 'trace-code');
        pre.innerHTML = highlight(ev.text, lang);
        card.appendChild(pre);
      } else {
        card.appendChild(el('div', 'trace-text', escapeText(ev.text)));
      }
    }
    r.trace.appendChild(card);
    requestAnimationFrame(() => card.classList.add('in'));
    r.trace.scrollTop = r.trace.scrollHeight;

    // surface the latest agent action in the WORKING banner so a long live
    // run never looks frozen. A fatal error step stops the banner instead.
    if (ev.status === 'error') {
      this._stopWorking();
      this._showFlowError(ev.title, ev.text);
    } else {
      const line = ev.title || ev.text || '';
      this._setWorking({ action: line.length > 120 ? line.slice(0, 117) + '…' : line });
    }
  }

  // --- (c) business rules --------------------------------------------------
  on_business_rule(ev) {
    const r = this.refs;
    const card = el('div', `rule-card sev-${ev.severity || 'rule'}`);
    card.innerHTML = `
      <div class="rule-head">
        <span class="rule-sev">${(ev.severity || 'rule').replace('_', ' ')}</span>
        <span class="rule-title">${escapeText(ev.title)}</span>
      </div>
      <div class="rule-plain">${escapeText(ev.plain)}</div>
      <code class="rule-ref">${escapeText(ev.cobol_ref)}</code>`;
    r.rules.appendChild(card);
    requestAnimationFrame(() => card.classList.add('in'));
    r.ruleCount.textContent = r.rules.children.length;
    this._revealCard('recover');
  }

  // --- (d) diff viewer -----------------------------------------------------
  on_diff(ev) {
    const r = this.refs;
    this._revealCard('translate');
    this._renderSide(r.diffLeft, r.diffLeftName, ev.left, ev.links, 'left');
    this._renderSide(r.diffRight, r.diffRightName, ev.right, ev.links, 'right');
    // flash to signal an update (re-translation after forge)
    r.diffRight.parentElement.classList.remove('flash');
    void r.diffRight.parentElement.offsetWidth;
    r.diffRight.parentElement.classList.add('flash');
  }

  _renderSide(container, nameEl, side, links, which) {
    if (!side) return;
    nameEl.textContent = side.name || '';
    const lines = (side.code || '').split('\n');
    const hi = new Map();
    for (const link of links || []) {
      const range = link[which];
      if (!range) continue;
      for (let i = range[0]; i <= range[1]; i++) hi.set(i, link.kind || 'rule');
    }
    container.innerHTML = '';
    lines.forEach((line, i) => {
      const ln = i + 1;
      const row = el('div', 'code-line');
      if (hi.has(ln)) row.classList.add('hl', `hl-${hi.get(ln)}`);
      row.innerHTML =
        `<span class="gutter">${ln}</span>` +
        `<span class="src">${highlight(line, side.lang) || '&nbsp;'}</span>`;
      container.appendChild(row);
    });
  }

  // --- (e) pytest terminal -------------------------------------------------
  on_pytest(ev) {
    const r = this.refs;
    this._revealCard('test');
    if (ev.result === 'running') {
      r.term.innerHTML =
        `<div class="term-line">$ pytest -q test_equivalence.py  <span class="term-iter">[iter ${ev.iteration}]</span></div>` +
        `<div class="term-line dim">collecting ▍</div>`;
      r.termVerdict.textContent = 'RUNNING';
      r.termVerdict.className = 'term-verdict running';
      return;
    }

    const isGreen = ev.result === 'green';
    const frag = document.createDocumentFragment();
    frag.appendChild(el('div', 'term-line', `$ pytest -q test_equivalence.py  <span class="term-iter">[iter ${ev.iteration}]</span>`));

    for (const c of ev.cases || []) {
      const pass = c.status === 'pass';
      const row = el('div', `term-case ${pass ? 'pass' : 'fail'}`);
      row.innerHTML =
        `<span class="case-mark">${pass ? 'PASS' : 'FAIL'}</span>` +
        `<span class="case-name">${escapeText(c.name)}</span>`;
      frag.appendChild(row);
      if (!pass && (c.cobol != null || c.python != null)) {
        const diff = el('div', 'case-diff');
        diff.innerHTML =
          `<div class="case-oracle"><span class="lbl">cobol oracle</span><code>${escapeText(c.cobol)}</code></div>` +
          `<div class="case-py"><span class="lbl">python out</span><code>${escapeText(c.python)}</code></div>` +
          (c.message ? `<div class="case-msg">${escapeText(c.message)}</div>` : '');
        frag.appendChild(diff);
      }
    }
    frag.appendChild(el('div', `term-summary ${isGreen ? 'green' : 'red'}`, escapeText(ev.summary || '')));

    r.term.innerHTML = '';
    r.term.appendChild(frag);
    r.term.scrollTop = r.term.scrollHeight;

    r.termVerdict.textContent = isGreen ? 'GREEN' : 'RED';
    r.termVerdict.className = `term-verdict ${isGreen ? 'green' : 'red'}`;
    // dramatic full-panel pulse on RED→GREEN transitions
    r.term.closest('.panel').classList.remove('pulse-red', 'pulse-green');
    void r.term.offsetWidth;
    r.term.closest('.panel').classList.add(isGreen ? 'pulse-green' : 'pulse-red');
  }

  // --- (the oracle money-shot banner) -------------------------------------
  on_oracle(ev) {
    const r = this.refs;
    this._revealCard('test');
    r.oracleBanner.innerHTML =
      `<span class="oracle-tag">DIFFERENTIAL ORACLE</span>` +
      `<span class="oracle-text">Ground truth = <strong>${escapeText(ev.compiler)}</strong> running the original COBOL · ` +
      `${(ev.inputs || []).length} canonical inputs</span>`;
    r.oracleBanner.classList.add('show');
  }

  // --- (f) forge / git-diff -----------------------------------------------
  on_step_status() {} // placeholder; status steps already handled by on_step

  on_forge(ev) {
    const r = this.refs;
    this._revealCard('forge');
    r.forgeReason.textContent = ev.reason || '';
    r.forge.innerHTML = '';

    const header = el('div', 'forge-file');
    header.innerHTML =
      `<span class="git-stat git-${ev.git.status}">${ev.git.status}</span>` +
      `<span class="forge-path">${escapeText(ev.skill)}</span>`;
    r.forge.appendChild(header);

    const diff = el('div', 'forge-diff');
    r.forge.appendChild(diff);

    // Type the additions in line-by-line for the "writing itself" effect.
    const lines = ev.git.additions || [];
    
    // If seeking, render the code block synchronously to keep seeks snappy and free of timer leaks
    if (ev._seeking) {
      for (const line of lines) {
        const row = el('div', 'diff-add in', `<span class="diff-sign">+</span><span>${escapeText(line) || '&nbsp;'}</span>`);
        diff.appendChild(row);
      }
      const commit = el('div', 'forge-commit in', `✓ ${escapeText(ev.git.commit)}`);
      r.forge.appendChild(commit);
      diff.scrollTop = diff.scrollHeight;
      return;
    }

    let i = 0;
    const step = () => {
      if (i >= lines.length) {
        const commit = el('div', 'forge-commit', `✓ ${escapeText(ev.git.commit)}`);
        r.forge.appendChild(commit);
        requestAnimationFrame(() => commit.classList.add('in'));
        return;
      }
      const row = el('div', 'diff-add', `<span class="diff-sign">+</span><span>${escapeText(lines[i]) || '&nbsp;'}</span>`);
      diff.appendChild(row);
      requestAnimationFrame(() => row.classList.add('in'));
      diff.scrollTop = diff.scrollHeight;
      i++;
      this._forgeTimer = setTimeout(step, 70);
    };
    step();
    r.forge.closest('.panel').classList.add('forging');
  }

  on_reload(ev) {
    const r = this.refs;
    r.forge.closest('.panel').classList.remove('forging');
    r.forge.closest('.panel').classList.add('reloaded');
    const note = el('div', 'forge-reload', `↻ ${escapeText(ev.label)}`);
    r.forge.appendChild(note);
    requestAnimationFrame(() => note.classList.add('in'));
  }

  // --- (g) download --------------------------------------------------------
  on_download(ev) {
    const r = this.refs;
    this.artifact = ev;   // may carry inline {content} (mock) or {url} (live)
    r.downloadBtn.removeAttribute('disabled');
    r.downloadBtn.classList.add('ready');
  }

  /** Live mode: point the download button at a real backend URL. */
  setDownloadUrl(url, name) {
    if (!url) return;
    this.artifact = { url, name: name || 'payroll.py' };
  }

  on_done(ev) {
    const r = this.refs;
    r.verdictBadge.textContent = ev.verdict || 'EQUIVALENT';
    r.verdictBadge.classList.add('show', 'good');
    r.stage.dataset.phase = 'done';
    // run finished: drop the WORKING banner; let every revealed card rest equally.
    this._stopWorking();
    // mark whole rail complete
    for (const node of r.rail.children) {
      node.classList.add('past');
      node.classList.remove('active');
    }
  }

  /** Trigger a browser download of the migrated artifact.
   *  Live: a real backend URL (pulled from the persistent sandbox).
   *  Fallback: an inline blob from the event content. */
  triggerDownload() {
    if (!this.artifact) return;
    const a = document.createElement('a');
    let revoke = null;
    if (this.artifact.url) {
      a.href = this.artifact.url;          // real file from the backend
    } else if (this.artifact.content != null) {
      const blob = new Blob([this.artifact.content], { type: this.artifact.mime || 'text/plain' });
      a.href = URL.createObjectURL(blob);
      revoke = a.href;
    } else {
      return;
    }
    a.download = this.artifact.name || 'payroll.py';
    document.body.appendChild(a);
    a.click();
    a.remove();
    if (revoke) setTimeout(() => URL.revokeObjectURL(revoke), 1000);
  }
}
