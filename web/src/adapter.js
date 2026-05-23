// adapter.js — the ONLY file that knows real Managed Agents API field names.
//
// The renderer consumes the canonical Event shape defined in STREAM_CONTRACT.md.
// The mock run is already in canonical shape, so it passes through untouched.
// The live API emits a different shape; everything API-specific lives here.
//
// VERIFIED API SHAPE (researcher-agents, sources: ai.google.dev interactions
// API reference + quickstart):
//
//   Streaming events carry `event.event_type`, one of:
//     step.start | step.delta | step.stop | interaction.created |
//     interaction.completed | interaction.status_update | error
//
//   On step.start / step.stop:  event.step  is a full Step object.
//   On step.delta:              event.delta = { type:"text"|..., text:"..." }
//
//   Step object types (event.step.type):
//     user_input             → { content:[{type:"text", text}] }
//     thought                → { summary:[{type:"text", text}], signature }
//     code_execution_call    → { id, arguments:{ code, language }, signature }
//     code_execution_result  → { call_id, result, is_error, signature }
//     model_output           → { content:[{type:"text", text}] }
//
// ⚠️ TWO API CAVEATS (researcher-agents, reconciled against the cookbook):
//   1. The live trace is a 3-event LIFECYCLE per step: step.start opens a card,
//      step.delta streams text into it (event.delta.text), step.stop finalizes
//      it. The step.stop step object may NOT carry the full streamed text, so we
//      accumulate deltas ourselves (see StreamAdapter) rather than reading text
//      off step.stop alone.
//   2. interaction.completed arrives "with empty outputs to reduce payload" —
//      do NOT rely on it for final text/steps. We already have everything from
//      the step.* stream; for the authoritative final object (environment_id,
//      full steps) the orchestrator calls client.interactions.get(id).
//
// To go live: drive the renderer with a StreamAdapter — feed each SSE event to
// .ingest(event) and push the returned canonical Events into a LivePlayer.
// Nothing in renderer/style/html changes.

// --- Step.type → canonical kind --------------------------------------------
const STEP_TYPE_KIND = {
  user_input: 'status',
  thought: 'thought',
  code_execution_call: 'code',
  code_execution_result: 'output',
  model_output: 'output',
  // present in the API but our Antigravity agent won't emit these:
  function_call: 'tool_call',
  function_result: 'output',
};

/** Pull display text out of a Step's varied nested shapes. */
function stepText(step) {
  if (!step) return '';
  // content[] and summary[] are arrays of {type, text}; join the text parts.
  const parts = step.content || step.summary;
  if (Array.isArray(parts)) {
    return parts.filter((p) => p && p.type === 'text').map((p) => p.text).join('');
  }
  if (step.type === 'code_execution_call') return (step.arguments && step.arguments.code) || '';
  if (step.type === 'code_execution_result') {
    const r = step.result;
    return typeof r === 'string' ? r : (r == null ? '' : JSON.stringify(r, null, 2));
  }
  if (typeof step.text === 'string') return step.text;
  return '';
}

/**
 * Map one full Step object (from step.start / step.stop) to a canonical Event.
 * Defensive: unknown shapes degrade to a generic status step rather than throw.
 * @param {object} step - event.step from the live stream
 * @returns {object|null}
 */
export function adaptStep(step) {
  if (!step || typeof step !== 'object') return null;
  const kind = STEP_TYPE_KIND[step.type] || 'status';

  const ev = { type: 'step', kind, text: stepText(step) };

  if (step.type === 'code_execution_call') {
    ev.tool = 'code_execution';
    ev.title = 'code execution';
    if (step.arguments && step.arguments.language) ev.lang = step.arguments.language;
  } else if (step.type === 'code_execution_result') {
    ev.lang = 'bash';
    ev.status = step.is_error ? 'error' : 'ok';
  } else if (step.type === 'thought') {
    ev.title = 'reasoning';
  }
  return ev;
}

