"""Tests for the FastAPI/SSE bridge (src/server.py) — all runnable WITHOUT a key.

Covers what's verifiable offline: health, the explicit no-key 503 (never fake
data), and that a (stubbed) agent run is forwarded over the run_id contract that
web/src/live.js consumes:  POST /api/migrate -> {run_id}; GET /api/stream/{run_id}
-> canonical SSE events. The live Gemini path itself is validated by
scripts/smoke_test.py once the key is provisioned.
"""
import json
import pathlib
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import server  # noqa: E402

agent_mod = server.agent_mod


def test_health_reports_agent_and_key_flag(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = TestClient(server.app)
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["agent"] == agent_mod.AGENT_ID
    assert body["base_agent"] == agent_mod.BASE_AGENT
    assert body["gemini_api_key_present"] is False


def test_migrate_without_key_returns_503(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = TestClient(server.app)
    r = client.post("/api/migrate", json={"cobol": "x", "filename": "x.cob"})
    assert r.status_code == 503
    assert "GEMINI_API_KEY" in r.json()["error"]


def test_stream_unknown_run_id_404(monkeypatch):
    client = TestClient(server.app)
    with client.stream("GET", "/api/stream/does-not-exist") as resp:
        assert resp.status_code == 404


def _make_tar_bytes(members: dict[str, str]) -> bytes:
    """Build an in-memory tar (path -> text content) for download-extraction tests."""
    import io
    import tarfile
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for path, text in members.items():
            data = text.encode()
            info = tarfile.TarInfo(name=path)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_extract_migrated_pulls_payroll_py_from_workspace():
    """The migrated module is extracted from /workspace/payroll.py inside the env tarball."""
    tar = _make_tar_bytes({
        "workspace/payroll.py": "print('migrated')\n",
        "workspace/other.txt": "ignore me\n",
    })
    content = server._extract_migrated_from_tar(tar, "payroll.py")
    assert content == "print('migrated')\n"


def test_extract_migrated_returns_none_when_absent():
    tar = _make_tar_bytes({"workspace/notes.md": "no python here\n"})
    assert server._extract_migrated_from_tar(tar, "payroll.py") is None


def test_download_migrated_uses_injected_fetcher(monkeypatch):
    """_download_migrated fetches the env tarball (injected here) + extracts the module —
    no network/key needed for the unit test."""
    tar = _make_tar_bytes({"workspace/payroll.py": "X = 1\n"})
    out = server._download_migrated(
        env_id="env-xyz", fetch_tarball=lambda env_id: tar
    )
    assert out == "X = 1\n"


def test_download_migrated_none_without_env_id():
    assert server._download_migrated(env_id=None) is None


def test_download_migrated_none_on_fetch_error():
    def boom(env_id):
        raise RuntimeError("network down")
    assert server._download_migrated(env_id="e", fetch_tarball=boom) is None


def test_post_then_stream_emits_canonical_events(monkeypatch):
    """POST -> run_id, then GET /api/stream/{run_id} forwards canonical events."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    monkeypatch.setattr(agent_mod.genai, "Client", lambda *a, **k: object())
    monkeypatch.setattr(agent_mod, "ensure_agent", lambda client: None)

    def fake_migrate(client, path):
        agent_mod.emit_iteration(1, agent_mod.MAX_ITERATIONS)
        agent_mod.emit_to_ui("Recovered business rules; wrote payroll.py ...")
        return SimpleNamespace()

    monkeypatch.setattr(agent_mod, "migrate", fake_migrate)
    monkeypatch.setattr(
        agent_mod, "extract_output_text",
        lambda r: "FORGED .agents/skills/numeric-display-rounding/SKILL.md. all tests pass",
    )
    monkeypatch.setattr(agent_mod, "extract_environment_id", lambda r: "env-abc123")

    client = TestClient(server.app)
    start = client.post("/api/migrate", json={"cobol": "IDENTIFICATION DIVISION.",
                                              "filename": "payroll.cob"})
    assert start.status_code == 200
    run_id = start.json()["run_id"]
    assert run_id

    seen = []
    with client.stream("GET", f"/api/stream/{run_id}") as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            s = line.decode() if isinstance(line, (bytes, bytearray)) else line
            if s and s.startswith("data:"):
                ev = json.loads(s[len("data:"):].strip())
                seen.append(ev.get("type"))
                if ev.get("type") in ("done", "error"):
                    break

    assert "phase" in seen     # enforced iteration counter + lifecycle
    assert "step" in seen      # live "agent working" trace
    assert "forge" in seen     # forged-skill detected from agent output
    assert "pytest" in seen    # RED/GREEN verdict
    assert "done" in seen      # terminal verdict


def test_stream_emits_structured_pytest_and_oracle(monkeypatch):
    """The #1 money shot: server derives a STRUCTURED pytest event (per-case
    cobol-vs-python) + an oracle banner from the agent's LAZARUS_ORACLE_JSON marker."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    monkeypatch.setattr(agent_mod.genai, "Client", lambda *a, **k: object())
    monkeypatch.setattr(agent_mod, "ensure_agent", lambda client: None)
    monkeypatch.setattr(agent_mod, "migrate", lambda client, path: SimpleNamespace())
    agent_output = (
        'LAZARUS_RULE: {"title": "Progressive tax", "plain": "22.5% withheld", "severity": "rule"}\n'
        'LAZARUS_ORACLE_JSON: [{"input": "1.00\\n", "cobol": "0000000.77\\n", '
        '"python": "0000000.78\\n", "match": false}, '
        '{"input": "1000.00\\n", "cobol": "0000775.00\\n", "python": "0000775.00\\n", "match": true}]\n'
        "1 failed, 1 passed"
    )
    monkeypatch.setattr(agent_mod, "extract_output_text", lambda r: agent_output)
    monkeypatch.setattr(agent_mod, "extract_environment_id", lambda r: "env-xyz")

    client = TestClient(server.app)
    run_id = client.post("/api/migrate", json={"cobol": "X", "filename": "p.cob"}).json()["run_id"]

    events = []
    with client.stream("GET", f"/api/stream/{run_id}") as resp:
        for line in resp.iter_lines():
            s = line.decode() if isinstance(line, (bytes, bytearray)) else line
            if s and s.startswith("data:"):
                ev = json.loads(s[len("data:"):].strip())
                events.append(ev)
                if ev.get("type") in ("done", "error"):
                    break

    by_type = {e["type"]: e for e in events}
    assert "oracle" in by_type and "GnuCOBOL" in by_type["oracle"]["compiler"]
    assert "business_rule" in by_type
    pt = by_type["pytest"]
    assert pt["result"] == "red"
    assert len(pt["cases"]) == 2
    fail = next(c for c in pt["cases"] if c["status"] == "fail")
    assert fail["cobol"] == "0000000.77\n" and fail["python"] == "0000000.78\n"  # the diff!


# --------------------------------------------------------------------------
# The DETERMINISTIC SAFETY NET: even with ZERO markers, the live path fetches the
# agent's payroll.py and drives the diff + a structured per-case pytest from the
# orchestrator's differential oracle (agent python vs real-cobc golden bytes).
# --------------------------------------------------------------------------
def _tar_with_module(module_text: str, *, path: str = "env-x/workspace/payroll.py") -> bytes:
    return _make_tar_bytes({path: module_text})


def _collect_events(client, run_id):
    events = []
    with client.stream("GET", f"/api/stream/{run_id}") as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            s = line.decode() if isinstance(line, (bytes, bytearray)) else line
            if s and s.startswith("data:"):
                ev = json.loads(s[len("data:"):].strip())
                events.append(ev)
                if ev.get("type") in ("done", "error"):
                    break
    return events


def _stub_markerless_agent(monkeypatch, *, output, env_id="env-x", emit=None):
    """Stub the agent so migrate() emits no markers — exercises the safety net path."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    monkeypatch.setattr(agent_mod.genai, "Client", lambda *a, **k: object())
    monkeypatch.setattr(agent_mod, "ensure_agent", lambda client: None)

    def fake_migrate(client, path):
        agent_mod.emit_iteration(1, agent_mod.MAX_ITERATIONS)
        for line in (emit or ["Reading COBOL", "Writing payroll.py", "Running pytest"]):
            agent_mod.emit_to_ui(line)
        return SimpleNamespace()

    monkeypatch.setattr(agent_mod, "migrate", fake_migrate)
    monkeypatch.setattr(agent_mod, "extract_output_text", lambda r: output)
    monkeypatch.setattr(agent_mod, "extract_environment_id", lambda r: env_id)


def _output_echoing_module(module_src: str, *, trailer: str = "") -> str:
    """Agent output that echoes the migrated module in a fenced ```python block (what the
    real agent does — qa confirmed). The model output is the PRIMARY module source now (the
    Files-API tarball can hang past the demo budget), so tests feed the module here."""
    return f"Here is the migration:\n\n```python\n{module_src}\n```\n\n{trailer}"


def test_safety_net_populates_every_panel_without_markers(monkeypatch):
    """No LAZARUS_* markers at all: the server still drives diff + a structured oracle pytest
    from the agent's echoed payroll.py, plus fallback rules + the oracle banner."""
    sample_py = (ROOT / "src" / "sample" / "payroll.py").read_text()
    _stub_markerless_agent(
        monkeypatch,
        output=_output_echoing_module(
            sample_py, trailer="All equivalence tests pass. Equivalent to original COBOL."),
    )

    client = TestClient(server.app)
    run_id = client.post("/api/migrate", json={
        "cobol": (ROOT / "src" / "sample" / "payroll.cob").read_text(),
        "filename": "payroll.cob",
    }).json()["run_id"]
    events = _collect_events(client, run_id)
    by_type = {e["type"]: e for e in events}

    # Every panel populated from REAL output, no markers + no working tarball required.
    assert sum(1 for e in events if e["type"] == "business_rule") >= 3   # fallback rules
    assert "oracle" in by_type
    diff = by_type["diff"]
    assert diff["left"]["name"] == "payroll.cob" and diff["right"]["name"] == "payroll.py"
    assert "IDENTIFICATION DIVISION" in diff["left"]["code"]              # real submitted COBOL
    assert "ROUND_HALF_UP" in diff["right"]["code"]                       # the agent's real module
    pt = by_type["pytest"]
    assert pt["source"] == "differential_oracle"                        # truthful labeling
    assert pt["result"] == "green" and len(pt["cases"]) == 10           # all golden cases
    assert all(c["name"].startswith("oracle_equivalence[") for c in pt["cases"])
    assert by_type["download"]["content"] and by_type["download"]["source"] == "model_output"
    assert by_type["done"]["verdict"] == "EQUIVALENT"


def test_safety_net_goes_red_when_module_diverges(monkeypatch):
    """A naive port using banker's rounding fails the tie cases — the oracle pytest goes
    RED with per-case cobol-vs-python bytes, even though the agent claimed success."""
    naive_py = (
        "import sys\n"
        "from decimal import Decimal\n"
        "g = Decimal(sys.stdin.readline().strip())\n"
        "tax = round(g * Decimal('0.225'), 2)\n"   # banker's rounding -> wrong on ties
        "net = g - tax\n"
        "print(f'{int(net):07d}.{int((net % 1) * 100):02d}')\n"
    )
    _stub_markerless_agent(  # agent OVER-claims, but echoes the naive module
        monkeypatch, output=_output_echoing_module(naive_py, trailer="all tests pass"))

    client = TestClient(server.app)
    run_id = client.post("/api/migrate", json={
        "cobol": (ROOT / "src" / "sample" / "payroll.cob").read_text(),
        "filename": "payroll.cob",
    }).json()["run_id"]
    by_type = {e["type"]: e for e in _collect_events(client, run_id)}

    pt = by_type["pytest"]
    assert pt["source"] == "differential_oracle"
    assert pt["result"] == "red"                 # the oracle catches the divergence
    assert any(c["status"] == "fail" for c in pt["cases"])
    assert by_type["done"]["verdict"] == "INCOMPLETE"   # verdict follows the REAL oracle


def test_crashing_module_goes_red_not_falsely_green(monkeypatch):
    """A fetched payroll.py that CRASHES under the oracle must show an explicit RED with a
    diagnostic note — never fall through to a prose-only green just because the agent claimed
    success. Otherwise a broken module + an over-claiming agent slips through."""
    broken_py = (                                      # >=5 lines so it scrapes; crashes on run
        "import sys\n"
        "from decimal import Decimal\n"
        "\n"
        "def main():\n"
        "    raise SystemExit('boom')\n"
        "\n"
        "main()\n"
    )
    _stub_markerless_agent(  # agent OVER-claims, but echoes the crashing module
        monkeypatch, output=_output_echoing_module(broken_py, trailer="All tests pass!"))

    client = TestClient(server.app)
    run_id = client.post("/api/migrate", json={"cobol": "X", "filename": "p.cob"}).json()["run_id"]
    by_type = {e["type"]: e for e in _collect_events(client, run_id)}

    pt = by_type["pytest"]
    assert pt["result"] == "red"                       # NOT a false green
    assert pt["source"] == "differential_oracle"
    assert "could not run" in pt["summary"]
    assert by_type["done"]["verdict"] == "INCOMPLETE"   # verdict follows the failed oracle


def test_agent_marker_pytest_is_labeled_agent_source(monkeypatch):
    """When the per-case pytest comes from the agent's OWN LAZARUS_ORACLE_JSON marker, it's
    labeled source='agent_pytest' (distinct from the orchestrator's differential_oracle), so
    the UI can show provenance honestly."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    monkeypatch.setattr(agent_mod.genai, "Client", lambda *a, **k: object())
    monkeypatch.setattr(agent_mod, "ensure_agent", lambda client: None)
    monkeypatch.setattr(agent_mod, "migrate", lambda client, path: SimpleNamespace())
    monkeypatch.setattr(
        agent_mod, "extract_output_text",
        lambda r: ('LAZARUS_ORACLE_JSON: [{"input": "1000.00\\n", "cobol": "0000775.00\\n", '
                   '"python": "0000775.00\\n", "match": true}]\n1 passed'),
    )
    monkeypatch.setattr(agent_mod, "extract_environment_id", lambda r: "env-xyz")

    client = TestClient(server.app)
    run_id = client.post("/api/migrate", json={"cobol": "X", "filename": "p.cob"}).json()["run_id"]
    by_type = {e["type"]: e for e in _collect_events(client, run_id)}

    pt = by_type["pytest"]
    assert pt["source"] == "agent_pytest"              # the agent's own oracle, not ours
    assert pt["cases"][0]["name"].startswith("test_equivalence[")  # agent's case naming


def test_phase_rail_advances_in_semantic_order_from_structured_events(monkeypatch):
    """The rail is driven by the STRUCTURED events the server emits (business_rule→recover,
    diff→translate, oracle→oracle, pytest→test), NOT by prose keywords — because the live
    agent's prose mentions beats OUT of order (it says "search golden_io.json" during early
    exploration and writes the business-rules summary at the END). So even with deliberately
    out-of-order prose, the rail must still fire ingest→recover→translate→oracle→test→…→done
    IN ORDER with no skip and no false-fire (esp. no FORGE during a conda-forge install)."""
    sample_py = (ROOT / "src" / "sample" / "payroll.py").read_text()
    monkeypatch.setattr(server, "_fetch_env_tarball",
                        lambda env_id: _tar_with_module(sample_py))
    # Prose mimics the REAL live stream's order: oracle keywords FIRST (exploration), then
    # the module, then the business-rules summary LAST — the order that broke a prose rail.
    _stub_markerless_agent(
        monkeypatch,
        output=_output_echoing_module(
            sample_py,
            trailer="### Business Rules Specification — recovered. All equivalence tests pass."),
        emit=[
            "I will search for golden_io.json and the differential oracle setup",
            "Installing gnucobol via micromamba -c conda-forge",   # must NOT fire FORGE
            "compiling the original COBOL",
            "Now writing the analysis and business rules summary",
        ],
    )

    client = TestClient(server.app)
    run_id = client.post("/api/migrate", json={"cobol": "IDENTIFICATION DIVISION.",
                                              "filename": "payroll.cob"}).json()["run_id"]
    events = _collect_events(client, run_id)

    order = ["ingest", "recover", "translate", "oracle", "test",
             "diagnose", "forge", "reload", "verify", "done"]
    seen = [e["phase"] for e in events if e["type"] == "phase"]
    idxs = [order.index(p) for p in seen]
    assert idxs == sorted(idxs)                          # forward-only: never moves backward
    # the demo beats all light, in order — NONE skipped despite the out-of-order prose
    assert {"ingest", "recover", "translate", "oracle", "test", "done"} <= set(seen)
    # translate (diff) must come BEFORE oracle in the rail (agent writes payroll.py, THEN the
    # oracle compares it) — this is the ordering bug team-lead flagged.
    assert seen.index("translate") < seen.index("oracle")
    # labels are human (WORKING banner reads phase.label)
    labeled = {e["phase"]: e["label"] for e in events
               if e["type"] == "phase" and "iteration" not in e}
    assert all(labeled.get(p) for p in ("recover", "translate", "oracle", "test"))


def test_forge_event_carries_git_additions(monkeypatch):
    """When the agent forges a skill, the forge event carries git.additions so the
    'writing itself' panel types in real content (renderer requires ev.git.additions)."""
    sample_py = (ROOT / "src" / "sample" / "payroll.py").read_text()
    monkeypatch.setattr(server, "_fetch_env_tarball",
                        lambda env_id: _tar_with_module(sample_py))
    _stub_markerless_agent(
        monkeypatch,
        output="Forged .agents/skills/numeric-display-rounding/SKILL.md. all tests pass",
    )

    client = TestClient(server.app)
    run_id = client.post("/api/migrate", json={"cobol": "X", "filename": "p.cob"}).json()["run_id"]
    by_type = {e["type"]: e for e in _collect_events(client, run_id)}

    forge = by_type["forge"]
    assert forge["skill"].endswith("SKILL.md")
    assert isinstance(forge["git"]["additions"], list) and len(forge["git"]["additions"]) >= 2
    assert forge["git"]["status"] == "A" and forge["git"]["commit"]
    assert "reload" in by_type


def test_hanging_tarball_does_not_block_diff_or_pytest(monkeypatch):
    """qa's live gap: the Files-API whole-env tarball can hang past the demo budget (>180s),
    which blanked diff+download when the tarball was the primary source. Now the model-output
    module is PRIMARY (instant), so even a tarball that raises/hangs never blocks diff, the
    oracle pytest, or download — they all fire from the agent's echoed ```python block."""
    def boom(env_id):
        raise TimeoutError("The read operation timed out")
    monkeypatch.setattr(server, "_fetch_env_tarball", boom)

    sample_py = (ROOT / "src" / "sample" / "payroll.py").read_text()
    _stub_markerless_agent(monkeypatch, output=_output_echoing_module(
        sample_py, trailer="All equivalence tests pass; equivalent to the original COBOL."))

    client = TestClient(server.app)
    run_id = client.post("/api/migrate", json={
        "cobol": (ROOT / "src" / "sample" / "payroll.cob").read_text(),
        "filename": "payroll.cob",
    }).json()["run_id"]
    by_type = {e["type"]: e for e in _collect_events(client, run_id)}

    # Despite the tarball timeout, every artifact still populated from the echoed module.
    assert "diff" in by_type and by_type["diff"]["right"]["code"]      # diff not blanked
    pt = by_type["pytest"]
    assert pt["source"] == "differential_oracle" and pt["result"] == "green"
    assert len(pt["cases"]) == 10                                      # oracle ran the module
    dl = by_type["download"]
    assert dl["content"] and dl["source"] == "model_output"           # honest provenance
    assert by_type["done"]["verdict"] == "EQUIVALENT"


def test_tarball_unavailable_plus_module_marker_populates_diff_and_download(monkeypatch):
    """team-lead's deterministic path: tarball unavailable + the agent emits its module under
    the explicit LAZARUS_MODULE: marker → diff + download both populate from model_output,
    with no dependency on the slow whole-env tarball."""
    def boom(env_id):
        raise TimeoutError("tarball never returns")
    monkeypatch.setattr(server, "_fetch_env_tarball", boom)

    sample_py = (ROOT / "src" / "sample" / "payroll.py").read_text()
    # The agent prints prose + the REQUIRED LAZARUS_MODULE marker block (not a bare fence).
    output = (
        "Recovered the rules and translated. All equivalence tests pass.\n\n"
        "LAZARUS_MODULE:\n```python\n" + sample_py + "\n```\n"
    )
    _stub_markerless_agent(monkeypatch, output=output)

    client = TestClient(server.app)
    run_id = client.post("/api/migrate", json={
        "cobol": (ROOT / "src" / "sample" / "payroll.cob").read_text(),
        "filename": "payroll.cob",
    }).json()["run_id"]
    by_type = {e["type"]: e for e in _collect_events(client, run_id)}

    assert "diff" in by_type and "ROUND_HALF_UP" in by_type["diff"]["right"]["code"]
    dl = by_type["download"]
    assert dl["content"] and dl["source"] == "model_output"
    pt = by_type["pytest"]
    assert pt["source"] == "differential_oracle" and pt["result"] == "green"
    assert by_type["done"]["verdict"] == "EQUIVALENT"


def test_download_endpoint_serves_module_after_stream_ends(monkeypatch):
    """Phase-2 fix: GET /api/download/{run_id} must still return the module AFTER the SSE
    stream ends (the stream pops _RUNS). Previously it 404'd post-run; now a retained-downloads
    LRU serves it. The UI armed Download from the inline event regardless, but the standalone
    endpoint must work too."""
    sample_py = (ROOT / "src" / "sample" / "payroll.py").read_text()
    _stub_markerless_agent(monkeypatch, output=_output_echoing_module(
        sample_py, trailer="All equivalence tests pass."))

    client = TestClient(server.app)
    run_id = client.post("/api/migrate", json={
        "cobol": (ROOT / "src" / "sample" / "payroll.cob").read_text(),
        "filename": "payroll.cob",
    }).json()["run_id"]
    # Drain the stream to completion -> _RUNS is popped, download retained in the LRU.
    _collect_events(client, run_id)
    assert run_id not in server._RUNS                       # live run record cleaned up

    resp = client.get(f"/api/download/{run_id}")            # was 404 before the fix
    assert resp.status_code == 200
    assert "ROUND_HALF_UP" in resp.text                     # the real migrated module
    assert resp.headers["content-type"].startswith("text/x-python")


def test_download_endpoint_404_for_unknown_run(monkeypatch):
    client = TestClient(server.app)
    assert client.get("/api/download/never-existed").status_code == 404


def test_tarball_and_output_both_empty_keeps_panels_honest(monkeypatch):
    """If BOTH the tarball fetch fails AND the agent echoed no module, diff/download stay
    absent (honest empty, never faked) and the verdict falls to the coarse prose check."""
    monkeypatch.setattr(server, "_fetch_env_tarball",
                        lambda env_id: (_ for _ in ()).throw(TimeoutError("nope")))
    _stub_markerless_agent(monkeypatch, output="I finished. All tests pass. (no code block)")

    client = TestClient(server.app)
    run_id = client.post("/api/migrate", json={"cobol": "X", "filename": "p.cob"}).json()["run_id"]
    by_type = {e["type"]: e for e in _collect_events(client, run_id)}

    assert "diff" not in by_type                       # honestly absent, not fabricated
    assert "download" not in by_type
    # rules + oracle banner still populate; verdict from the coarse prose check
    assert "business_rule" in by_type and "oracle" in by_type
    assert by_type["done"]["verdict"] == "EQUIVALENT"  # prose says pass; no oracle to contradict
