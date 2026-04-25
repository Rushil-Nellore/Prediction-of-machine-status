from __future__ import annotations

from statistics import mean

from .config import DATASET_PATH, FEATURE_COLUMNS, MODEL_PATH, SENSOR_COLUMNS, SUMMARY_PATH
from .features import engineer_features, vectorize
from .models.health_model import LogisticRegressionModel
from .utils import ensure_directories, read_csv, write_json


def standardize(x_rows: list[list[float]]) -> tuple[list[list[float]], list[float], list[float]]:
    means = [mean(column) for column in zip(*x_rows)]
    stds: list[float] = []
    standardized: list[list[float]] = []

    for index, column in enumerate(zip(*x_rows)):
        values = list(column)
        column_mean = means[index]
        variance = sum((value - column_mean) ** 2 for value in values) / max(len(values), 1)
        stds.append(variance ** 0.5 if variance > 1e-9 else 1.0)

    for row in x_rows:
        standardized.append([(value - avg) / std for value, avg, std in zip(row, means, stds)])

    return standardized, means, stds


def baseline_stats(feature_rows: list[dict]) -> dict:
    healthy_rows = [row for row in feature_rows if row["label"] == 0 and row["degradation"] < 0.65]
    baseline = {}
    for sensor in SENSOR_COLUMNS:
        values = [float(row[sensor]) for row in healthy_rows]
        avg = sum(values) / max(len(values), 1)
        variance = sum((value - avg) ** 2 for value in values) / max(len(values), 1)
        baseline[sensor] = {"mean": avg, "std": variance ** 0.5 if variance > 1e-9 else 1.0}
    return baseline


def evaluate(model: LogisticRegressionModel, x_rows: list[list[float]], y_rows: list[int]) -> dict:
    tp = fp = tn = fn = 0
    probabilities: list[float] = []
    for features, label in zip(x_rows, y_rows):
        probability = model.predict_probability(features)
        prediction = 1 if probability >= 0.5 else 0
        probabilities.append(probability)
        if prediction == 1 and label == 1:
            tp += 1
        elif prediction == 1 and label == 0:
            fp += 1
        elif prediction == 0 and label == 0:
            tn += 1
        else:
            fn += 1

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    accuracy = (tp + tn) / max(tp + tn + fp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "average_risk": round(sum(probabilities) / max(len(probabilities), 1), 4),
    }


def train_model() -> None:
    ensure_directories()
    raw_rows = read_csv(DATASET_PATH)
    feature_rows = engineer_features(raw_rows)
    x = [vectorize(row) for row in feature_rows]
    y = [int(row["label"]) for row in feature_rows]
    x_scaled, means, stds = standardize(x)

    split_index = int(0.8 * len(x_scaled))
    x_train = x_scaled[:split_index]
    y_train = y[:split_index]
    x_test = x_scaled[split_index:]
    y_test = y[split_index:]

    model = LogisticRegressionModel(weights=[0.0] * len(FEATURE_COLUMNS), bias=0.0)
    model.train(x_train, y_train)

    baseline = baseline_stats(feature_rows)
    metrics = evaluate(model, x_test, y_test)

    payload = {
        "feature_columns": FEATURE_COLUMNS,
        "weights": model.weights,
        "bias": model.bias,
        "means": means,
        "stds": stds,
        "baseline": baseline,
        "metrics": metrics,
        "risk_thresholds": {
            "warning": 0.45,
            "critical": 0.72,
        },
        "health_thresholds": {
            "warning": 65,
            "critical": 40,
        },
    }
    write_json(MODEL_PATH, payload)
    write_json(
        SUMMARY_PATH,
        {
            "dataset_rows": len(raw_rows),
            "feature_rows": len(feature_rows),
            "machine_count": len({row["machine_id"] for row in raw_rows}),
            "dataset_profile": "ai4i_2020_imported" if any(row["machine_id"].startswith("AI4I-") for row in raw_rows) else "synthetic_industrial",
            "metrics": metrics,
            "feature_columns": FEATURE_COLUMNS,
        },
    )
    print(f"Trained predictive model and saved artifacts to {MODEL_PATH}")
    print(f"Evaluation metrics: {metrics}")