/**
 * Stateful driver for the live step.* lifecycle. The renderer renders one
 * finalized card per step, so this accumulates step.delta text against the
 * currently-open step (keyed by event.index) and emits the canonical Event on
 * step.stop, preferring the accumulated text over what step.stop may omit.
 *
 * Usage:
 *   const sa = new StreamAdapter();
 *   for await (const event of sseStream) {
 *     for (const ev of sa.ingest(event)) livePlayer.push(ev);
 *   }
 */
export class StreamAdapter {
  constructor() {
    this.open = new Map();   // index -> { step, text }
  }

  /**
   * Feed one SSE event; returns an array of canonical Events to emit (0..n).
   * @param {object} event - one SSE event with event.event_type
   * @returns {object[]}
   */
  ingest(event) {
    if (!event || typeof event !== 'object') return [];
    switch (event.event_type) {
      case 'step.start':
        this.open.set(event.index, { step: event.step || {}, text: '' });
        return [];
      case 'step.delta': {
        const slot = this.open.get(event.index);
        const piece = event.delta && event.delta.type === 'text' ? (event.delta.text || '') : '';
        if (slot) slot.text += piece;
        return [];
      }
      case 'step.stop': {
        const slot = this.open.get(event.index);
        this.open.delete(event.index);
        // Merge the final step object with the accumulated streamed text.
        const step = event.step || (slot && slot.step) || {};
        const ev = adaptStep(step);
        if (!ev) return [];
        const accumulated = slot && slot.text;
        if (accumulated && !ev.text) ev.text = accumulated;     // step.stop omitted text
        return [ev];
      }
      case 'interaction.completed':
        // Empty-payload event; we already emitted everything from the stream.
        return [{ type: 'done', verdict: 'COMPLETE', summary: '' }];
      case 'error':
        return [{ type: 'step', kind: 'status', status: 'error', title: 'error',
                  text: (event.error && event.error.message) || 'stream error' }];
      case 'interaction.created':
      case 'interaction.status_update':
      default:
        return [];
    }
  }
}

/**
 * Stateless convenience: map one SSE event to a single canonical Event (or
 * null). Surfaces the full step on step.stop; ignores start/delta lifecycle
 * markers (use StreamAdapter for proper delta accumulation).
 * @param {object} event - one SSE event with event.event_type
 * @returns {object|null}
 */
export function adaptStreamEvent(event) {
  if (!event || typeof event !== 'object') return null;
  switch (event.event_type) {
    case 'step.stop':
      return adaptStep(event.step);
    case 'interaction.completed':
      return { type: 'done', verdict: 'COMPLETE', summary: '' };
    case 'error':
      return { type: 'step', kind: 'status', status: 'error',
               title: 'error', text: (event.error && event.error.message) || 'stream error' };
    case 'step.start':
    case 'step.delta':
    case 'interaction.created':
    case 'interaction.status_update':
    default:
      return null;
  }
}

/**
 * Back-compat for a non-streamed payload that exposes a `steps` array.
 * @param {object} raw - a single element of an interaction `steps` array
 * @returns {object|null}
 */
export function adaptInteractionStep(raw) {
  return adaptStep(raw);
}

/**
 * Normalize a whole run. Mock runs (canonical events) pass through; a raw API
 * payload is adapted via its steps. Keeps the player agnostic to the source.
 * @param {object} run - either { version, meta, events } or a raw API response
 * @returns {{ meta: object, events: object[] }}
 */
export function normalizeRun(run) {
  if (run && Array.isArray(run.events)) {
    return { meta: run.meta || {}, events: run.events };  // canonical (the mock)
  }
  const steps =
    (run && run.interaction && run.interaction.steps) ||
    (run && run.steps) ||
    [];
  const events = [];
  for (const s of steps) {
    const adapted = adaptStep(s);
    if (adapted) events.push(adapted);
  }
  return { meta: (run && run.meta) || {}, events };
}
