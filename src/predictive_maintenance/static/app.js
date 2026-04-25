const SENSOR_KEYS = ["vibration", "temperature", "pressure", "current", "rpm", "load"];

const state = {
  selectedMachine: null,
  machines: [],
  events: [],
  detail: null,
  scenarios: [],
  templates: [],
};

let chartInstance = null;

async function getJson(url, options = {}) {
  const response = await fetch(url, options);
  return response.json();
}

function renderChart(history) {
  const ctx = document.getElementById("metricsChart").getContext("2d");
  const section = document.getElementById("telemetrySection");
  const title = document.getElementById("telemetryTitle");

  if (!history || history.length === 0) {
    section.style.display = "none";
    return;
  }

  section.style.display = "block";
  title.textContent = `${state.selectedMachine} Telemetry`;

  const labels = history.map(row => {
    const date = new Date(row.timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  });

  const bearingStrain = history.map(row => row.feature_vector?.mechanical_stress || 0);
  const powerDraw = history.map(row => row.feature_vector?.power_proxy || 0);
  const thermalStress = history.map(row => row.feature_vector?.thermal_stress || 0);

  if (chartInstance) {
    chartInstance.data.labels = labels;
    chartInstance.data.datasets[0].data = bearingStrain;
    chartInstance.data.datasets[1].data = powerDraw;
    chartInstance.data.datasets[2].data = thermalStress;
    chartInstance.update('none');
  } else {
    Chart.defaults.color = "#9ec2cb";
    Chart.defaults.font.family = '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif';

    chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Bearing Strain',
            data: bearingStrain,
            borderColor: '#ffbf69',
            backgroundColor: 'rgba(255, 191, 105, 0.1)',
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4
          },
          {
            label: 'Power Draw',
            data: powerDraw,
            borderColor: '#39d0b8',
            backgroundColor: 'rgba(57, 208, 184, 0.1)',
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4
          },
          {
            label: 'Thermal Stress',
            data: thermalStress,
            borderColor: '#ff6b6b',
            backgroundColor: 'rgba(255, 107, 107, 0.1)',
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: { position: 'top' },
          tooltip: {
            backgroundColor: 'rgba(8, 20, 27, 0.9)',
            titleColor: '#e9f5f7',
            bodyColor: '#e9f5f7',
            borderColor: 'rgba(140, 196, 219, 0.16)',
            borderWidth: 1
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
            ticks: { maxTicksLimit: 10 }
          },
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false }
          }
        }
      }
    });
  }
}

function statCard(label, value) {
  return `
    <article class="stat">
      <div class="stat-label">${label}</div>
      <div class="stat-value">${value}</div>
    </article>
  `;
}

function normalizeTrend(history) {
  const recent = history.slice(-12);
  while (recent.length < 12) {
    recent.unshift(recent[0] || { risk_probability: 0, health_score: 0 });
  }
  return recent;
}

function machineTrend(history) {
  const normalized = normalizeTrend(history);
  
  const bearing = normalized.map(row => row.bearing_strain ?? 0);
  const power = normalized.map(row => row.power_draw ?? 0);
  
  const maxBearing = Math.max(...bearing, 10);
  const maxPower = Math.max(...power, 10);

  const width = 240;
  const height = 40;
  const step = width / (Math.max(normalized.length - 1, 1));
  
  const bearingPath = bearing.map((val, i) => `${i === 0 ? 'M' : 'L'} ${i * step} ${height - ((val / maxBearing) * height)}`).join(' ');
  const powerPath = power.map((val, i) => `${i === 0 ? 'M' : 'L'} ${i * step} ${height - ((val / maxPower) * height)}`).join(' ');

  const latestRisk = normalized.length ? Math.round(normalized[normalized.length - 1].risk_probability * 100) : 0;
  const latestHealth = normalized.length ? Math.round(normalized[normalized.length - 1].health_score) : 0;

  return `
    <div class="machine-trend">
      <svg viewBox="0 0 ${width} ${height}" class="trend-svg" preserveAspectRatio="none">
        <path d="${bearingPath}" stroke="#ffbf69" fill="none" stroke-width="2" vector-effect="non-scaling-stroke"/>
        <path d="${powerPath}" stroke="#39d0b8" fill="none" stroke-width="2" vector-effect="non-scaling-stroke"/>
      </svg>
    </div>
    <div class="trend-legend">
      <span class="risk">Bearing Strain</span>
      <span class="health">Power Draw</span>
    </div>
    <div class="trend-values">
      <span>Predicted risk: ${latestRisk}%</span>
      <span>Health: ${latestHealth}/100</span>
    </div>
  `;
}

