const roleSelect = document.getElementById("roleFilter");
const monthSelect = document.getElementById("monthFilter");
const refreshBtn = document.getElementById("refreshBtn");
const statusEl = document.getElementById("status");
const warningBanner = document.getElementById("warningBanner");
const fetchedAtEl = document.getElementById("fetchedAt");
const tableBody = document.querySelector("#reportTable tbody");

let userChart, trendChart;
let optionsPopulated = false;

async function fetchReport(params) {
  const qs = new URLSearchParams(params);
  const res = await fetch(`/api/report?${qs.toString()}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

function populateOptions(roles, months) {
  if (optionsPopulated) return;
  for (const r of roles) {
    const opt = document.createElement("option");
    opt.value = r;
    opt.textContent = r;
    roleSelect.appendChild(opt);
  }
  for (const m of months) {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = m;
    monthSelect.appendChild(opt);
  }
  optionsPopulated = true;
}

function renderTable(rows) {
  tableBody.innerHTML = "";
  for (const r of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${r.month}</td>
      <td>${r.name ?? "(unknown)"}</td>
      <td>${r.email ?? "-"}</td>
      <td>${r.role}</td>
      <td>${r.uncached_input_tokens.toLocaleString()}</td>
      <td>${r.output_tokens.toLocaleString()}</td>
      <td>${r.cache_read_input_tokens.toLocaleString()}</td>
      <td>${r.cache_write_tokens.toLocaleString()}</td>
      <td><strong>${r.total_tokens.toLocaleString()}</strong></td>
      <td>$${r.estimated_cost_usd.toFixed(2)}</td>
      <td>${r.models.join(", ")}</td>
    `;
    tableBody.appendChild(tr);
  }
}

function renderUserChart(rows) {
  const byUser = new Map();
  for (const r of rows) {
    const label = r.name || r.email || r.account_id;
    byUser.set(label, (byUser.get(label) || 0) + r.total_tokens);
  }
  const sorted = [...byUser.entries()].sort((a, b) => b[1] - a[1]).slice(0, 25);

  const ctx = document.getElementById("userChart");
  const data = {
    labels: sorted.map(([label]) => label),
    datasets: [{ label: "Total tokens", data: sorted.map(([, v]) => v), backgroundColor: "#cc785c" }],
  };
  if (userChart) {
    userChart.data = data;
    userChart.update();
  } else {
    userChart = new Chart(ctx, { type: "bar", data, options: { indexAxis: "y", plugins: { legend: { display: false } } } });
  }
}

function renderTrendChart(rows) {
  const months = [...new Set(rows.map((r) => r.month))].sort();
  const roles = [...new Set(rows.map((r) => r.role))].sort();
  const totals = new Map(); // role -> month -> total

  for (const role of roles) totals.set(role, new Map(months.map((m) => [m, 0])));
  for (const r of rows) {
    totals.get(r.role).set(r.month, totals.get(r.role).get(r.month) + r.total_tokens);
  }

  const palette = ["#cc785c", "#6b8e9c", "#a3b18a", "#e8a87c", "#5c6b73", "#b56576"];
  const datasets = roles.map((role, i) => ({
    label: role,
    data: months.map((m) => totals.get(role).get(m)),
    borderColor: palette[i % palette.length],
    backgroundColor: palette[i % palette.length],
    fill: false,
    tension: 0.2,
  }));

  const ctx = document.getElementById("trendChart");
  const data = { labels: months, datasets };
  if (trendChart) {
    trendChart.data = data;
    trendChart.update();
  } else {
    trendChart = new Chart(ctx, { type: "line", data, options: {} });
  }
}

async function refreshView() {
  const role = roleSelect.value;
  const month = monthSelect.value;

  statusEl.textContent = "Loading...";
  try {
    const [tableData, trendData] = await Promise.all([
      fetchReport({ ...(role && { role }), ...(month && { month }) }),
      fetchReport({ ...(role && { role }) }),
    ]);

    populateOptions(tableData.roles, tableData.months);
    renderTable(tableData.rows);
    renderUserChart(tableData.rows);
    renderTrendChart(trendData.rows);
    fetchedAtEl.textContent = new Date(tableData.fetched_at).toLocaleString();

    if (tableData.unknown_account_ids.length) {
      warningBanner.hidden = false;
      warningBanner.textContent = `${tableData.unknown_account_ids.length} account id(s) in usage data have no matching current org member (likely removed/deactivated users) and show up with role "unknown".`;
    } else {
      warningBanner.hidden = true;
    }
    statusEl.textContent = "";
  } catch (err) {
    statusEl.textContent = err.message;
  }
}

roleSelect.addEventListener("change", refreshView);
monthSelect.addEventListener("change", refreshView);
refreshBtn.addEventListener("click", async () => {
  statusEl.textContent = "Refreshing from Admin API (this can take a bit)...";
  refreshBtn.disabled = true;
  try {
    const res = await fetch("/api/refresh", { method: "POST" });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Refresh failed: ${res.status}`);
    }
    await refreshView();
  } catch (err) {
    statusEl.textContent = err.message;
  } finally {
    refreshBtn.disabled = false;
  }
});

refreshView();
