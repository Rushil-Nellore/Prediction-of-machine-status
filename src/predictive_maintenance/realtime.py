from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta

from .config import DATASET_PATH, FEATURE_COLUMNS, MACHINE_IDS, MODEL_PATH, SENSOR_COLUMNS
from .features import engineer_features, split_by_machine, vectorize
from .utils import read_csv, read_json


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


SCENARIO_LIBRARY = {
    "bearing_wear": {
        "name": "Bearing Wear",
        "description": "Vibration rises, RPM falls, and failure risk increases as the bearing degrades.",
        "fault_code": "bearing_wear_demo",
        "sensor_bias": {
            "vibration": 2.2,
            "temperature": 5.0,
            "pressure": -1.2,
            "current": 1.4,
            "rpm": -130.0,
            "load": 6.0,
        },
        "risk_bias": 0.22,
        "health_penalty": 16,
        "maintenance_penalty": 42,
        "steps": 10,
        "event_message": "Bearing wear scenario injected. Rising vibration and falling RPM indicate instability.",
    },
    "overheating": {
        "name": "Overheating",
        "description": "Temperature and current surge under load, pushing the machine toward a thermal fault.",
        "fault_code": "overheating_demo",
        "sensor_bias": {
            "vibration": 0.5,
            "temperature": 18.0,
            "pressure": -0.8,
            "current": 3.2,
            "rpm": -60.0,
            "load": 7.5,
        },
        "risk_bias": 0.28,
        "health_penalty": 20,
        "maintenance_penalty": 48,
        "steps": 8,
        "event_message": "Overheating scenario injected. Cooling loss and current draw are moving into a critical range.",
    },
    "pressure_instability": {
        "name": "Pressure Instability",
        "description": "Pressure drops and oscillates, creating unstable process output and warning-level behavior.",
        "fault_code": "pressure_instability_demo",
        "sensor_bias": {
            "vibration": 0.8,
            "temperature": 4.0,
            "pressure": -5.8,
            "current": 1.0,
            "rpm": -45.0,
            "load": 5.0,
        },
        "risk_bias": 0.19,
        "health_penalty": 14,
        "maintenance_penalty": 35,
        "steps": 9,
        "event_message": "Pressure instability scenario injected. Process pressure is dropping below a healthy envelope.",
    },
    "electrical_spike": {
        "name": "Electrical Spike",
        "description": "Current spikes and thermal stress rise, simulating an unstable electrical drive condition.",
        "fault_code": "electrical_spike_demo",
        "sensor_bias": {
            "vibration": 0.4,
            "temperature": 9.0,
            "pressure": -0.6,
            "current": 5.5,
            "rpm": -30.0,
            "load": 4.0,
        },
        "risk_bias": 0.24,
        "health_penalty": 18,
        "maintenance_penalty": 40,
        "steps": 7,
        "event_message": "Electrical spike scenario injected. Current draw is unstable and thermal stress is increasing.",
    },
}