function machineCard(machine) {
  const riskPercent = Math.round(machine.risk_probability * 100);
  return `
    <article class="machine-card ${state.selectedMachine === machine.machine_id ? "active" : ""}" data-machine="${machine.machine_id}">
      <div class="machine-top">
        <div>
          <h3>${machine.machine_id}</h3>
          <p>${machine.fault_code.replaceAll("_", " ")}</p>
        </div>
        <span class="badge ${machine.status}">${machine.status}</span>
      </div>
      ${machineTrend(machine.mini_history || [])}
      <div class="machine-bottom">
        <div>
          <p>Health Score</p>
          <strong>${machine.health_score}/100</strong>
        </div>
        <div class="meter"><span style="width:${riskPercent}%"></span></div>
        <div>
          <p>Failure Risk</p>
          <strong>${riskPercent}%</strong>
        </div>
        <div>
          <p>Maintenance In</p>
          <strong>${machine.maintenance_in_hours} h</strong>
        </div>
      </div>
      <div class="card-actions">
        <button class="secondary remove-card-button" data-remove-machine="${machine.machine_id}" type="button">Remove</button>
      </div>
    </article>
  `;
}

function machineGroup(title, description, statusClass, machines) {
  return `
    <section class="machine-group">
      <div class="group-header">
        <div>
          <h3>${title}</h3>
          <p>${description}</p>
        </div>
        <span class="group-chip ${statusClass}">${machines.length}</span>
      </div>
      ${
        machines.length
          ? `<div class="machine-grid">${machines.map(machineCard).join("")}</div>`
          : `<div class="empty-group">No machines currently in this group.</div>`
      }
    </section>
  `;
}

function renderStats(fleet) {
  document.getElementById("stats").innerHTML = [
    statCard("Machines", fleet.machine_count),
    statCard("Average Health", fleet.average_health),
    statCard("Average Risk", `${Math.round(fleet.average_risk * 100)}%`),
    statCard("Warnings", fleet.warning),
    statCard("Critical", fleet.critical),
  ].join("");
}

function wireMachineCards() {
  const machineSelect = document.getElementById("scenarioMachine");
  machineSelect.innerHTML = state.machines
    .map((machine) => `<option value="${machine.machine_id}">${machine.machine_id}</option>`)
    .join("");
  if (state.selectedMachine) {
    machineSelect.value = state.selectedMachine;
  }

  document.querySelectorAll(".machine-card").forEach((card) => {
    card.addEventListener("click", async (event) => {
      if (event.target.closest(".remove-card-button")) return;
      state.selectedMachine = card.dataset.machine;
      machineSelect.value = state.selectedMachine;
      await loadMachineDetail();
      renderMachines();
      showMachineModal();
    });
  });
}

function renderMachines() {
  const critical = state.machines.filter((machine) => machine.status === "critical");
  const warning = state.machines.filter((machine) => machine.status === "warning");
  const normal = state.machines.filter((machine) => machine.status === "normal");

  document.getElementById("machineSections").innerHTML = [
    machineGroup("Critical Machines", "Immediate maintenance attention required.", "critical", critical),
    machineGroup("Moderate Machines", "Machines in warning state with rising risk.", "warning", warning),
    machineGroup("Good Machines", "Machines operating in a healthy range.", "normal", normal),
  ].join("");

  wireMachineCards();
}

function renderEvents() {
  const feed = document.getElementById("eventFeed");
  const badge = document.getElementById("alertBadge");
  if (!state.events.length) {
    feed.innerHTML = `<div class="event"><strong>No recent alerts</strong><small>Simulation is currently stable.</small></div>`;
    badge.classList.add("hidden");
    return;
  }
  badge.textContent = state.events.length;
  badge.classList.remove("hidden");
  feed.innerHTML = state.events
    .map(
      (event) => `
        <div class="event ${event.status}">
          <strong>${event.machine_id} - ${event.status.toUpperCase()}</strong>
          <p>${event.message}</p>
          <small>${event.timestamp} - ${event.fault_code}</small>
        </div>
      `
    )
    .join("");
}

function renderScenarioOptions() {
  const scenarioSelect = document.getElementById("scenarioSelect");
  if (!state.scenarios.length) {
    scenarioSelect.innerHTML = `<option value="">No scenarios available</option>`;
    document.getElementById("scenarioHelp").innerHTML = "Scenario presets are unavailable.";
    return;
  }

  scenarioSelect.innerHTML = state.scenarios
    .map((scenario) => `<option value="${scenario.key}">${scenario.name}</option>`)
    .join("");
  updateScenarioHelp();
}

