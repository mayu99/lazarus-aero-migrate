// player.js — forwards canonical events to the renderer.
//
// LivePlayer pushes events as they arrive from the real SSE stream (live.js).
// There is no scripted/timeline player — the UI runs only against the live
// backend (task #9).

/** Tiny event bus: on(type, cb) / emit(type, payload). '*' subscribes to all. */
function makeBus() {
  const handlers = new Map();
  return {
    on(type, cb) {
      if (!handlers.has(type)) handlers.set(type, new Set());
      handlers.get(type).add(cb);
      return () => handlers.get(type).delete(cb);
    },
    emit(type, payload) {
      (handlers.get(type) || []).forEach((cb) => cb(payload));
      (handlers.get('*') || []).forEach((cb) => cb(type, payload));
    },
  };
}

export class LivePlayer {
  /** @param {object} meta - run metadata (module, iteration_cap, …) */
  constructor(meta = {}) {
    this.meta = meta;
    this.bus = makeBus();
    this.events = [];
  }
  on(type, cb) { return this.bus.on(type, cb); }
  /** Feed one canonical Event into the renderer. */
  push(ev) {
    this.events.push(ev);
    this.bus.emit('event', ev);
  }
  reset() {
    this.events = [];
    this.bus.emit('reset', { meta: this.meta });
  }
  /** Synchronously replay events up to index for state scrubbing */
  seek(index) {
    this.bus.emit('reset', { meta: this.meta });
    const subset = this.events.slice(0, index + 1);
    // Suppress any delayed typewriter animations or visual offsets by replaying immediately
    for (const ev of subset) {
      this.bus.emit('event', { ...ev, _seeking: true });
    }
  }
}
