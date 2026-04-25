from __future__ import annotations

import math
import random
from datetime import datetime

from ..config import DATASET_PATH, MACHINE_IDS
from ..utils import ensure_directories, iso_hours, write_csv


FIELDNAMES = [
    "timestamp",
    "machine_id",
    "vibration",
    "temperature",
    "pressure",
    "current",
    "rpm",
    "load",
    "degradation",
    "failure_within_24h",
    "fault_code",
]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def machine_profile(machine_id: str) -> dict:
    seed = sum(ord(ch) for ch in machine_id)
    random.seed(seed)
    return {
        "vibration": random.uniform(1.8, 2.7),
        "temperature": random.uniform(58.0, 66.0),
        "pressure": random.uniform(28.0, 34.0),
        "current": random.uniform(14.0, 19.0),
        "rpm": random.uniform(1380.0, 1520.0),
        "load": random.uniform(50.0, 72.0),
    }


def generate_dataset(hours: int = 720) -> None:
    ensure_directories()
    start = datetime(2026, 1, 1, 0, 0, 0)
    rows: list[dict] = []

    for machine_id in MACHINE_IDS:
        base = machine_profile(machine_id)
        degradation = random.uniform(0.01, 0.06)
        pending_fault = ""
        fault_started = random.randint(420, 610)

        for hour in range(hours):
            load_wave = 9 * math.sin(hour / 18.0) + 4 * math.sin(hour / 7.0)
            environmental_heat = 2.5 * math.sin(hour / 24.0)
            degradation += random.uniform(0.0004, 0.0018)
            degradation = clamp(degradation, 0.0, 1.15)

            if hour >= fault_started:
                if not pending_fault:
                    pending_fault = random.choice(
                        ["bearing_wear", "overheating", "pressure_instability", "current_spike"]
                    )
                degradation += random.uniform(0.002, 0.005)

            fault_factor = max(0.0, degradation - 0.55)
            vibration = (
                base["vibration"]
                + 0.014 * load_wave
                + degradation * random.uniform(1.1, 2.3)
                + random.uniform(-0.18, 0.18)
            )
            temperature = (
                base["temperature"]
                + 0.12 * load_wave
                + environmental_heat
                + degradation * random.uniform(10.0, 18.0)
                + random.uniform(-1.2, 1.2)
            )
            pressure = (
                base["pressure"]
                - degradation * random.uniform(2.0, 6.0)
                + 0.08 * load_wave
                + random.uniform(-0.7, 0.7)
            )
            current = (
                base["current"]
                + 0.09 * load_wave
                + degradation * random.uniform(4.0, 7.0)
                + random.uniform(-0.6, 0.6)
            )
            rpm = (
                base["rpm"]
                - degradation * random.uniform(120.0, 260.0)
                - 0.9 * load_wave
                + random.uniform(-15.0, 15.0)
            )
            load = clamp(base["load"] + load_wave + random.uniform(-3.0, 3.0), 30.0, 100.0)

            if pending_fault == "bearing_wear":
                vibration += fault_factor * 2.4
                rpm -= fault_factor * 90.0
            elif pending_fault == "overheating":
                temperature += fault_factor * 11.0
                current += fault_factor * 2.2
            elif pending_fault == "pressure_instability":
                pressure -= fault_factor * 5.8
                vibration += fault_factor * 0.9
            elif pending_fault == "current_spike":
                current += fault_factor * 3.6
                temperature += fault_factor * 3.5

            failure_within_24h = 1 if degradation >= 0.88 else 0
            fault_code = pending_fault if degradation >= 0.70 else "normal"

            rows.append(
                {
                    "timestamp": iso_hours(start, hour),
                    "machine_id": machine_id,
                    "vibration": round(clamp(vibration, 0.5, 9.0), 4),
                    "temperature": round(clamp(temperature, 35.0, 130.0), 4),
                    "pressure": round(clamp(pressure, 10.0, 45.0), 4),
                    "current": round(clamp(current, 8.0, 36.0), 4),
                    "rpm": round(clamp(rpm, 900.0, 1800.0), 4),
                    "load": round(load, 4),
                    "degradation": round(clamp(degradation, 0.0, 1.0), 4),
                    "failure_within_24h": failure_within_24h,
                    "fault_code": fault_code,
                }
            )

    write_csv(DATASET_PATH, rows, FIELDNAMES)
    print(f"Generated synthetic telemetry dataset at {DATASET_PATH}")