function updateScenarioHelp() {
  const scenarioKey = document.getElementById("scenarioSelect").value;
  const scenario = state.scenarios.find((item) => item.key === scenarioKey);
  const help = document.getElementById("scenarioHelp");
  if (!scenario) {
    help.textContent = "Choose a scenario to see what unstable behavior it will create.";
    return;
  }
  help.innerHTML = `<strong>${scenario.name}</strong><p>${scenario.description}</p><small>Typical duration: ${scenario.default_steps} simulation steps.</small>`;
}

function renderTemplateOptions() {
  const templateSelect = document.getElementById("templateMachine");
  templateSelect.innerHTML = state.templates
    .map((template) => `<option value="${template.machine_id}">${template.machine_id}</option>`)
    .join("");
  if (!templateSelect.value && state.templates.length) {
    templateSelect.value = state.templates[0].machine_id;
  }
  populateTemplateSensorValues();
}

function populateTemplateSensorValues() {
  const templateId = document.getElementById("templateMachine").value;
  const template = state.templates.find((item) => item.machine_id === templateId);
  if (!template) return;

  document.getElementById("inputVibration").value = template.sensors.vibration.toFixed(2);
  document.getElementById("inputTemperature").value = template.sensors.temperature.toFixed(2);
  document.getElementById("inputPressure").value = template.sensors.pressure.toFixed(2);
  document.getElementById("inputCurrent").value = template.sensors.current.toFixed(2);
  document.getElementById("inputRpm").value = template.sensors.rpm.toFixed(2);
  document.getElementById("inputLoad").value = template.sensors.load.toFixed(2);
  document.getElementById("machineFormHelp").innerHTML =
    `<strong>${template.machine_id}</strong><p>Template status: ${template.status}. You can keep these baseline values or edit them before adding the new machine.</p>`;
}

function showMachineModal() {
  if (!state.detail) return;
  const current = state.detail.current;
  const modal = document.getElementById("machineModal");
  document.getElementById("modalTitle").textContent = `${current.machine_id} detailed machine card`;
  document.getElementById("modalContent").innerHTML = `
    <div class="modal-metrics">
      <div class="modal-metric"><span>Health Score</span><strong>${current.health_score}/100</strong></div>
      <div class="modal-metric"><span>Failure Risk</span><strong>${Math.round(current.risk_probability * 100)}%</strong></div>
      <div class="modal-metric"><span>Anomaly Score</span><strong>${current.anomaly_score.toFixed(2)}</strong></div>
      <div class="modal-metric"><span>Maintenance In</span><strong>${current.maintenance_in_hours} h</strong></div>
    </div>
    <div class="sensor-grid">
      <article><span>Status</span><strong>${current.status}</strong></article>
      <article><span>Fault Code</span><strong>${current.fault_code}</strong></article>
      <article><span>Scenario</span><strong>${current.scenario ? current.scenario.name : "None"}</strong></article>
      <article><span>Vibration</span><strong>${current.sensors.vibration.toFixed(2)}</strong></article>
      <article><span>Temperature</span><strong>${current.sensors.temperature.toFixed(2)} C</strong></article>
      <article><span>Pressure</span><strong>${current.sensors.pressure.toFixed(2)} bar</strong></article>
      <article><span>Current</span><strong>${current.sensors.current.toFixed(2)} A</strong></article>
      <article><span>RPM</span><strong>${current.sensors.rpm.toFixed(0)}</strong></article>
      <article><span>Load</span><strong>${current.sensors.load.toFixed(1)} %</strong></article>
    </div>
  `;
  modal.classList.remove("hidden");
}

function hideMachineModal() {
  document.getElementById("machineModal").classList.add("hidden");
}

function showAlertsModal() {
  document.getElementById("alertsModal").classList.remove("hidden");
}

function hideAlertsModal() {
  document.getElementById("alertsModal").classList.add("hidden");
}

async function loadScenarios() {
  const payload = await getJson("/api/scenarios");
  state.scenarios = payload.scenarios;
  renderScenarioOptions();
}

async function loadTemplates() {
  const payload = await getJson("/api/machine-templates");
  state.templates = payload.templates;
  renderTemplateOptions();
}

async function loadFleet() {
  const payload = await getJson("/api/machines");
  state.machines = payload.machines;
  if (!state.selectedMachine && state.machines.length) {
    state.selectedMachine = state.machines[0].machine_id;
  }
  if (state.selectedMachine && !state.machines.some((machine) => machine.machine_id === state.selectedMachine)) {
    state.selectedMachine = state.machines[0]?.machine_id ?? null;
  }
  renderStats(payload.fleet);
  renderMachines();
}