class PredictiveMaintenanceEngine:
    def __init__(self) -> None:
        self.model = read_json(MODEL_PATH)
        rows = read_csv(DATASET_PATH)
        self.feature_rows = engineer_features(rows)
        self.rows_by_machine = split_by_machine(self.feature_rows)
        self.machine_ids = list(self.rows_by_machine.keys())
        self.pointer = 48
        self.history_by_machine: dict[str, deque] = {machine_id: deque(maxlen=60) for machine_id in self.machine_ids}
        self.latest_by_machine: dict[str, dict] = {}
        self.events: deque = deque(maxlen=100)
        self.active_scenarios: dict[str, dict] = {}

        for _ in range(self.pointer):
            self.tick(record_events=False)

    def _scale(self, vector: list[float]) -> list[float]:
        means = self.model["means"]
        stds = self.model["stds"]
        return [(value - avg) / std for value, avg, std in zip(vector, means, stds)]

    def _predict_probability(self, scaled_vector: list[float]) -> float:
        total = self.model["bias"]
        for weight, value in zip(self.model["weights"], scaled_vector):
            total += weight * value
        if total >= 0:
            exp_term = 2.718281828459045 ** (-total)
            return 1 / (1 + exp_term)
        exp_term = 2.718281828459045 ** total
        return exp_term / (1 + exp_term)

    def _anomaly_score(self, row: dict) -> float:
        baseline = self.model["baseline"]
        weighted = 0.0
        weights = {
            "vibration": 0.26,
            "temperature": 0.22,
            "pressure": 0.14,
            "current": 0.16,
            "rpm": 0.12,
            "load": 0.10,
        }
        for sensor in SENSOR_COLUMNS:
            stats = baseline[sensor]
            z = abs((float(row[sensor]) - stats["mean"]) / max(stats["std"], 1.0))
            weighted += weights[sensor] * min(z, 6.0)
        return round(weighted / 6.0, 4)

    def _rul_hours(self, probability: float, anomaly: float, degradation: float) -> int:
        urgency = (probability * 0.55) + (anomaly * 0.25) + (degradation * 0.20)
        hours = int(220 - urgency * 200)
        return max(hours, 4)

    def _status(self, probability: float, health: int) -> str:
        if probability >= self.model["risk_thresholds"]["critical"] or health <= self.model["health_thresholds"]["critical"]:
            return "critical"
        if probability >= self.model["risk_thresholds"]["warning"] or health <= self.model["health_thresholds"]["warning"]:
            return "warning"
        return "normal"

    def _event_message(self, state: dict) -> str:
        scenario = state.get("scenario")
        if scenario:
            label = scenario["name"]
            if state["status"] == "critical":
                return f'{state["machine_id"]} is in {label.lower()} and now requires immediate maintenance attention.'
            if state["status"] == "warning":
                return f'{state["machine_id"]} is in {label.lower()} with elevated failure risk.'
        if state["status"] == "critical":
            return f'{state["machine_id"]} requires immediate maintenance attention.'
        if state["status"] == "warning":
            return f'{state["machine_id"]} is showing elevated failure risk.'
        return f'{state["machine_id"]} operating within normal range.'

    def _apply_scenario(self, machine_id: str, row: dict) -> tuple[dict, dict | None]:
        scenario_state = self.active_scenarios.get(machine_id)
        if not scenario_state:
            return row, None

        definition = scenario_state["definition"]
        step = scenario_state["step"]
        total_steps = max(definition["steps"], 1)
        progress = clamp((step + 1) / total_steps, 0.15, 1.0)
        adjusted = dict(row)

        for sensor, bias in definition["sensor_bias"].items():
            adjusted[sensor] = str(round(float(adjusted[sensor]) + bias * progress, 4))

        adjusted["degradation"] = str(round(clamp(float(adjusted["degradation"]) + 0.18 * progress, 0.0, 1.0), 4))
        adjusted["fault_code"] = definition["fault_code"]
        return adjusted, {
            "key": scenario_state["key"],
            "name": definition["name"],
            "description": definition["description"],
            "progress": round(progress, 2),
        }

    def available_scenarios(self) -> list[dict]:
        return [
            {
                "key": key,
                "name": definition["name"],
                "description": definition["description"],
                "default_steps": definition["steps"],
            }
            for key, definition in SCENARIO_LIBRARY.items()
        ]

    def trigger_scenario(self, machine_id: str, scenario_key: str) -> dict:
        if machine_id not in self.machine_ids:
            raise KeyError(f"Unknown machine_id: {machine_id}")
        if scenario_key not in SCENARIO_LIBRARY:
            raise KeyError(f"Unknown scenario: {scenario_key}")

        definition = SCENARIO_LIBRARY[scenario_key]
        self.active_scenarios[machine_id] = {
            "key": scenario_key,
            "definition": definition,
            "step": 0,
        }
        event = {
            "timestamp": datetime.now().isoformat(),
            "machine_id": machine_id,
            "status": "warning",
            "message": definition["event_message"],
            "fault_code": definition["fault_code"],
        }
        self.events.appendleft(event)
        self.tick(record_events=True)
        return {
            "machine_id": machine_id,
            "scenario": scenario_key,
            "message": definition["event_message"],
            "current": self.latest_by_machine[machine_id],
        }

    def tick(self, record_events: bool = True) -> dict[str, dict]:
        snapshot: dict[str, dict] = {}
        for machine_id in self.machine_ids:
            series = self.rows_by_machine[machine_id]
            row = series[self.pointer % len(series)]
            row, scenario = self._apply_scenario(machine_id, row)
            vector = vectorize(row)
            scaled = self._scale(vector)
            probability = self._predict_probability(scaled)
            anomaly = self._anomaly_score(row)
            if scenario:
                definition = self.active_scenarios[machine_id]["definition"]
                progress = scenario["progress"]
                probability = clamp(probability + definition["risk_bias"] * progress, 0.0, 0.995)
                anomaly = round(clamp(anomaly + 0.22 * progress, 0.0, 1.0), 4)
                health_adjustment = definition["health_penalty"] * progress
                maintenance_penalty = int(definition["maintenance_penalty"] * progress)
            else:
                health_adjustment = 0.0
                maintenance_penalty = 0

            probability = round(probability, 4)
            health_score = int(
                clamp(
                    round(100 - (probability * 55 + anomaly * 40 + float(row["degradation"]) * 20) - health_adjustment),
                    5,
                    99,
                )
            )
            maintenance_in = max(self._rul_hours(probability, anomaly, float(row["degradation"])) - maintenance_penalty, 4)
            status = self._status(probability, health_score)
            state = {
                "timestamp": row["timestamp"],
                "machine_id": machine_id,
                "risk_probability": probability,
                "anomaly_score": anomaly,
                "health_score": health_score,
                "maintenance_in_hours": maintenance_in,
                "status": status,
                "fault_code": row["fault_code"],
                "scenario": scenario,
                "sensors": {column: float(row[column]) for column in SENSOR_COLUMNS},
                "feature_vector": {column: float(row[column]) for column in FEATURE_COLUMNS},
            }
            self.history_by_machine[machine_id].append(state)
            self.latest_by_machine[machine_id] = state
            snapshot[machine_id] = state
            if scenario:
                active = self.active_scenarios[machine_id]
                active["step"] += 1
                if active["step"] >= active["definition"]["steps"]:
                    del self.active_scenarios[machine_id]
            if record_events and status in {"warning", "critical"}:
                self.events.appendleft(
                    {
                        "timestamp": row["timestamp"],
                        "machine_id": machine_id,
                        "status": status,
                        "message": self._event_message(state),
                        "fault_code": row["fault_code"],
                    }
                )

        self.pointer += 1
        return snapshot

    def reset(self) -> None:
        self.pointer = 48
        self.events.clear()
        self.active_scenarios.clear()
        self.history_by_machine = {machine_id: deque(maxlen=60) for machine_id in self.machine_ids}
        self.latest_by_machine = {}
        for _ in range(self.pointer):
            self.tick(record_events=False)

    def fleet_summary(self) -> dict:
        machines = list(self.latest_by_machine.values())
        if not machines:
            return {"machine_count": 0, "critical": 0, "warning": 0, "average_health": 0}
        return {
            "machine_count": len(machines),
            "critical": sum(1 for row in machines if row["status"] == "critical"),
            "warning": sum(1 for row in machines if row["status"] == "warning"),
            "average_health": round(sum(row["health_score"] for row in machines) / len(machines), 2),
            "average_risk": round(sum(row["risk_probability"] for row in machines) / len(machines), 4),
        }

    def _mini_history(self, machine_id: str, points: int = 12) -> list[dict]:
        history = list(self.history_by_machine[machine_id])[-points:]
        return [
            {
                "risk_probability": row["risk_probability"],
                "health_score": row["health_score"],
                "bearing_strain": row.get("feature_vector", {}).get("mechanical_stress", 0.0),
                "power_draw": row.get("feature_vector", {}).get("power_proxy", 0.0),
                "thermal_stress": row.get("feature_vector", {}).get("thermal_stress", 0.0)
            }
            for row in history
        ]

    def machine_list(self) -> list[dict]:
        machines: list[dict] = []
        for machine_id in self.machine_ids:
            current = dict(self.latest_by_machine[machine_id])
            current["mini_history"] = self._mini_history(machine_id)
            machines.append(current)
        return machines

    def machine_detail(self, machine_id: str) -> dict:
        return {
            "current": self.latest_by_machine[machine_id],
            "history": list(self.history_by_machine[machine_id]),
        }

    def machine_templates(self) -> list[dict]:
        templates = []
        for machine_id in self.machine_ids:
            state = self.latest_by_machine.get(machine_id)
            if not state:
                continue
            templates.append(
                {
                    "machine_id": machine_id,
                    "status": state["status"],
                    "health_score": state["health_score"],
                    "sensors": state["sensors"],
                }
            )
        return templates

    def _build_machine_series(self, machine_id: str, template_id: str, sensor_profile: dict[str, float]) -> list[dict]:
        template_series = self.rows_by_machine[template_id]
        template_start = template_series[0]
        offsets = {sensor: sensor_profile[sensor] - float(template_start[sensor]) for sensor in SENSOR_COLUMNS}

        built_rows: list[dict] = []
        previous: dict[str, float] | None = None
        for template_row in template_series:
            row = dict(template_row)
            row["machine_id"] = machine_id
            for sensor in SENSOR_COLUMNS:
                adjusted = float(template_row[sensor]) + offsets[sensor]
                row[sensor] = round(adjusted, 4)

            if previous is None:
                previous = {sensor: float(row[sensor]) for sensor in SENSOR_COLUMNS}

            row["vibration_delta"] = round(float(row["vibration"]) - previous["vibration"], 4)
            row["temperature_delta"] = round(float(row["temperature"]) - previous["temperature"], 4)
            row["pressure_delta"] = round(float(row["pressure"]) - previous["pressure"], 4)
            row["current_delta"] = round(float(row["current"]) - previous["current"], 4)
            row["rpm_delta"] = round(float(row["rpm"]) - previous["rpm"], 4)
            row["load_delta"] = round(float(row["load"]) - previous["load"], 4)
            row["power_proxy"] = round(float(row["current"]) * max(float(row["load"]), 1.0) / 100.0, 4)
            row["thermal_stress"] = round(float(row["temperature"]) * float(row["current"]) / 100.0, 4)
            row["mechanical_stress"] = round(
                float(row["vibration"]) * max(float(row["load"]), 1.0) / max(float(row["rpm"]), 1.0) * 1000.0,
                4,
            )
            row["fault_code"] = "normal"
            previous = {sensor: float(row[sensor]) for sensor in SENSOR_COLUMNS}
            built_rows.append(row)

        return built_rows

    def add_machine(self, machine_id: str, template_id: str, sensor_profile: dict[str, float]) -> dict:
        normalized_id = machine_id.strip().upper()
        if not normalized_id:
            raise ValueError("Machine ID is required.")
        if normalized_id in self.machine_ids:
            raise ValueError("Machine ID already exists.")
        if template_id not in self.machine_ids:
            raise ValueError("Template machine not found.")

        for sensor in SENSOR_COLUMNS:
            if sensor not in sensor_profile:
                raise ValueError(f"Missing sensor value: {sensor}")

        self.rows_by_machine[normalized_id] = self._build_machine_series(normalized_id, template_id, sensor_profile)
        self.machine_ids.append(normalized_id)
        self.history_by_machine[normalized_id] = deque(maxlen=60)

        for lookback in range(60):
            index = self.pointer - 60 + lookback
            row = self.rows_by_machine[normalized_id][index % len(self.rows_by_machine[normalized_id])]
            vector = vectorize(row)
            scaled = self._scale(vector)
            probability = round(self._predict_probability(scaled), 4)
            anomaly = self._anomaly_score(row)
            health_score = int(clamp(round(100 - (probability * 55 + anomaly * 40 + float(row["degradation"]) * 20)), 5, 99))
            maintenance_in = self._rul_hours(probability, anomaly, float(row["degradation"]))
            status = self._status(probability, health_score)
            state = {
                "timestamp": row["timestamp"],
                "machine_id": normalized_id,
                "risk_probability": probability,
                "anomaly_score": anomaly,
                "health_score": health_score,
                "maintenance_in_hours": maintenance_in,
                "status": status,
                "fault_code": row["fault_code"],
                "scenario": None,
                "sensors": {column: float(row[column]) for column in SENSOR_COLUMNS},
                "feature_vector": {column: float(row[column]) for column in FEATURE_COLUMNS},
            }
            self.history_by_machine[normalized_id].append(state)
            self.latest_by_machine[normalized_id] = state

        self.events.appendleft(
            {
                "timestamp": datetime.now().isoformat(),
                "machine_id": normalized_id,
                "status": "normal",
                "message": f"{normalized_id} has been added to the fleet using {template_id} as the onboarding template.",
                "fault_code": "machine_onboarded",
            }
        )
        return self.machine_detail(normalized_id)

    def remove_machine(self, machine_id: str) -> dict:
        normalized_id = machine_id.strip().upper()
        if normalized_id not in self.machine_ids:
            raise ValueError("Machine not found.")
        if len(self.machine_ids) <= 1:
            raise ValueError("At least one machine must remain in the fleet.")

        self.machine_ids.remove(normalized_id)
        self.rows_by_machine.pop(normalized_id, None)
        self.history_by_machine.pop(normalized_id, None)
        self.latest_by_machine.pop(normalized_id, None)
        self.active_scenarios.pop(normalized_id, None)
        self.events = deque(
            [event for event in self.events if event.get("machine_id") != normalized_id],
            maxlen=100,
        )
        self.events.appendleft(
            {
                "timestamp": datetime.now().isoformat(),
                "machine_id": normalized_id,
                "status": "normal",
                "message": f"{normalized_id} has been removed from the live fleet.",
                "fault_code": "machine_removed",
            }
        )
        return {"removed_machine_id": normalized_id, "remaining_machines": len(self.machine_ids)}

    def ingest_telemetry(self, machine_id: str, sensors: dict[str, float]) -> dict:
        if machine_id not in self.latest_by_machine:
            raise ValueError(f"Machine {machine_id} must be onboarded first.")
            
        previous_state = self.latest_by_machine[machine_id]
        prev_sensors = previous_state["sensors"]
        
        row = {
            "machine_id": machine_id,
            "timestamp": datetime.now().isoformat(),
            **sensors,
        }
        
        row["vibration_delta"] = sensors.get("vibration", 0.0) - prev_sensors.get("vibration", 0.0)
        row["temperature_delta"] = sensors.get("temperature", 0.0) - prev_sensors.get("temperature", 0.0)
        row["pressure_delta"] = sensors.get("pressure", 0.0) - prev_sensors.get("pressure", 0.0)
        row["current_delta"] = sensors.get("current", 0.0) - prev_sensors.get("current", 0.0)
        row["rpm_delta"] = sensors.get("rpm", 0.0) - prev_sensors.get("rpm", 0.0)
        row["load_delta"] = sensors.get("load", 0.0) - prev_sensors.get("load", 0.0)
        
        row["power_proxy"] = (sensors.get("current", 0.0) * max(sensors.get("load", 0.0), 1.0)) / 100.0
        row["thermal_stress"] = (sensors.get("temperature", 0.0) * sensors.get("current", 0.0)) / 100.0
        row["mechanical_stress"] = (sensors.get("vibration", 0.0) * max(sensors.get("load", 0.0), 1.0) / max(sensors.get("rpm", 0.0), 1.0)) * 1000.0
        row["degradation"] = previous_state.get("feature_vector", {}).get("degradation", 0.0)
        row["fault_code"] = "normal"
        
        vector = vectorize(row)
        scaled = self._scale(vector)
        probability = round(self._predict_probability(scaled), 4)
        anomaly = self._anomaly_score(row)
        health_score = int(clamp(round(100 - (probability * 55 + anomaly * 40 + float(row["degradation"]) * 20)), 5, 99))
        
        state = {
            "timestamp": row["timestamp"],
            "machine_id": machine_id,
            "risk_probability": probability,
            "anomaly_score": anomaly,
            "health_score": health_score,
            "maintenance_in_hours": self._rul_hours(probability, anomaly, float(row["degradation"])),
            "status": self._status(probability, health_score),
            "fault_code": "normal",
            "scenario": None,
            "sensors": sensors,
            "feature_vector": {col: float(row.get(col, 0.0)) for col in FEATURE_COLUMNS},
        }
        
        self.history_by_machine[machine_id].append(state)
        self.latest_by_machine[machine_id] = state
        return state


    def health(self) -> dict:
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "model_loaded": True,
            "dataset_loaded": True,
            "machines": len(self.latest_by_machine),
            "active_scenarios": len(self.active_scenarios),
            "server_time_plus_one_hour": (datetime.now() + timedelta(hours=1)).isoformat(),
        }
