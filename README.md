# Prediction of Machine Status

Engineering-grade predictive maintenance project for monitoring industrial machine health, estimating failure risk, and simulating live machine behavior through a browser dashboard.

## Overview

This project combines:

- A machine-learning prediction pipeline
- A real-time monitoring dashboard
- Live machine onboarding and removal
- Fault simulation scenarios
- Public dataset support using the AI4I 2020 predictive maintenance dataset

The system predicts machine condition from telemetry-style sensor inputs such as:

- Vibration
- Temperature
- Pressure
- Current
- RPM
- Load

It then converts those predictions into:

- Failure risk probability
- Health score
- Maintenance urgency
- Machine status: `good`, `moderate`, or `critical`

## Main Features

- Real-time predictive maintenance dashboard
- From-scratch logistic regression model for failure risk estimation
- Synthetic industrial telemetry generation
- AI4I 2020 dataset import from UCI / Kaggle-style public source
- Machine grouping by health status
- Machine onboarding through the UI
- Machine removal from the live fleet
- Alert modal for warning and critical events
- Demo scenarios such as overheating, bearing wear, pressure instability, and electrical spike
- Smoke-test verification suite

## Model

The current prediction engine uses a custom logistic regression classifier implemented in:

- [src/predictive_maintenance/models/health_model.py](src/predictive_maintenance/models/health_model.py)

Training and artifact generation are handled in:

- [src/predictive_maintenance/training.py](src/predictive_maintenance/training.py)

The dashboard shows prediction results through:

- Failure risk
- Health score
- Maintenance horizon
- Status label

## Supported Data Modes

### 1. Synthetic Industrial Dataset

The app can generate its own industrial telemetry with progressive degradation and fault behavior.

Use:

```powershell
python main.py bootstrap
```

### 2. Public AI4I 2020 Dataset

The project also supports the AI4I 2020 Predictive Maintenance Dataset from the UCI Machine Learning Repository.

Reference sources:

- [UCI AI4I 2020 Predictive Maintenance Dataset](https://archive-beta.ics.uci.edu/dataset/601/ai4i%2B2020%2Bpredictive%2Bmaintenance%2Bdataset)
- [Kaggle mirror](https://www.kaggle.com/datasets/stephanmatzka/predictive-maintenance-dataset-ai4i-2020/data)

Use:

```powershell
python main.py bootstrap-ai4i
```

## Project Structure

```text
.
├── main.py
├── README.md
├── requirements.txt
├── client_simulator.py
├── dataset_client.py
├── src/
│   └── predictive_maintenance/
│       ├── api_server.py
│       ├── config.py
│       ├── features.py
│       ├── realtime.py
│       ├── training.py
│       ├── utils.py
│       ├── data/
│       │   ├── external.py
│       │   └── simulate.py
│       ├── models/
│       │   └── health_model.py
│       └── static/
│           ├── app.js
│           ├── index.html
│           └── styles.css
└── tests/
    └── smoke_test.py
```

## Quick Start

Run from the project folder:

```powershell
python main.py bootstrap
python main.py serve
```

Then open:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Commands

```powershell
python main.py bootstrap        # Generate synthetic data and train
python main.py bootstrap-ai4i   # Import AI4I dataset and train
python main.py generate         # Generate synthetic telemetry only
python main.py import-ai4i      # Convert AI4I data into app telemetry format
python main.py train            # Train the model on current dataset
python main.py serve            # Start dashboard and API server
python main.py verify           # Run smoke tests
```

## Dashboard Workflow

Inside the browser dashboard you can:

1. Monitor grouped fleets by `Critical`, `Moderate`, and `Good`
2. Open alert cards for warning and failure events
3. Add new machines with custom baseline values
4. Remove machines from the live fleet
5. Inject instability scenarios
6. Inspect machine prediction metrics in detail

## Presentation Talking Points

If you need to explain the project in a review or viva, you can describe it as:

- A predictive maintenance system for machine-status monitoring
- A browser-based industrial dashboard backed by a machine-learning model
- A project that supports both synthetic telemetry and a cited public dataset
- A simulation environment for demonstrating good, moderate, and critical machine states

## Notes

- The project uses only the Python standard library.
- Generated data and trained artifacts are excluded from git using `.gitignore`.
- Running `bootstrap` switches the project back to synthetic data.
- Running `bootstrap-ai4i` switches the project to the imported public dataset.

## Verification

Run:

```powershell
python main.py verify
```

This checks:

- Synthetic training flow
- AI4I import and training flow
- Realtime engine boot
- Scenario injection
- Machine add/remove behavior

## Future Improvements

- Dataset mode switcher directly in the UI
- Persistent storage for added machines
- More advanced models such as Random Forest, XGBoost, or LSTM
- Database-backed telemetry ingestion
- MQTT / IoT sensor integration
