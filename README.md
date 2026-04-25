<div align="center">
  <h1>⚙️ Predictive Maintenance Control Center</h1>
  <p><strong>Industrial-Grade IoT Telemetry & Machine Learning Dashboard</strong></p>
  
  [![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?style=flat-square&logo=python&logoColor=white)]()
  [![Chart.js](https://img.shields.io/badge/Chart.js-Line_Graphs-ff69b4.svg?style=flat-square&logo=chartdotjs&logoColor=white)]()
  [![Status](https://img.shields.io/badge/Status-Active-success.svg?style=flat-square)]()
</div>

<hr/>

## 📖 Overview

This project is a full-stack **Engineering-Grade Predictive Maintenance System**. It bridges the gap between raw industrial sensor telemetry and actionable machine-learning insights. 

The platform continuously monitors a live fleet of simulated (or streaming dataset) machines, processing telemetry like **Vibration**, **Temperature**, **Pressure**, **Current**, **RPM**, and **Load**. It runs this data through a custom Logistic Regression model to instantly predict:

- 🔴 **Failure Risk Probability**
- 🟢 **Overall Health Score**
- ⏳ **Maintenance Urgency (RUL)**
- 📊 **Live Machine Status** (`Good`, `Moderate`, or `Critical`)

---

## ✨ Key Features

- 🖥️ **Real-Time IoT Dashboard**: A stunning, dark-mode browser interface built with HTML/CSS/JS.
- 📈 **Live Telemetry Streaming**: Features beautiful, responsive SVG and **Chart.js** line graphs charting Bearing Strain, Power Draw, and Thermal Stress in real-time.
- 🧠 **Machine Learning Engine**: Custom-built logistic regression classifier that computes anomaly scores and predicts mechanical failure.
- 🚀 **Live Machine Management**: Seamlessly onboard new machines with baseline sensor templates, or remove failing machines from the live fleet.
- 🚨 **Instant Alerts System**: Top-right dropdown notification system for immediate warning and critical failure events.
- 📊 **Public Dataset Support**: Native integration with the **AI4I 2020 Predictive Maintenance Dataset** from the UCI Machine Learning Repository / Kaggle.

---

## 🏗️ Architecture & Project Structure

The project is built entirely on the Python Standard Library (no heavy framework bloat) and vanilla web technologies.

```text
📁 ml mp/
├── 📄 main.py                 # Core CLI application entrypoint
├── 📄 client_simulator.py     # Edge-device simulator (pushes random live data)
├── 📄 dataset_client.py       # Dataset streaming client (pushes historical failing data)
├── 📁 data/                   # Auto-generated CSV datasets & model artifacts
└── 📁 src/predictive_maintenance/
    ├── 📄 api_server.py       # REST API HTTP Server
    ├── 📄 realtime.py         # The core Stateful Simulation Engine
    ├── 📄 features.py         # Telemetry feature engineering (Strain, Stress, Power)
    ├── 📄 training.py         # Model training pipeline
    ├── 📁 models/             # Machine Learning logic (health_model.py)
    └── 📁 static/             # Frontend UI (index.html, styles.css, app.js)
```

---

## 🚀 Quick Start Guide

### 1. Boot up the Backend Server
First, generate the initial dataset, train the AI model, and start the API server:
```powershell
python main.py bootstrap
python main.py serve
```
> *The server will start running at [http://127.0.0.1:8000](http://127.0.0.1:8000)*

### 2. Stream Live Edge Data
Open a **second terminal window** in the project folder and run the streaming client. This script acts like a physical IoT device attached to a failing machine, pushing telemetry to your dashboard every second!
```powershell
python dataset_client.py
```
Watch your dashboard as `MX-CRITICAL-01` appears and its risk meter begins to climb!

---

## 🛠️ Command Line Reference

The `main.py` CLI is your control center for the backend:

| Command | Description |
|---------|-------------|
| `python main.py serve` | **Start the Dashboard** and REST API Server. |
| `python main.py bootstrap` | Generate synthetic telemetry data and train the AI model. |
| `python main.py bootstrap-ai4i`| Import the public AI4I Kaggle dataset and train the model. |
| `python main.py generate` | *Generate synthetic telemetry only.* |
| `python main.py train` | *Train the model on the current dataset.* |
| `python main.py verify` | Run the internal Smoke Test verification suite. |

---

## 🎓 Presentation / Viva Talking Points
If you are presenting this project, hit these major engineering concepts:
1. **End-to-End Pipeline**: We built everything from data generation, to feature engineering, to model training, to live API serving, and finally frontend data visualization.
2. **Event-Driven Architecture**: The frontend passively consumes an API, while independent edge clients (`dataset_client.py`) push telemetry over HTTP.
3. **Advanced UI/UX**: The dashboard prioritizes cognitive load. It categorizes fleets by health, uses modern SVG/Canvas graphs for data density, and employs a non-intrusive alert notification system.
4. **Real-World Ready**: Instead of just running a model on a static CSV file, this project proves the model works in a continuous, live streaming environment.

---

## 📝 Notes

- The project uses only the Python standard library.
- Generated data and trained artifacts are excluded from git using `.gitignore`.
- Running `bootstrap` switches the project back to synthetic data.
- Running `bootstrap-ai4i` switches the project to the imported public dataset.

## 🔮 Future Improvements

- Dataset mode switcher directly in the UI
- Persistent storage for added machines
- More advanced models such as Random Forest, XGBoost, or LSTM
- Database-backed telemetry ingestion
- MQTT / IoT sensor integration

---
<div align="center">
  <i>Built for the future of Industrial AI.</i>
</div>
