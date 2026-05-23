// live.js — REAL end-to-end SSE client. The ONLY data source for the UI; there
// is no scripted/mock path. Bridges the FastAPI backend (src/server.py) to a
// LivePlayer: subscribe to the agent's event-stream, push canonical Events into
// the renderer as they arrive, surface real errors (never fake data).
//
// Backend emits CANONICAL Event JSON per SSE line (web/STREAM_CONTRACT.md):
// phase | step | business_rule | diff | oracle | pytest | forge | reload |
// download | done | error. The UI does zero transform.
//
// CONTRACT AUTO-DETECTION — the backend is mid-reconcile between two shapes, so
// this client supports BOTH and picks whichever the running server offers:
//   (A) GET-direct:  GET {base}/api/migrate?module=<name>   -> text/event-stream
//                    (current src/server.py)
//   (B) POST+run_id: POST {base}/api/migrate {cobol,filename} -> { run_id }
//                    then GET {base}/api/stream/{run_id}      -> text/event-stream
//                    (shape in tests/test_server.py)
// It tries (B) first (POST); if the server doesn't speak it, falls back to (A).
//
// Download: canonical mode delivers the migrated module INLINE in the `download`
// event ({name,mime,content}); contract (B) may instead expose
// GET /api/download/{run_id}. The renderer handles both (url or content).

import { LivePlayer } from './player.js';

export const ENDPOINTS = {
  base: '',                                            // same-origin (server serves web/ at /)
  health: (b) => `${b}/api/health`,
  migrate: (b) => `${b}/api/migrate`,
  migrateGet: (b, module) => `${b}/api/migrate?module=${encodeURIComponent(module)}`,
  stream: (b, id) => `${b}/api/stream/${id}`,
  download: (b, id) => `${b}/api/download/${id}`,
};

/** Create a LivePlayer. Caller MUST attach the renderer + reset BEFORE driving,
 *  so the first pushed event (including a fatal error) renders. */
export function createLivePlayer(meta = {}) {
  return new LivePlayer(meta);
}

/** Probe the backend; returns { ok, keyPresent, info } or { ok:false }. */
export async function checkHealth(base = ENDPOINTS.base) {
  try {
    const res = await fetch(ENDPOINTS.health(base), { cache: 'no-store' });
    if (!res.ok) return { ok: false };
    const info = await res.json();
    return { ok: true, keyPresent: !!info.gemini_api_key_present, info };
  } catch {
    return { ok: false };
  }
}

const errStep = (title, text) => ({
  type: 'step', kind: 'status', status: 'error', title, text,
});

/**
 * Drive the real migration on an already-attached player. Pushes canonical
 * Events as they stream; pushes an error step on any failure (no fake data).
 * @param {LivePlayer} player
 * @param {string} cobol      - source text (used by contract B)
 * @param {string} filename   - e.g. "payroll.cob" (module name for contract A)
 * @param {object} opts       - { base }
 * @returns {Promise<{ runId, abort }>}
 */
export async function driveLiveRun(player, cobol, filename, opts = {}) {
  const base = opts.base ?? ENDPOINTS.base;
  const moduleName = filename || 'payroll.cob';

  // --- Try contract (B): POST -> run_id ------------------------------------
  let runId = null;
  let postSupported = true;
  try {
    const res = await fetch(ENDPOINTS.migrate(base), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cobol, filename: moduleName }),
    });
    if (res.status === 405 || res.status === 501) {
      postSupported = false;                       // server is GET-direct only
    } else if (res.status === 503) {
      const body = await res.json().catch(() => ({}));
      player.push(errStep('no API key',
        `${body.error || 'GEMINI_API_KEY not set'}. ${body.hint || 'Provision the key, then re-run.'}`));
      return { runId: null, abort: () => {} };
    } else if (!res.ok) {
      // POST exists but errored for another reason — report it, don't fall back blindly.
      const body = await res.text().catch(() => '');
      player.push(errStep(`backend error ${res.status}`, body.slice(0, 300) || 'POST /api/migrate failed.'));
      return { runId: null, abort: () => {} };
    } else {
      const data = await res.json().catch(() => ({}));
      runId = data.run_id || data.runId || data.id || null;
      if (!runId) postSupported = false;           // 200 but no run_id -> treat as GET-direct
    }
  } catch (err) {
    // Network failure → backend likely down. One health probe to give a precise message.
    const h = await checkHealth(base);
    if (!h.ok) {
      player.push(errStep('backend unreachable',
        `Cannot reach the LAZARUS server at ${base || location.origin}. ` +
        `Start it:  uvicorn server:app --app-dir src  (then reload).`));
      return { runId: null, abort: () => {} };
    }
    postSupported = false;                          // server up but POST failed → try GET-direct
  }

  // --- Subscribe to the SSE stream -----------------------------------------
  const useGetDirect = !(postSupported && runId);

  // GET-direct (contract A) returns the SSE stream OR a 503 JSON when there's no
  // key. EventSource can't read a 503 body — it just fires onerror opaquely — so
  // probe health first and surface the precise no-key error instead.
  if (useGetDirect) {
    const h = await checkHealth(base);
    if (h.ok && !h.keyPresent) {
      player.push(errStep('no API key',
        'GEMINI_API_KEY not set on the server. Provision the key (export GEMINI_API_KEY=…), then re-run.'));
      return { runId: null, abort: () => {} };
    }
    if (!h.ok) {
      player.push(errStep('backend unreachable',
        `Cannot reach the LAZARUS server at ${base || location.origin}. ` +
        `Start it:  uvicorn server:app --app-dir src  (then reload).`));
      return { runId: null, abort: () => {} };
    }
  }

  const streamUrl = useGetDirect
    ? ENDPOINTS.migrateGet(base, moduleName)        // contract A (GET-direct)
    : ENDPOINTS.stream(base, runId);                // contract B
  const es = new EventSource(streamUrl);
  let done = false;

  es.onmessage = (e) => {
    let payload;
    try { payload = JSON.parse(e.data); } catch { return; }
    if (!payload || !payload.type) return;
    if (payload.type === 'error') {
      player.push(errStep('agent error', payload.message || payload.error || 'stream error'));
      done = true; es.close(); return;
    }
    // Live download via contract B: rewrite to a real URL if no inline content.
    if (payload.type === 'download' && payload.content == null && runId) {
      player.push({ type: 'download', name: payload.name || moduleName.replace(/\.cob$/, '.py'),
                    url: ENDPOINTS.download(base, runId) });
      return;
    }
    player.push(payload);
    if (payload.type === 'done') { done = true; es.close(); }
  };

  es.onerror = () => {
    if (es.readyState === EventSource.CLOSED && !done) {
      player.push(errStep('stream closed',
        'The event stream closed before completion. Check the server logs.'));
    }
  };

  return { runId, abort: () => es.close() };
}
