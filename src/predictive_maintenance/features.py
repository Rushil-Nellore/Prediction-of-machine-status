from __future__ import annotations

from collections import defaultdict

from .config import FEATURE_COLUMNS


def to_float(row: dict, key: str) -> float:
    return float(row[key])


def engineer_features(rows: list[dict]) -> list[dict]:
    previous_by_machine: dict[str, dict] = {}
    features: list[dict] = []

    for row in rows:
        machine_id = row["machine_id"]
        prev = previous_by_machine.get(machine_id)

        vibration = to_float(row, "vibration")
        temperature = to_float(row, "temperature")
        pressure = to_float(row, "pressure")
        current = to_float(row, "current")
        rpm = to_float(row, "rpm")
        load = to_float(row, "load")

        if prev is None:
            prev = {
                "vibration": vibration,
                "temperature": temperature,
                "pressure": pressure,
                "current": current,
                "rpm": rpm,
                "load": load,
            }

        feature_row = {
            "timestamp": row["timestamp"],
            "machine_id": machine_id,
            "label": int(row["failure_within_24h"]),
            "fault_code": row["fault_code"],
            "degradation": float(row["degradation"]),
            "vibration": vibration,
            "temperature": temperature,
            "pressure": pressure,
            "current": current,
            "rpm": rpm,
            "load": load,
            "vibration_delta": vibration - prev["vibration"],
            "temperature_delta": temperature - prev["temperature"],
            "pressure_delta": pressure - prev["pressure"],
            "current_delta": current - prev["current"],
            "rpm_delta": rpm - prev["rpm"],
            "load_delta": load - prev["load"],
            "power_proxy": current * max(load, 1.0) / 100.0,
            "thermal_stress": temperature * current / 100.0,
            "mechanical_stress": vibration * max(load, 1.0) / max(rpm, 1.0) * 1000.0,
        }
        previous_by_machine[machine_id] = {
            "vibration": vibration,
            "temperature": temperature,
            "pressure": pressure,
            "current": current,
            "rpm": rpm,
            "load": load,
        }
        features.append(feature_row)

    return features


def split_by_machine(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["machine_id"]].append(row)
    return dict(grouped)


def vectorize(row: dict) -> list[float]:
    return [float(row[column]) for column in FEATURE_COLUMNS]

