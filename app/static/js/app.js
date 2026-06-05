(function () {
  const page = document.body.dataset.page;
  const statusEl = document.getElementById("page-status");
  let bandwidthChart = null;

  function setStatus(message) {
    if (statusEl) statusEl.textContent = message;
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  }

  function fmtBytes(bytes) {
    if (bytes === null || bytes === undefined) return "-";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let value = Number(bytes);
    let index = 0;
    while (value >= 1024 && index < units.length - 1) {
      value /= 1024;
      index += 1;
    }
    return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
  }

  function fmtDate(value) {
    if (!value) return "-";
    return new Date(value).toLocaleString("vi-VN");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function renderAlertItem(alert) {
    return `
      <article class="list-item ${escapeHtml(alert.severity || "info")} ${alert.acknowledged ? "ack" : ""}">
        <strong>${escapeHtml(alert.message)}</strong>
        <p class="muted">${fmtDate(alert.created_at)}</p>
        ${alert.acknowledged ? "" : `<button data-ack="${alert.id}" type="button">Đã xử lý</button>`}
      </article>
    `;
  }

  async function loadDashboard() {
    const data = await api("/api/dashboard");
    document.getElementById("metric-online").textContent = data.devices.online;
    document.getElementById("metric-unknown").textContent = data.devices.unknown;
    document.getElementById("metric-cpu").textContent = `${Math.round(data.system.cpu_percent)}%`;
    document.getElementById("metric-memory").textContent = `${Math.round(data.system.memory_percent)}%`;
    document.getElementById("network-interface").textContent = data.network.interface || "-";
    document.getElementById("network-subnet").textContent = data.network.subnet || "-";
    document.getElementById("network-sent").textContent = fmtBytes(data.network.bytes_sent);
    document.getElementById("network-recv").textContent = fmtBytes(data.network.bytes_recv);
    document.getElementById("latest-alerts").innerHTML =
      data.latest_alerts.length ? data.latest_alerts.map(renderAlertItem).join("") : `<p class="muted">Chưa có cảnh báo.</p>`;
    setStatus("Dữ liệu dashboard đã cập nhật");
  }

  async function loadDevices() {
    const devices = await api("/api/devices");
    document.getElementById("device-count").textContent = `${devices.length} thiết bị`;
    document.getElementById("devices-table").innerHTML = devices.map((device) => `
      <tr data-device="${device.id}">
        <td><span class="status ${device.is_online ? "online" : "offline"}">${device.is_online ? "Online" : "Offline"}</span></td>
        <td>
          <input data-field="custom_name" value="${escapeHtml(device.custom_name)}" placeholder="${escapeHtml(device.hostname || device.ip)}">
          <p class="muted">${escapeHtml(device.hostname || "")}</p>
        </td>
        <td>${escapeHtml(device.ip)}</td>
        <td><code>${escapeHtml(device.mac)}</code></td>
        <td>${escapeHtml(device.vendor || "-")}</td>
        <td><textarea data-field="notes">${escapeHtml(device.notes)}</textarea></td>
        <td><input data-field="is_known" type="checkbox" ${device.is_known ? "checked" : ""}></td>
        <td><button data-save="${device.id}" type="button">Lưu</button></td>
      </tr>
    `).join("");
    setStatus("Danh sách thiết bị đã cập nhật");
  }

  async function saveDevice(button) {
    const row = button.closest("tr");
    const id = row.dataset.device;
    const payload = {};
    row.querySelectorAll("[data-field]").forEach((field) => {
      payload[field.dataset.field] = field.type === "checkbox" ? field.checked : field.value;
    });
    await api(`/api/devices/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    setStatus("Đã lưu thiết bị");
    await loadDevices();
  }

  async function loadWifi() {
    const data = await api("/api/wifi");
    document.getElementById("wifi-ssid").textContent = data.ssid || "-";
    document.getElementById("wifi-signal").textContent = data.signal_dbm ? `${data.signal_quality} (${data.signal_dbm} dBm)` : data.signal_quality;
    document.getElementById("wifi-channel").textContent = data.channel || "-";
    document.getElementById("wifi-band").textContent = data.band || "-";
    document.getElementById("wifi-interface").textContent = data.interface || "-";
    document.getElementById("wifi-frequency").textContent = data.frequency_mhz ? `${data.frequency_mhz} MHz` : "-";
    document.getElementById("wifi-bitrate").textContent = data.tx_bitrate || "-";
    document.getElementById("wifi-source").textContent = data.source || "-";
    setStatus("Thông tin WiFi đã cập nhật");
  }

  async function loadBandwidth(range = "hour") {
    const data = await api(`/api/bandwidth?range=${encodeURIComponent(range)}`);
    const labels = data.samples.map((sample) => fmtDate(sample.sampled_at));
    const upload = data.samples.map((sample) => sample.upload_delta);
    const download = data.samples.map((sample) => sample.download_delta);
    const canvas = document.getElementById("bandwidth-chart");
    if (!window.Chart) {
      canvas.replaceWith(document.createTextNode("Không tải được Chart.js."));
      return;
    }
    if (bandwidthChart) bandwidthChart.destroy();
    bandwidthChart = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Upload", data: upload, borderColor: "#c4562d", backgroundColor: "rgba(196, 86, 45, 0.12)", tension: 0.25 },
          { label: "Download", data: download, borderColor: "#116466", backgroundColor: "rgba(17, 100, 102, 0.12)", tension: 0.25 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { ticks: { callback: fmtBytes } } },
        plugins: { tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmtBytes(ctx.raw)}` } } },
      },
    });
    setStatus("Biểu đồ băng thông đã cập nhật");
  }

  async function loadRouter() {
    const data = await api("/api/router/status");
    document.getElementById("router-url").textContent = data.config.base_url;
    document.getElementById("router-reachable").textContent = data.reachable ? "Có phản hồi" : "Không phản hồi";
    document.getElementById("router-code").textContent = data.status_code || "-";
    document.getElementById("router-latency").textContent = data.latency_ms ? `${data.latency_ms} ms` : "-";
    document.getElementById("router-message").textContent = data.message || "-";
    const form = document.getElementById("router-form");
    form.base_url.value = data.config.base_url || "";
    form.username.value = data.config.username || "";
    setStatus("Trạng thái router đã cập nhật");
  }

  async function saveRouter(event) {
    event.preventDefault();
    const form = event.currentTarget;
    await api("/api/router/settings", {
      method: "POST",
      body: JSON.stringify({
        base_url: form.base_url.value,
        username: form.username.value,
        password: form.password.value,
      }),
    });
    form.password.value = "";
    await loadRouter();
  }

  async function loadAlerts() {
    const alerts = await api("/api/alerts");
    document.getElementById("alert-count").textContent = `${alerts.length} cảnh báo`;
    document.getElementById("alerts-list").innerHTML =
      alerts.length ? alerts.map(renderAlertItem).join("") : `<p class="muted">Chưa có cảnh báo.</p>`;
    setStatus("Cảnh báo đã cập nhật");
  }

  async function ackAlert(button) {
    await api(`/api/alerts/${button.dataset.ack}/ack`, { method: "POST" });
    if (page === "alerts") await loadAlerts();
    if (page === "dashboard") await loadDashboard();
  }

  async function loadSettings() {
    const [settings, tools] = await Promise.all([api("/api/settings"), api("/api/settings/tools")]);
    const form = document.getElementById("settings-form");
    form.network_interface.value = settings.network_interface || "";
    form.network_subnet.value = settings.network_subnet || "";
    form.scan_interval_seconds.value = settings.scan_interval_seconds || 60;
    form.mock_data.checked = Boolean(settings.mock_data);
    document.getElementById("tools-list").innerHTML = tools.map((tool) => `
      <article class="tool">
        <strong>${escapeHtml(tool.name)}</strong>
        <span class="pill">${tool.available ? "Có" : "Thiếu"}</span>
        <code>${escapeHtml(tool.available ? (tool.path || tool.version) : tool.install_command)}</code>
      </article>
    `).join("");
    setStatus("Cài đặt đã cập nhật");
  }

  async function saveSettings(event) {
    event.preventDefault();
    const form = event.currentTarget;
    await api("/api/settings", {
      method: "POST",
      body: JSON.stringify({
        network_interface: form.network_interface.value,
        network_subnet: form.network_subnet.value,
        scan_interval_seconds: Number(form.scan_interval_seconds.value || 60),
        mock_data: form.mock_data.checked ? "true" : "false",
      }),
    });
    await loadSettings();
  }

  async function runScan() {
    setStatus("Đang quét mạng");
    await api("/api/scan", { method: "POST" });
    if (page === "dashboard") await loadDashboard();
    if (page === "devices") await loadDevices();
    if (page === "alerts") await loadAlerts();
  }

  function bindSocket() {
    if (typeof io !== "function") return;
    const socket = io();
    socket.on("dashboard:update", () => { if (page === "dashboard") loadDashboard().catch(console.error); });
    socket.on("devices:update", () => { if (page === "devices") loadDevices().catch(console.error); });
    socket.on("alerts:new", () => { if (page === "alerts") loadAlerts().catch(console.error); });
    socket.on("bandwidth:update", () => { if (page === "bandwidth") loadBandwidth().catch(console.error); });
  }

  document.addEventListener("click", (event) => {
    const saveButton = event.target.closest("[data-save]");
    const ackButton = event.target.closest("[data-ack]");
    if (saveButton) saveDevice(saveButton).catch((error) => setStatus(error.message));
    if (ackButton) ackAlert(ackButton).catch((error) => setStatus(error.message));
  });

  document.getElementById("scan-now")?.addEventListener("click", () => runScan().catch((error) => setStatus(error.message)));
  document.getElementById("router-form")?.addEventListener("submit", (event) => saveRouter(event).catch((error) => setStatus(error.message)));
  document.getElementById("settings-form")?.addEventListener("submit", (event) => saveSettings(event).catch((error) => setStatus(error.message)));
  document.getElementById("bandwidth-range")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-range]");
    if (!button) return;
    document.querySelectorAll("#bandwidth-range button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    loadBandwidth(button.dataset.range).catch((error) => setStatus(error.message));
  });

  const initializers = {
    dashboard: loadDashboard,
    devices: loadDevices,
    wifi: loadWifi,
    bandwidth: loadBandwidth,
    router: loadRouter,
    alerts: loadAlerts,
    settings: loadSettings,
  };

  if (initializers[page]) {
    initializers[page]().catch((error) => setStatus(error.message));
  }
  bindSocket();
})();
