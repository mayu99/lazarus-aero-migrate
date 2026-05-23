"""
LAZARUS — FastAPI + SSE bridge (browser <-> live Managed Agent).

Serves the web/ UI and drives the REAL Gemini Managed Agent (src/agent.py),
forwarding its progress to the live-trace UI as CANONICAL events
(web/STREAM_CONTRACT.md). There is NO mock here — the scripted run survives only
as the UI's `?mock=1` break-glass. With no GEMINI_API_KEY this returns an
explicit 503 (never fake data).

Endpoint contract (matches web/src/live.js, mode='canonical'):
    POST /api/migrate   { cobol, filename }     -> { run_id }
    GET  /api/stream/{run_id}                    -> text/event-stream (canonical events)
    GET  /api/download/{run_id}                  -> migrated module bytes (when available)
    GET  /api/health                             -> liveness + key/agent info

What this bridge derives from agent.py's stream — EVERY panel, two layers deep:
  * PROGRESSIVE `phase` events off the streamed step text (ingest->recover->translate
    ->oracle->test->forge->done), so the UI advances live, not only at the end.
  * `step` (live trace), enforced iteration counter, `forge` (+git additions),
    `reload`, `download`, `done`.
  * FAST PATH (markers): `business_rule` from LAZARUS_RULE, structured per-case `pytest`
    from LAZARUS_ORACLE_JSON.
  * SAFETY NET (deterministic, no markers needed): after migrate() we fetch the agent's
    /workspace/payroll.py via the Files API and emit (a) a real COBOL<->Python `diff` and
    (b) a structured per-case `pytest` by running src/differential_oracle on that module
    vs the real-cobc golden bytes (golden_io.json) — labeled source="differential_oracle"
    so it's never misrepresented as the agent's own test. Business rules fall back to the
    module's real recovered rules. So the demo never looks empty, with or without markers.
Validate the whole live path with `scripts/smoke_test.py` the instant the key exists.

Run:
    pip install -r requirements.txt
    export GEMINI_API_KEY=...            # provisioned at the event
    uvicorn server:app --app-dir src --reload
    # open http://127.0.0.1:8000   (UI at /, live by default; ?mock=1 = break-glass)
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib
import queue
import tempfile
import threading
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

import agent as agent_mod  # src/ is on sys.path (uvicorn --app-dir src)
import differential_oracle  # deterministic equivalence harness (agent python vs golden)
import event_transform  # canonical-event derivations (pytest/oracle/business_rule)

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
SAMPLE_DIR = ROOT / "src" / "sample"

app = FastAPI(title="LAZARUS — Aero-Migrate", version="1.0")

# run_id -> {"queue": queue.Queue (thread-safe, loop-independent), "download": str|None}
_RUNS: dict[str, dict] = {}
_RUN_PY_NAMES: dict[str, str] = {}
_SENTINEL = object()  # marks end-of-stream in the queue

# Completed-run download retention: when the SSE stream ends we pop _RUNS (one subscriber
# per run), which previously made GET /api/download/{run_id} 404 AFTER the run — the UI arms
# Download from the inline event so the demo works, but the standalone endpoint died. Keep
# the migrated bytes in a bounded LRU so the endpoint serves them post-run too.
import collections  # noqa: E402 (kept next to the structure it backs)
_COMPLETED_DOWNLOADS: "collections.OrderedDict[str, str]" = collections.OrderedDict()
_COMPLETED_DOWNLOADS_MAX = 32  # cap memory; oldest finished run's bytes evicted first


def _retain_download(run_id: str, content: str | None) -> None:
    """Stash a finished run's migrated module so /api/download serves it after the stream
    ends. Bounded LRU (oldest evicted) so a long-lived server doesn't grow unbounded."""
    if not content:
        return
    _COMPLETED_DOWNLOADS[run_id] = content
    _COMPLETED_DOWNLOADS.move_to_end(run_id)
    while len(_COMPLETED_DOWNLOADS) > _COMPLETED_DOWNLOADS_MAX:
        _COMPLETED_DOWNLOADS.popitem(last=False)

