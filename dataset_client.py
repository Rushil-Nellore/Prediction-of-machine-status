import csv
import time
import requests
from pathlib import Path

# Connects directly to the generated telemetry dataset
DATASET_PATH = Path(__file__).resolve().parent / "data" / "generated" / "machine_telemetry.csv"
SERVER_URL = "http://127.0.0.1:8000/api/telemetry"
MACHINE_ID = "MX-CRITICAL-01"

def stream_critical_data():
    if not DATASET_PATH.exists():
        print(f"Dataset not found at {DATASET_PATH}")
        return

    # Extract a sequence of rows that represent a machine degrading towards failure
    critical_sequence = []
    with open(DATASET_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Look for rows where the machine is failing
            if row.get("failure_within_24h") == "1" or row.get("fault_code", "normal") != "normal":
                critical_sequence.append(row)
                
    if not critical_sequence:
        print("No critical rows found in dataset!")
        return
        
    print(f"Found {len(critical_sequence)} critical data points in dataset.")
    print(f"Beginning real-time stream of failing machine data...")
    
    # Grab the very first row to onboard the machine
    first_row = critical_sequence[0]
    base_sensors = {
        "vibration": float(first_row["vibration"]),
        "temperature": float(first_row["temperature"]),
        "pressure": float(first_row["pressure"]),
        "current": float(first_row["current"]),
        "rpm": float(first_row["rpm"]),
        "load": float(first_row["load"])
    }
    
    try:
        print(f"Onboarding machine {MACHINE_ID} to the backend...")
        requests.post("http://127.0.0.1:8000/api/machines", json={
            "machine_id": MACHINE_ID,
            "template_id": "MX-101",
            "sensors": base_sensors
        })
    except Exception as e:
        print(f"Onboarding error: {e}")

    # Stream the critical sequence row by row
    for row in critical_sequence:
        sensors = {
            "vibration": float(row["vibration"]),
            "temperature": float(row["temperature"]),
            "pressure": float(row["pressure"]),
            "current": float(row["current"]),
            "rpm": float(row["rpm"]),
            "load": float(row["load"])
        }
        
        try:
            response = requests.post(SERVER_URL, json={
                "machine_id": MACHINE_ID,
                "sensors": sensors
            })
            if response.status_code == 200:
                data = response.json()
                print(f"[{time.strftime('%X')}] Pushed real dataset row | Failure Risk: {data.get('risk_probability')*100:.1f}%, Status: {data.get('status').upper()}")
            else:
                print(f"Error from server: {response.text}")
        except requests.exceptions.ConnectionError:
            print("Could not connect to server. Is the API running?")
            
        time.sleep(1) # Stream at 1 data point per second

if __name__ == "__main__":
    stream_critical_data()
