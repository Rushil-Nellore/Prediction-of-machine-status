from __future__ import annotations

import csv
import math
import urllib.request
import zipfile
from datetime import datetime, timedelta

from ..config import AI4I_ARCHIVE_PATH, AI4I_EXTRACTED_DIR, AI4I_SOURCE_PATH, DATASET_PATH
from ..utils import ensure_directories, write_csv


AI4I_URL = "https://cdn.uci-ics-mlr-prod.aws.uci.edu/601/ai4i%2B2020%2Bpredictive%2Bmaintenance%2Bdataset.zip"

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


def ensure_ai4i_source(download_if_missing: bool = True) -> None:
    ensure_directories()
    if AI4I_SOURCE_PATH.exists():
        return
    if not AI4I_ARCHIVE_PATH.exists():
        if not download_if_missing:
            raise FileNotFoundError(f"AI4I archive not found at {AI4I_ARCHIVE_PATH}")
        urllib.request.urlretrieve(AI4I_URL, AI4I_ARCHIVE_PATH)
    AI4I_EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(AI4I_ARCHIVE_PATH, "r") as archive:
        archive.extractall(AI4I_EXTRACTED_DIR)
    if not AI4I_SOURCE_PATH.exists():
        raise FileNotFoundError(f"AI4I CSV not found after extraction: {AI4I_SOURCE_PATH}")


def _fault_code(row: dict) -> str:
    if row["TWF"] == "1":
        return "tool_wear_failure"
    if row["HDF"] == "1":
        return "heat_dissipation_failure"
    if row["PWF"] == "1":
        return "power_failure"
    if row["OSF"] == "1":
        return "overstrain_failure"
    if row["RNF"] == "1":
        return "random_failure"
    return "normal"


def _machine_id(index: int, quality: str) -> str:
    bucket = index // 250
    return f"AI4I-{quality}-{bucket + 1:02d}"


def import_ai4i_dataset() -> None:
    ensure_ai4i_source(download_if_missing=False)
    start = datetime(2026, 2, 1, 0, 0, 0)
    rows: list[dict] = []
    sequence_by_machine: dict[str, int] = {}

    with AI4I_SOURCE_PATH.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for index, source_row in enumerate(reader):
            quality = source_row["Type"].strip()
            machine_id = _machine_id(index, quality)
            step = sequence_by_machine.get(machine_id, 0)
            sequence_by_machine[machine_id] = step + 1

            air_temp = float(source_row["Air temperature [K]"]) - 273.15
            process_temp = float(source_row["Process temperature [K]"]) - 273.15
            rpm = float(source_row["Rotational speed [rpm]"])
            torque = float(source_row["Torque [Nm]"])
            tool_wear = float(source_row["Tool wear [min]"])
            failure = int(source_row["Machine failure"])
            heat_gap = process_temp - air_temp
            power_kw = torque * (2 * math.pi * rpm / 60.0) / 1000.0

            quality_factor = {"L": 0.92, "M": 1.0, "H": 1.08}.get(quality, 1.0)
            vibration = clamp(1.2 + torque / 24.0 + tool_wear / 145.0 + failure * 1.6, 0.5, 9.0)
            temperature = clamp(process_temp, 20.0, 120.0)
            pressure = clamp(34.0 - heat_gap * 1.55 + (1.08 - quality_factor) * 4.5 - failure * 1.2, 10.0, 45.0)
            current = clamp(10.0 + power_kw / 1.55 + failure * 1.5, 8.0, 36.0)
            load = clamp(35.0 + torque * 1.08 + tool_wear / 8.0, 20.0, 100.0)
            degradation = clamp(tool_wear / 255.0 + failure * 0.18 + max(0.0, 40.0 - heat_gap) / 100.0, 0.0, 1.0)

            rows.append(
                {
                    "timestamp": (start + timedelta(minutes=step * 15)).isoformat(),
                    "machine_id": machine_id,
                    "vibration": round(vibration, 4),
                    "temperature": round(temperature, 4),
                    "pressure": round(pressure, 4),
                    "current": round(current, 4),
                    "rpm": round(clamp(rpm, 900.0, 1800.0), 4),
                    "load": round(load, 4),
                    "degradation": round(degradation, 4),
                    "failure_within_24h": failure,
                    "fault_code": _fault_code(source_row),
                }
            )

    write_csv(DATASET_PATH, rows, FIELDNAMES)
    print(f"Imported AI4I 2020 dataset into telemetry format at {DATASET_PATH}")
