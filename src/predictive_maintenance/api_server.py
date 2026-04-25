from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .config import DATASET_PATH, MODEL_PATH, STATIC_DIR
from .data.simulate import generate_dataset
from .realtime import PredictiveMaintenanceEngine
from .training import train_model


ENGINE: PredictiveMaintenanceEngine | None = None


class ApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_json(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json(ENGINE.health())
            return
        if parsed.path == "/api/machines":
            self._send_json({"fleet": ENGINE.fleet_summary(), "machines": ENGINE.machine_list()})
            return
        if parsed.path == "/api/machine-templates":
            self._send_json({"templates": ENGINE.machine_templates()})
            return
        if parsed.path.startswith("/api/machines/"):
            machine_id = parsed.path.rsplit("/", 1)[-1]
            if machine_id not in ENGINE.latest_by_machine:
                self._send_json({"error": "Machine not found"}, status=404)
                return
            self._send_json(ENGINE.machine_detail(machine_id))
            return
        if parsed.path == "/api/events":
            self._send_json({"events": list(ENGINE.events)})
            return
        if parsed.path == "/api/scenarios":
            self._send_json({"scenarios": ENGINE.available_scenarios()})
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/simulate/tick":
            self._send_json({"machines": ENGINE.tick(), "fleet": ENGINE.fleet_summary()})
            return
        if parsed.path == "/api/simulate/reset":
            ENGINE.reset()
            self._send_json({"fleet": ENGINE.fleet_summary(), "machines": ENGINE.machine_list()})
            return
        if parsed.path == "/api/simulate/scenario":
            payload = self._read_json_body()
            machine_id = payload.get("machine_id")
            scenario_key = payload.get("scenario")
            try:
                result = ENGINE.trigger_scenario(machine_id, scenario_key)
            except KeyError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json(result)
            return
        if parsed.path == "/api/predict":
            payload = self._read_json_body()
            machine_id = payload.get("machine_id")
            if not machine_id or machine_id not in ENGINE.latest_by_machine:
                self._send_json({"error": "Provide a valid machine_id from the existing fleet."}, status=400)
                return
            self._send_json(ENGINE.machine_detail(machine_id)["current"])
            return
        if parsed.path == "/api/telemetry":
            payload = self._read_json_body()
            machine_id = payload.get("machine_id", "")
            sensors = payload.get("sensors", {})
            try:
                normalized_sensors = {key: float(value) for key, value in sensors.items()}
                result = ENGINE.ingest_telemetry(machine_id, normalized_sensors)
            except (ValueError, TypeError) as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json(result)
            return
        if parsed.path == "/api/machines":
            payload = self._read_json_body()
            machine_id = payload.get("machine_id", "")
            template_id = payload.get("template_id", "")
            sensors = payload.get("sensors", {})
            try:
                normalized_sensors = {key: float(value) for key, value in sensors.items()}
                detail = ENGINE.add_machine(machine_id, template_id, normalized_sensors)
            except (ValueError, TypeError) as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json(detail, status=201)
            return
        if parsed.path == "/api/machines/remove":
            payload = self._read_json_body()
            machine_id = payload.get("machine_id", "")
            try:
                result = ENGINE.remove_machine(machine_id)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json(result)
            return
        self._send_json({"error": "Unknown endpoint"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        return


def run_server(host: str, port: int) -> None:
    global ENGINE
    if ENGINE is None:
        if not DATASET_PATH.exists():
            generate_dataset()
        if not MODEL_PATH.exists():
            train_model()
        ENGINE = PredictiveMaintenanceEngine()

    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"Predictive maintenance server running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