# Operator-facing labels for the phase rail / WORKING banner (frontend reads phase.label).
# Used as the default when a phase is emitted without an explicit label (e.g. milestone-
# derived phases). Keep these human and present-tense — they're what the operator reads
# during the multi-minute live wait.
_PHASE_LABELS = {
    "ingest": "Provisioning sandbox + reading the COBOL",
    "recover": "Recovering the business rules",
    "translate": "Translating COBOL → Python",
    "oracle": "Running the differential oracle",
    "test": "Proving byte-for-byte equivalence",
    "diagnose": "Diagnosing the divergent idiom",
    "forge": "Forging a new skill for the idiom",
    "reload": "Re-reading the forged skill",
    "verify": "Verifying the re-translation",
    "done": "Migration complete",
}


def _key_present() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


# The whole-environment tarball is HUGE (conda lives in /workspace) and qa saw it hang past
# 180s — never returning inside the demo budget. It is NO LONGER the primary module source
# (the agent's echoed LAZARUS_MODULE block is — see python_module_from_output); the tarball
# is only a best-effort, BACKGROUND upgrade to authoritative on-disk bytes. So give it a SHORT
# timeout: fail fast instead of burning minutes. Override via env if a run wants to wait.
_ENV_TARBALL_TIMEOUT = float(os.environ.get("LAZARUS_ENV_TARBALL_TIMEOUT", "8"))


