from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
GENERATED_DIR = DATA_DIR / "generated"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
STATIC_DIR = Path(__file__).resolve().parent / "static"

DATASET_PATH = GENERATED_DIR / "machine_telemetry.csv"
AI4I_ARCHIVE_PATH = GENERATED_DIR / "ai4i_2020.zip"
AI4I_EXTRACTED_DIR = GENERATED_DIR / "ai4i_2020"
AI4I_SOURCE_PATH = AI4I_EXTRACTED_DIR / "ai4i2020.csv"
MODEL_PATH = ARTIFACTS_DIR / "predictive_model.json"
SUMMARY_PATH = ARTIFACTS_DIR / "training_summary.json"

APP_HOST = "127.0.0.1"
APP_PORT = 8000

MACHINE_IDS = [
    "MX-101",
    "MX-102",
    "MX-103",
    "MX-104",
    "MX-105",
    "MX-106",
]

SENSOR_COLUMNS = [
    "vibration",
    "temperature",
    "pressure",
    "current",
    "rpm",
    "load",
]

FEATURE_COLUMNS = [
    "vibration",
    "temperature",
    "pressure",
    "current",
    "rpm",
    "load",
    "vibration_delta",
    "temperature_delta",
    "pressure_delta",
    "current_delta",
    "rpm_delta",
    "load_delta",
    "power_proxy",
    "thermal_stress",
    "mechanical_stress",
]
