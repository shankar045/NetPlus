const $ = (id) => document.getElementById(id);
let latencyChart = null;
let toastTimer = null;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[char]));
}

function formatBytes(bytes) {
  if (!Number.isFinite(Number(bytes))) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = Math.max(0, Number(bytes));
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit === 0 ? 0 : 2)} ${units[unit]}`;
}

function formatRate(bytesPerSecond) {
  return `${formatBytes(bytesPerSecond)}<small>/s</small>`;
}

function formatTime(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"});
}

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2800);
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
}

async function postJson(url, data) {
  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}

async function refreshSummary() {
  try {
    const data = await getJson("/api/summary");
    $("totalChecks").textContent = data.total_checks;
    $("successfulChecks").textContent = data.successful_checks;
    $("failedChecks").textContent = data.failed_checks;
    $("avgLatency").textContent = data.average_latency_ms == null ? "—" : data.average_latency_ms;
  } catch (error) {
    console.warn("Summary refresh failed:", error);
  }
}

function initChart() {
  if (typeof Chart === "undefined") {
    $("chartCount").textContent = "Chart library unavailable";
    return;
  }
  const context = $("latencyChart").getContext("2d");
  const gradient = context.createLinearGradient(0, 0, 0, 260);
  gradient.addColorStop(0, "rgba(118, 101, 238, 0.22)");
  gradient.addColorStop(1, "rgba(118, 101, 238, 0.01)");
  latencyChart = new Chart(context, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label: "TCP latency",
        data: [],
        borderColor: "#7665ee",
        backgroundColor: gradient,
        fill: true,
        tension: 0.35,
        borderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor: "#ffffff",
        pointBorderColor: "#7665ee"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {legend: {display: false}, tooltip: {displayColors: false}},
      scales: {
        x: {grid: {display: false}, border: {display: false}, ticks: {color: "#9ba4b7", maxTicksLimit: 6, font: {size: 9}}},
        y: {beginAtZero: true, border: {display: false, dash: [4, 4]}, grid: {color: "#eef0f6"}, ticks: {color: "#9ba4b7", font: {size: 9}, callback: (value) => `${value} ms`}}
      }
    }
  });
}

function renderHistory(rows) {
  const successful = rows.filter((row) => row.status === "UP" && row.latency_ms != null);
  if (latencyChart) {
    latencyChart.data.labels = successful.map((row) => formatTime(row.checked_at));
    latencyChart.data.datasets[0].data = successful.map((row) => row.latency_ms);
    latencyChart.update();
  }
  $("chartCount").textContent = `${successful.length} successful data point${successful.length === 1 ? "" : "s"}`;

  if (!rows.length) {
    $("historyBody").innerHTML = '<tr><td colspan="5" class="empty-table">No checks saved yet. Run a test above.</td></tr>';
    return;
  }
  $("historyBody").innerHTML = [...rows].reverse().slice(0, 12).map((row) => `
    <tr>
      <td class="target-name">${escapeHtml(row.name)}</td>
      <td class="host-cell">${escapeHtml(row.host)}:${row.port}</td>
      <td><span class="status-badge ${row.status === "UP" ? "up" : "down"}">${row.status}</span></td>
      <td>${row.latency_ms == null ? "—" : `${Number(row.latency_ms).toFixed(2)} ms`}</td>
      <td>${formatTime(row.checked_at)}</td>
    </tr>`).join("");
}

async function refreshHistory() {
  try {
    const rows = await getJson("/api/history?limit=40");
    renderHistory(rows);
  } catch (error) {
    console.warn("History refresh failed:", error);
  }
}

async function refreshAlerts() {
  try {
    const alerts = await getJson("/api/alerts");
    $("alertCount").textContent = alerts.length;
    if (!alerts.length) {
      $("alertsList").innerHTML = '<div class="empty-alerts">No alerts yet. Run a test to begin.</div>';
      return;
    }
    $("alertsList").innerHTML = alerts.map((alert) => `
      <div class="alert-item">
        <div class="alert-symbol">!</div>
        <div class="alert-copy"><strong>${escapeHtml(alert.name)} · ${escapeHtml(alert.host)}:${alert.port}</strong><p>${escapeHtml(alert.alert)}</p></div>
        <span class="alert-time">${formatTime(alert.checked_at)}</span>
      </div>`).join("");
  } catch (error) {
    console.warn("Alerts refresh failed:", error);
  }
}

async function refreshTraffic() {
  try {
    const data = await getJson("/api/traffic");
    $("uploadRate").innerHTML = formatRate(data.upload_bytes_per_sec);
    $("downloadRate").innerHTML = formatRate(data.download_bytes_per_sec);
    $("bytesSent").textContent = formatBytes(data.bytes_sent);
    $("bytesReceived").textContent = formatBytes(data.bytes_recv);
    $("trafficUpdated").textContent = `Updated ${formatTime(data.sampled_at)}`;
  } catch (error) {
    $("trafficUpdated").textContent = "Traffic stats unavailable";
    console.warn("Traffic refresh failed:", error);
  }
}

function renderResult(result) {
  const success = result.status === "UP";
  const box = $("resultBox");
  box.className = `result-box ${success ? "success" : "failure"}`;
  box.innerHTML = `
    <div class="result-symbol">${success ? "✓" : "!"}</div>
    <div><strong>${escapeHtml(result.name)} — ${success ? "Connection successful" : "Connection failed"}</strong>
    <p>${escapeHtml(result.message)}${result.latency_ms == null ? "" : ` · ${Number(result.latency_ms).toFixed(2)} ms`}${result.alert ? ` · ${escapeHtml(result.alert)}` : ""}</p></div>`;
}

async function runTest(name, host, port) {
  const button = $("testButton");
  button.disabled = true;
  button.innerHTML = '<span>◌</span> Testing connection…';
  try {
    const result = await postJson("/api/monitor", {name, host, port});
    renderResult(result);
    showToast(result.status === "UP" ? "Connection test saved." : "Test completed; connection failed.");
    await Promise.all([refreshSummary(), refreshHistory(), refreshAlerts()]);
  } catch (error) {
    showToast(error.message || "Could not run the connection test.");
  } finally {
    button.disabled = false;
    button.innerHTML = '<span>⌁</span> Test connection <span class="button-arrow">→</span>';
  }
}

$("monitorForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const name = $("hostName").value.trim() || $("hostInput").value.trim();
  const host = $("hostInput").value.trim();
  const port = Number($("portInput").value);
  if (!host || !Number.isInteger(port) || port < 1 || port > 65535) {
    showToast("Enter a hostname and a port between 1 and 65535.");
    return;
  }
  runTest(name, host, port);
});

document.querySelectorAll(".target-chip").forEach((button) => {
  button.addEventListener("click", () => {
    $("hostName").value = button.dataset.name;
    $("hostInput").value = button.dataset.host;
    $("portInput").value = button.dataset.port;
    runTest(button.dataset.name, button.dataset.host, Number(button.dataset.port));
  });
});

initChart();
refreshSummary();
refreshHistory();
refreshAlerts();
refreshTraffic();
setInterval(refreshTraffic, 4000);
setInterval(() => Promise.all([refreshSummary(), refreshHistory(), refreshAlerts()]), 15000);
