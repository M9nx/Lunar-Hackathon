"""Local server for a saved-input run. It does not call Horizons."""

from __future__ import annotations

import json
import queue
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from lunar_navigator.catalog import (
    build_catalog,
    comparison_window_scenarios,
    default_roots,
    find_entry,
    root_path,
    scenario_for,
)
from lunar_navigator.engine import stream_comparison, stream_scenario

SCENARIOS = {
    "site04-48h": "tests/fixtures/site04_p02_practice_scenario.json",
    "site04-6h": "tests/fixtures/site04_p02_practice_6h_scenario.json",
    "malapert-48h": "tests/fixtures/malapert_practice_scenario.json",
    "site04-30d": "tests/fixtures/site04_p02_practice_30d_scenario.json",
    "malapert-30d": "tests/fixtures/malapert_practice_30d_scenario.json",
}

COMPARISONS = {
    "practice-48h": ("site04-48h", "malapert-48h"),
    "practice-30d": ("site04-30d", "malapert-30d"),
}


class LiveRun:
    def __init__(self) -> None:
        self.cancel = threading.Event()
        self.events: queue.Queue = queue.Queue()


def make_server(repo: Path, data_root: Path, revision: str, port: int) -> ThreadingHTTPServer:
    runs: dict[str, LiveRun] = {}
    comparisons: dict[str, LiveRun] = {}
    lock = threading.Lock()
    web_root = (repo / "web").resolve()
    roots = default_roots(repo, data_root)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            return

        def _json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 8192:
                raise ValueError("request body is too large")
            if length == 0:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "events":
                self._events(runs, parts[2])
                return
            if len(parts) == 4 and parts[:2] == ["api", "comparisons"] and parts[3] == "events":
                self._events(comparisons, parts[2])
                return
            if parts == ["api", "catalog"]:
                self._json(200, build_catalog(roots))
                return
            self._static(parsed.path)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            parts = [part for part in parsed.path.split("/") if part]
            if parts == ["api", "runs"]:
                self._start_run()
                return
            if parts == ["api", "comparisons"]:
                self._start_comparison()
                return
            if len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "cancel":
                self._cancel(runs, parts[2])
                return
            if len(parts) == 4 and parts[:2] == ["api", "comparisons"] and parts[3] == "cancel":
                self._cancel(comparisons, parts[2])
                return
            self._json(404, {"error": "not found"})

        def _load_scenario(self, name: str) -> dict:
            if name not in SCENARIOS:
                raise ValueError("scenario must be one of " + ", ".join(sorted(SCENARIOS)))
            return json.loads((repo / SCENARIOS[name]).read_text(encoding="utf-8"))

        @staticmethod
        def _with_mode(scenario: dict, body: dict) -> dict:
            """Apply the optional ``horizon_mode`` request field. Terrain mode never substitutes the 0 deg baseline."""
            mode = body.get("horizon_mode")
            if mode in (None, "", scenario.get("horizon_mode", "geometric_0deg")):
                return scenario
            if mode not in ("geometric_0deg", "terrain"):
                raise ValueError("horizon_mode must be geometric_0deg or terrain")
            return {**scenario, "horizon_mode": mode}

        def _resolve_run(self, body: dict) -> tuple[dict, Path]:
            """A named scenario, or a catalog entry with an optional UTC window."""
            if body.get("catalog"):
                entry = find_entry(build_catalog(roots), str(body["catalog"]))
                scenario = scenario_for(entry, body.get("start_utc"), body.get("end_utc"))
                return self._with_mode(scenario, body), root_path(roots, entry["root_id"])
            return self._with_mode(self._load_scenario(body.get("scenario")), body), data_root

        def _start_run(self) -> None:
            try:
                body = self._read_json()
                scenario, run_root = self._resolve_run(body)
                batch_size = int(body.get("batch_size", 4))
                pause_seconds = float(body.get("pause_seconds", 0))
                fail_after = body.get("fail_after_batches")
                fail_after_batches = None if fail_after in (None, "") else int(fail_after)
            except (ValueError, TypeError, json.JSONDecodeError, OSError) as exc:
                self._json(400, {"error": str(exc)})
                return
            if not 1 <= batch_size <= 500:
                self._json(400, {"error": "batch_size must be from 1 to 500"})
                return
            if not 0 <= pause_seconds <= 5:
                self._json(400, {"error": "pause_seconds must be from 0 to 5"})
                return
            live = LiveRun()
            run_id = uuid.uuid4().hex[:12]
            with lock:
                runs[run_id] = live

            def produce() -> None:
                try:
                    for event in stream_scenario(
                        scenario,
                        run_root,
                        revision,
                        batch_size=batch_size,
                        cancel=live.cancel,
                        fail_after_batches=fail_after_batches,
                        pause_seconds=pause_seconds,
                        run_id=run_id,
                    ):
                        live.events.put(event)
                finally:
                    live.events.put(None)

            threading.Thread(target=produce, daemon=True).start()
            self._json(200, {"run_id": run_id})

        def _start_comparison(self) -> None:
            try:
                body = self._read_json()
                comparison_root = data_root
                if body.get("catalog_window"):
                    scenario_a, scenario_b, window = comparison_window_scenarios(
                        build_catalog(roots), str(body["catalog_window"]), body.get("start_utc"), body.get("end_utc")
                    )
                    comparison_root = root_path(roots, find_entry(build_catalog(roots), window["a"])["root_id"])
                    scenario_a, scenario_b = self._with_mode(scenario_a, body), self._with_mode(scenario_b, body)
                else:
                    pair = body.get("pair", "practice-48h")
                    if pair not in COMPARISONS:
                        raise ValueError("pair must be one of " + ", ".join(sorted(COMPARISONS)))
                    name_a, name_b = COMPARISONS[pair]
                    if body.get("scenario_a") or body.get("scenario_b"):
                        name_a = body.get("scenario_a") or name_a
                        name_b = body.get("scenario_b") or name_b
                    scenario_a = self._with_mode(self._load_scenario(name_a), body)
                    scenario_b = self._with_mode(self._load_scenario(name_b), body)
                batch_size_a = int(body.get("batch_size_a", body.get("batch_size", 4)))
                batch_size_b = int(body.get("batch_size_b", body.get("batch_size", 4)))
                pause_seconds = float(body.get("pause_seconds", 0))
                fail_a = body.get("fail_after_batches_a")
                fail_b = body.get("fail_after_batches_b")
                if body.get("fail_after_batches") not in (None, "") and fail_a in (None, "") and fail_b in (None, ""):
                    fail_a = body.get("fail_after_batches")
                fail_after_batches_a = None if fail_a in (None, "") else int(fail_a)
                fail_after_batches_b = None if fail_b in (None, "") else int(fail_b)
            except (ValueError, TypeError, json.JSONDecodeError, OSError) as exc:
                self._json(400, {"error": str(exc)})
                return
            if not 1 <= batch_size_a <= 500 or not 1 <= batch_size_b <= 500:
                self._json(400, {"error": "batch_size must be from 1 to 500"})
                return
            if not 0 <= pause_seconds <= 5:
                self._json(400, {"error": "pause_seconds must be from 0 to 5"})
                return
            live = LiveRun()
            comparison_id = uuid.uuid4().hex[:12]
            run_id_a = uuid.uuid4().hex[:12]
            run_id_b = uuid.uuid4().hex[:12]
            with lock:
                comparisons[comparison_id] = live

            def produce() -> None:
                try:
                    for event in stream_comparison(
                        scenario_a,
                        scenario_b,
                        comparison_root,
                        revision,
                        batch_size_a=batch_size_a,
                        batch_size_b=batch_size_b,
                        cancel=live.cancel,
                        fail_after_batches_a=fail_after_batches_a,
                        fail_after_batches_b=fail_after_batches_b,
                        pause_seconds=pause_seconds,
                        comparison_id=comparison_id,
                        run_id_a=run_id_a,
                        run_id_b=run_id_b,
                    ):
                        live.events.put(event)
                finally:
                    live.events.put(None)

            threading.Thread(target=produce, daemon=True).start()
            self._json(
                200,
                {
                    "comparison_id": comparison_id,
                    "run_id_a": run_id_a,
                    "run_id_b": run_id_b,
                },
            )

        def _events(self, store: dict[str, LiveRun], item_id: str) -> None:
            with lock:
                live = store.get(item_id)
            if live is None:
                self._json(404, {"error": f"unknown id {item_id}"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            while True:
                event = live.events.get()
                if event is None:
                    break
                self.wfile.write((json.dumps(event) + "\n").encode("utf-8"))
                self.wfile.flush()

        def _cancel(self, store: dict[str, LiveRun], item_id: str) -> None:
            with lock:
                live = store.get(item_id)
            if live is None:
                self._json(404, {"error": f"unknown id {item_id}"})
                return
            live.cancel.set()
            self._json(200, {"id": item_id, "accepted": True})

        def _static(self, path: str) -> None:
            relative = path.lstrip("/") or "index.html"
            candidate = (web_root / relative).resolve()
            if candidate.is_dir():
                candidate = (candidate / "index.html").resolve()
            if not str(candidate).startswith(str(web_root)) or not candidate.is_file():
                self._json(404, {"error": "not found"})
                return
            content_type = "application/octet-stream"
            if candidate.suffix == ".html":
                content_type = "text/html; charset=utf-8"
            elif candidate.suffix == ".css":
                content_type = "text/css; charset=utf-8"
            elif candidate.suffix == ".js":
                content_type = "text/javascript; charset=utf-8"
            elif candidate.suffix == ".json":
                content_type = "application/json"
            elif candidate.suffix == ".woff2":
                content_type = "font/woff2"
            elif candidate.suffix == ".md":
                content_type = "text/markdown; charset=utf-8"
            data = candidate.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(repo: Path, data_root: Path, revision: str, port: int) -> None:
    make_server(repo, data_root, revision, port).serve_forever()