async function loadEvents() {
  const payload = await getJson("/api/events");
  state.events = payload.events.slice(0, 20);
  renderEvents();
}

async function loadMachineDetail() {
  if (!state.selectedMachine) {
    state.detail = null;
    if (chartInstance) {
      document.getElementById("telemetrySection").style.display = "none";
    }
    return;
  }
  state.detail = await getJson(`/api/machines/${state.selectedMachine}`);
  if (state.detail && state.detail.history) {
    renderChart(state.detail.history);
  }
}

async function tickSimulation() {
  await getJson("/api/simulate/tick", { method: "POST" });
  await refresh();
}

async function resetSimulation() {
  await getJson("/api/simulate/reset", { method: "POST" });
  await refresh();
}

async function injectScenario() {
  const machineId = document.getElementById("scenarioMachine").value;
  const scenarioKey = document.getElementById("scenarioSelect").value;
  if (!machineId || !scenarioKey) {
    return;
  }
  state.selectedMachine = machineId;
  await getJson("/api/simulate/scenario", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ machine_id: machineId, scenario: scenarioKey }),
  });
  await refresh();
}

async function addMachine(event) {
  event.preventDefault();
  const machineId = document.getElementById("newMachineId").value.trim();
  const templateId = document.getElementById("templateMachine").value;
  const sensors = Object.fromEntries(
    SENSOR_KEYS.map((sensor) => [sensor, Number(document.getElementById(`input${sensor.charAt(0).toUpperCase()}${sensor.slice(1)}`).value)])
  );

  const response = await getJson("/api/machines", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      machine_id: machineId,
      template_id: templateId,
      sensors,
    }),
  });

  if (response.error) {
    document.getElementById("machineFormHelp").innerHTML = `<strong>Could not add machine</strong><p>${response.error}</p>`;
    return;
  }

  document.getElementById("newMachineId").value = "";
  document.getElementById("machineFormHelp").innerHTML =
    `<strong>${response.current.machine_id} added</strong><p>The new machine is now part of the live fleet and can be monitored like the others.</p>`;
  state.selectedMachine = response.current.machine_id;
  await refresh();
  await loadTemplates();
  showMachineModal();
}

async function removeMachine() {
  if (!state.selectedMachine) return;
  await removeMachineById(state.selectedMachine);
}

async function removeMachineById(machineId) {
  const response = await getJson("/api/machines/remove", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ machine_id: machineId }),
  });

  if (response.error) {
    alert(`Could not remove machine: ${response.error}`);
    return;
  }

  alert(`${machineId} removed successfully.`);
  hideMachineModal();
  state.selectedMachine = null;
  await refresh();
  await loadTemplates();
}

async function refresh() {
  await loadFleet();
  await loadEvents();
  await loadMachineDetail();
}

document.getElementById("tickButton").addEventListener("click", tickSimulation);
document.getElementById("resetButton").addEventListener("click", resetSimulation);
document.getElementById("injectScenarioButton").addEventListener("click", injectScenario);
document.getElementById("alertsToggleButton").addEventListener("click", showAlertsModal);
document.getElementById("scenarioSelect").addEventListener("change", updateScenarioHelp);
document.getElementById("scenarioMachine").addEventListener("change", (event) => {
  state.selectedMachine = event.target.value;
  renderMachines();
});
document.getElementById("templateMachine").addEventListener("change", populateTemplateSensorValues);
document.getElementById("machineForm").addEventListener("submit", addMachine);
document.getElementById("removeMachineButton").addEventListener("click", removeMachine);
document.getElementById("machineSections").addEventListener("click", async (event) => {
  const button = event.target.closest(".remove-card-button");
  if (!button) return;
  event.stopPropagation();
  await removeMachineById(button.dataset.removeMachine);
});
document.getElementById("closeModalButton").addEventListener("click", hideMachineModal);
document.getElementById("closeAlertsButton").addEventListener("click", hideAlertsModal);
document.getElementById("machineModal").addEventListener("click", (event) => {
  if (event.target.id === "machineModal") {
    hideMachineModal();
  }
});
document.getElementById("alertsModal").addEventListener("click", (event) => {
  if (event.target.id === "alertsModal") {
    hideAlertsModal();
  }
});

Promise.all([loadScenarios(), loadTemplates()]).then(refresh);
setInterval(refresh, 5000);