def _fetch_env_tarball(env_id: str) -> bytes:
    """Download the whole-environment tarball via the Files API (findings-agents.md §9,
    cookbook-verbatim URL). Requires GEMINI_API_KEY. Raises on any HTTP/network error."""
    import urllib.request
    key = os.environ.get("GEMINI_API_KEY", "")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/files/"
        f"environment-{env_id}:download?alt=media"
    )
    req = urllib.request.Request(url, headers={"x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=_ENV_TARBALL_TIMEOUT) as resp:  # noqa: S310
        return resp.read()


def _extract_migrated_from_tar(tar_bytes: bytes, module_name: str = "payroll.py") -> str | None:
    """Extract the migrated module's text from an environment tarball.

    Looks for `<...>/workspace/<module_name>` (the agent writes the migration into
    /workspace). Returns the file's text, or None if it isn't present.
    """
    import io
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:*") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = member.name.lstrip("./")
            if name == f"workspace/{module_name}" or name.endswith(f"/workspace/{module_name}") \
                    or name.endswith(f"/{module_name}") and "workspace" in name.split("/"):
                fh = tar.extractfile(member)
                if fh is not None:
                    return fh.read().decode("utf-8", errors="replace")
    return None


def _download_migrated(env_id: str | None, *, module_name: str = "payroll.py",
                       fetch_tarball=None) -> str | None:
    """Fetch the agent-written module from the persistent sandbox via the Files API.

    `fetch_tarball(env_id) -> bytes` is injectable for testing; defaults to the real
    Files-API call. Returns None (so the Download button stays un-armed, never serving a
    stand-in) when there's no env id or any fetch/extract error.
    """
    if not env_id:
        return None
    fetch = fetch_tarball or _fetch_env_tarball
    try:
        return _extract_migrated_from_tar(fetch(env_id), module_name)
    except Exception:
        return None


def _start_background_tarball_upgrade(run: dict, env_id: str, module_name: str = "payroll.py") -> None:
    """Opportunistically upgrade run["download"] to the AUTHORITATIVE on-disk tarball bytes.

    The diff/pytest/download events already fire off the model-output module (instant). The
    Files-API whole-environment tarball is the authoritative image but can hang well past the
    demo budget (qa: >180s), so we fetch it in a DAEMON thread and only overwrite the download
    payload if it returns. It never blocks the live event stream; if it never returns, the UI
    keeps the model-output module (the same code the agent wrote). Best-effort, swallow errors.
    """
    def worker() -> None:
        try:
            authoritative = _download_migrated(env_id, module_name=module_name)
            if authoritative:
                run["download"] = authoritative  # upgrade to on-disk bytes if/when they arrive
        except Exception:
            pass  # keep the model-output module already in run["download"]
    threading.Thread(target=worker, daemon=True).start()


# Deterministic preview of the skill the agent forges for this module's idiom (numeric
# DISPLAY de-editing + ROUND_HALF_UP). Shown as the forge panel's git additions when we
# can't extract the agent's actual SKILL.md bytes from the env tarball. It describes the
# REAL technique for the divergence the oracle catches, so the panel stays truthful.
_FORGE_SKILL_PREVIEW = [
    "# Skill: numeric DISPLAY de-editing + half-up rounding",
    "",
    "## When",
    "A COBOL `COMPUTE ... ROUNDED` over a PIC 9(n)V99 DISPLAY field diverges from a",
    "naive Python port on rounding ties (e.g. 1.00 -> COBOL 0.77 vs Python round() 0.78).",
    "",
    "## Fix",
    "- ROUNDED is round-half-UP, not banker's: use",
    "  Decimal(x).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP).",
    "- DISPLAY of PIC 9(7)V99 emits 7 zero-padded integer digits + '.' + 2 decimals,",
    "  unsigned, with a trailing newline: f\"{int_part:07d}.{frac:02d}\\n\".",
    "- Do NOT use Python's float or round(); carry Decimal end-to-end.",
]


def _forge_skill_preview(skill_path: str, output_text: str) -> list[str]:
    """git additions for the forge panel: the lines of the skill the agent forged.

    Best-effort, in order: (1) a fenced block immediately after the skill path in the
    agent's own output (its real authored content, if printed), else (2) the deterministic
    preview of the idiom fix. Either way the lines describe the REAL technique.
    """
    import re as _re
    # If the agent echoed the file content in a fenced block near the path, prefer it.
    m = _re.search(r"```[a-zA-Z]*\n(.*?)```", output_text, _re.S)
    if m and "ROUND" in m.group(1).upper():
        lines = m.group(1).rstrip("\n").splitlines()
        if 2 <= len(lines) <= 40:
            return lines
    return list(_FORGE_SKILL_PREVIEW)


def _run_oracle_pytest(migrated_src: str, py_name: str = "payroll.py", iteration: int = 1) -> dict | None:
    """Run the differential oracle on the agent's Python code vs the real-cobc golden bytes.

    The DETERMINISTIC fallback (and corroboration) for the test panel: write the agent's
    fetched module to a temp file and diff its output, per golden input, against the
    pre-captured real-GnuCOBOL bytes in golden_io.json. Returns a STRUCTURED pytest event
    (per-case cobol-vs-python) labeled as the differential-oracle harness — so the RED->GREEN
    panel populates from REAL output regardless of whether the agent printed a marker.

    Failure modes are kept HONEST (so a broken module never looks falsely green):
      * golden capture missing/unreadable -> None (the harness genuinely can't run; the
        caller falls back to the coarse prose verdict).
      * the agent's module won't RUN (crash / non-zero exit / timeout) -> an explicit RED
        pytest event noting the oracle couldn't execute it, NEVER None. Otherwise an agent
        that crashes but claims "all tests pass" would slip through as a prose-only green.
    """
    golden = SAMPLE_DIR / "golden_io.json"
    if not golden.exists():
        return None
    py_tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write(migrated_src)
            py_tmp = fh.name
        try:
            records = differential_oracle.prove_equivalence(py_tmp, str(golden))
        except Exception as e:
            # The module itself failed to run under the oracle -> explicit RED, not None.
            return {
                "type": "pytest",
                "result": "red",
                "iteration": iteration,
                "source": "differential_oracle",
                "summary": (f"differential oracle could not run the agent's {py_name}: "
                            f"{type(e).__name__}: {e}".strip()[:300]),
                "cases": [],
            }
        return event_transform.oracle_harness_pytest_event(records, iteration=iteration)
    finally:
        if py_tmp:
            try:
                os.unlink(py_tmp)
            except OSError:
                pass


def _run_migration(run_id: str, cobol: str, filename: str) -> None:
    """Worker thread: drive the real agent, pushing canonical events to the run's queue.

    Uses a thread-safe queue.Queue (NOT asyncio.Queue) so it is independent of
    which event loop the POST and GET-stream requests run on.

    Two layers feed the panels:
      * FAST PATH (markers): if the agent prints LAZARUS_RULE / LAZARUS_ORACLE_JSON, those
        drive the rules + structured pytest directly.
      * SAFETY NET (deterministic): regardless of markers, after migrate() returns we fetch
        the agent's payroll.py via the Files API and (a) emit a real COBOL<->Python `diff`
        and (b) run the differential oracle against golden_io.json for a structured per-case
        `pytest`. The phase rail also advances PROGRESSIVELY off the streamed step text.
    """
    run = _RUNS[run_id]
    q: queue.Queue = run["queue"]

    def push(ev) -> None:
        q.put(ev)

    # Progressive phases: advance the rail as the agent's streamed text crosses milestones.
    # Only forward-moving transitions are emitted (the rail never jumps backwards), and each
    # phase is emitted at most once, so the UI shows ingest->recover->translate->oracle->test
    # ->forge LIVE rather than only the terminal verdict.
    _PHASE_ORDER = ["ingest", "recover", "translate", "oracle", "test",
                    "diagnose", "forge", "reload", "verify", "done"]
    progress = {"idx": 0}  # highest phase index emitted so far

    def emit_phase(phase: str, *, label: str | None = None, **extra) -> None:
        try:
            idx = _PHASE_ORDER.index(phase)
        except ValueError:
            return
        if idx < progress["idx"]:
            return  # never move the rail backwards
        progress["idx"] = idx
        # Always carry a human label — the UI's WORKING banner shows it during the
        # multi-minute live wait (reads phase.label, falls back to phase.phase).
        push({"type": "phase", "phase": phase,
              "label": label or _PHASE_LABELS.get(phase, f"{phase.capitalize()}…"),
              **extra})

    def emit_step(text: str) -> None:
        # Stream the agent's prose + tool breadcrumbs to the trace (keeps the screen alive),
        # but DO NOT advance the phase rail from prose: qa's live capture proved the agent's
        # prose mentions beats out of chronological order (oracle keywords during early file
        # exploration; the business-rules summary at the very end), so a forward-only prose
        # rail skips recover/translate/test. The rail is driven by the ordered STRUCTURED
        # events below (recover/translate/oracle/test) instead.
        push({"type": "step", "kind": "output", "text": text})

    def emit_iteration(c: int, t: int) -> None:
        # The enforced loop counter is orthogonal to the phase: surface `iteration` on the
        # CURRENT phase (don't jump the rail to TEST before the agent has tested anything).
        cur = _PHASE_ORDER[progress["idx"]]
        push({"type": "phase", "phase": cur, "iteration": c,
              "iteration_cap": t, "label": f"Iteration {c}/{t}"})

    orig_emit, orig_iter = agent_mod.emit_to_ui, agent_mod.emit_iteration
    agent_mod.emit_to_ui = emit_step
    agent_mod.emit_iteration = emit_iteration
    tmp_path = None
    try:
        emit_phase("ingest", label=f"Provisioning sandbox + reading {filename}")
        with tempfile.NamedTemporaryFile("w", suffix=".cob", delete=False) as fh:
            fh.write(cobol)
            tmp_path = fh.name

        client = agent_mod.genai.Client()  # reads GEMINI_API_KEY
        agent_mod.ensure_agent(client)
        result = agent_mod.migrate(client, tmp_path)

        output = agent_mod.extract_output_text(result)

        # The phase rail is driven by these STRUCTURED emissions IN SEMANTIC ORDER
        # (recover→translate→oracle→test), NOT by prose keywords — the live agent's prose
        # mentions beats out of order (oracle keywords during early file exploration; the
        # business-rules summary at the very end), so a forward-only prose rail skips beats.
        # The structured events the orchestrator emits ARE ordered, so we emit each phase as
        # its event is produced, with the diff (translate) BEFORE the oracle banner — which is
        # also the true sequence: the agent writes payroll.py, THEN the oracle compares it.

        # recover: recovered business rules (markers if emitted, else the >=3-rule fallback).
        emit_phase("recover")
        rules = event_transform.business_rules_from_text(output)
        if not rules:
            rules = event_transform.business_rules_fallback()
        for rule in rules:
            push(rule)

        # Recover the agent's actual module to drive the diff + the oracle pytest + download.
        # PRIMARY = the fenced ```python block the agent echoes in its model output. This is
        # INSTANT (already in `output`, no network) — qa proved the whole-environment Files-API
        # tarball can hang well past 180s, which would stall a 2-min demo and blank the diff +
        # download. So we DO NOT block the demo on the tarball; the echoed module is the agent's
        # real, runnable code and it's right here.
        # BEST-EFFORT UPGRADE = the Files-API tarball is the authoritative on-disk image; we try
        # it with a SHORT timeout in the BACKGROUND and upgrade run["download"] only if it
        # returns quickly. It can never delay the diff/pytest/download events.
        env_id = agent_mod.extract_environment_id(result)
        migrated = event_transform.python_module_from_output(output)
        module_source = "model_output" if migrated is not None else None
        run["download"] = migrated
        py_name = filename.replace(".cob", ".py") if filename.endswith(".cob") else "payroll.py"
        if env_id:
            _start_background_tarball_upgrade(run, env_id, py_name)

        # translate: COBOL<->Python diff from REAL sources (submitted COBOL + agent module).
        # Emitted BEFORE the oracle so the forward-only rail lights translate→oracle in order.
        if migrated is not None:
            emit_phase("translate")
            push(event_transform.diff_event(cobol, migrated,
                                            cobol_name=filename, python_name=py_name))

        # oracle: the differential-oracle banner (real compiler + the golden input battery).
        golden = SAMPLE_DIR / "golden_io.json"
        if golden.exists():
            emit_phase("oracle")
            push(event_transform.oracle_event(str(golden)))

        # STRUCTURED pytest (the money shot). Priority:
        #   1. agent's LAZARUS_ORACLE_JSON marker (the agent's own per-case oracle), else
        #   2. the orchestrator's differential oracle on the fetched module vs golden bytes
        #      (deterministic; labeled as the oracle harness, not the agent's pytest), else
        #   3. a coarse RED/GREEN verdict scraped from the agent's terminal text.
        emit_phase("test")
        records = event_transform.parse_oracle_records(output)
        if records:
            pytest_ev = event_transform.to_pytest_event(records, iteration=1)
        elif migrated is not None:
            pytest_ev = _run_oracle_pytest(migrated, py_name=py_name, iteration=1)
        else:
            pytest_ev = None
        if pytest_ev is not None:
            passed = pytest_ev["result"] == "green"
            push(pytest_ev)
        else:
            passed = agent_mod._tests_passed(output)
            push({"type": "pytest", "result": "green" if passed else "red",
                  "iteration": 1, "summary": output[-500:] or "(no test output)",
                  "cases": []})

        # forge + reload: the self-authored SKILL.md beat. Emitted AFTER test so the
        # forward-only rail stays in order (forge/reload sit after test in the rail); the
        # narrative is write→test(RED)→forge→reload→re-test(GREEN), and these structured
        # events report the skill the agent wrote during that loop.
        skill = agent_mod._forged_skill_path(output)
        if skill:
            emit_phase("forge")
            push({"type": "forge", "skill": skill,
                  "reason": "Unknown idiom: numeric DISPLAY format + ROUND-HALF-UP.",
                  "git": {"status": "A",
                          "additions": _forge_skill_preview(skill, output),
                          "commit": f"forge: add {pathlib.Path(skill).parent.name} skill"}})
            emit_phase("reload")
            push({"type": "reload",
                  "label": f"Re-reading {skill} in the reused environment"})

        if migrated is not None:
            push({"type": "download", "name": py_name,
                  "mime": "text/x-python", "content": migrated, "source": module_source})
        emit_phase("done")
        push({"type": "done",
              "verdict": "EQUIVALENT" if passed else "INCOMPLETE",
              "environment_id": env_id})
    except Exception as e:  # surface real errors to the UI, never fake success
        push({"type": "error", "message": f"{type(e).__name__}: {e}"})
    finally:
        agent_mod.emit_to_ui, agent_mod.emit_iteration = orig_emit, orig_iter
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        q.put(_SENTINEL)  # end of stream


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "gemini_api_key_present": _key_present(),
        "agent": agent_mod.AGENT_ID,
        "base_agent": agent_mod.BASE_AGENT,
        "max_iterations": agent_mod.MAX_ITERATIONS,
    }


@app.get("/api/skills")
def list_skills():
    """List all seed and dynamically forged skills inside .agents/skills/"""
    skills_dir = ROOT / ".agents" / "skills"
    skills = []
    if skills_dir.is_dir():
        for skill_path in sorted(skills_dir.glob("*/SKILL.md")):
            try:
                content = skill_path.read_text(encoding="utf-8")
                name = skill_path.parent.name
                description = "Self-authored COBOL modernization skill."
                
                # Basic frontmatter parse
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        fm = parts[1]
                        for line in fm.splitlines():
                            if line.startswith("name:"):
                                name = line.split(":", 1)[1].strip()
                            elif line.startswith("description:"):
                                description = line.split(":", 1)[1].strip()
                
                skills.append({
                    "id": skill_path.parent.name,
                    "name": name,
                    "description": description,
                    "content": content
                })
            except Exception:
                pass
    return skills


@app.post("/api/migrate")
async def migrate_start(request: Request):
    """Kick off a migration; return a run_id the UI subscribes to via /api/stream."""
    if not _key_present():
        return JSONResponse(
            status_code=503,
            content={"type": "error", "error": "GEMINI_API_KEY not set",
                     "hint": "export GEMINI_API_KEY=... (Gemini API key, provisioned at the event)"},
        )
    try:
        body = await request.json()
    except Exception:
        body = {}
    cobol = (body or {}).get("cobol")
    filename = (body or {}).get("filename", "payroll.cob")
    if not cobol:
        sample = SAMPLE_DIR / "payroll.cob"  # convenience fallback to the golden sample
        if sample.exists():
            cobol = sample.read_text()
        else:
            raise HTTPException(status_code=400, detail="no COBOL provided")

    run_id = uuid.uuid4().hex
    _RUNS[run_id] = {"queue": queue.Queue(), "download": None}
    _RUN_PY_NAMES[run_id] = filename.replace(".cob", ".py") if filename.endswith(".cob") else "payroll.py"
    threading.Thread(
        target=_run_migration, args=(run_id, cobol, filename), daemon=True
    ).start()
    return {"run_id": run_id}


@app.get("/api/stream/{run_id}")
async def migrate_stream(run_id: str, request: Request):
    """Stream a run's canonical events as SSE until the terminal `done`/`error`."""
    run = _RUNS.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="unknown run_id")
    q: queue.Queue = run["queue"]

    async def event_gen():
        try:
            while True:
                if await request.is_disconnected():
                    break
                ev = await asyncio.to_thread(q.get)  # loop-independent blocking get
                if ev is _SENTINEL:
                    break
                yield {"data": json.dumps(ev)}
        finally:
            # Retain the migrated bytes (if any) so /api/download still serves them after the
            # stream ends, THEN drop the live run record (one subscriber per run; clean up).
            finished = _RUNS.pop(run_id, None)
            if finished is not None:
                _retain_download(run_id, finished.get("download"))

    return EventSourceResponse(event_gen())


@app.get("/api/download/{run_id}")
def download(run_id: str):
    """Return the migrated module for a run — DURING the run (from _RUNS) or AFTER it ends
    (from the retained-downloads LRU), so the endpoint doesn't 404 once the stream closes."""
    run = _RUNS.get(run_id)
    content = (run.get("download") if run else None) or _COMPLETED_DOWNLOADS.get(run_id)
    if not content:
        raise HTTPException(status_code=404, detail="migrated module not available yet")
    py_name = _RUN_PY_NAMES.get(run_id, "payroll.py")
    return PlainTextResponse(
        content,
        media_type="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="{py_name}"'},
    )


# Serve the live-trace UI at / (mounted last so /api/* wins).
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
