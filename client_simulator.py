import requests
import time
import random

# Configuration
SERVER_URL = "http://127.0.0.1:8000/api/telemetry"
MACHINE_ID = "MX-REAL-01"

# Initial base values for the sensors
base_sensors = {
    "vibration": 1.2,
    "temperature": 45.0,
    "pressure": 120.0,
    "current": 15.0,
    "rpm": 1500.0,
    "load": 80.0
}

# Add the machine to the server first so it knows about it
try:
    print(f"Onboarding machine {MACHINE_ID} to the server...")
    requests.post("http://127.0.0.1:8000/api/machines", json={
        "machine_id": MACHINE_ID,
        "template_id": "MX-101", # Use an existing machine as the template baseline
        "sensors": base_sensors
    })
    print("Machine onboarded successfully!")
except Exception as e:
    print(f"Warning during onboarding: {e}")

print("Starting live telemetry push...")

# Run the simulation loop
while True:
    # Add random walks to simulate live data
    # (In a real scenario, you would read these from a physical sensor, e.g. via serial port)
    base_sensors["vibration"] += random.uniform(-0.05, 0.05)
    base_sensors["temperature"] += random.uniform(-0.2, 0.2)
    base_sensors["pressure"] += random.uniform(-1.0, 1.0)
    base_sensors["current"] += random.uniform(-0.1, 0.1)
    base_sensors["rpm"] += random.uniform(-5.0, 5.0)
    base_sensors["load"] += random.uniform(-0.5, 0.5)

    # Ensure values don't go strictly negative where they shouldn't
    for key in base_sensors:
        if base_sensors[key] < 0:
            base_sensors[key] = 0.0

    payload = {
        "machine_id": MACHINE_ID,
        "sensors": base_sensors
    }
    
    try:
        response = requests.post(SERVER_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"[{time.strftime('%X')}] Pushed data. Server says -> Health: {data.get('health_score')}, Status: {data.get('status')}")
        else:
            print(f"Error from server: {response.text}")
    except requests.exceptions.ConnectionError:
        print("Could not connect to server. Is the API running?")
        
    time.sleep(1) # Wait 1 second before next push
