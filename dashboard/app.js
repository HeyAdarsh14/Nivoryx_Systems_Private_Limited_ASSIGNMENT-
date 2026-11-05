/**
 * AquaSense Tank Level Telemetry Dashboard
 * Assignment implementation for Nivoryx Systems Private Limited
 */

// Official Mock Data (also loaded via mock-data.json)
const DEFAULT_MOCK_DATA = [
  { timestamp: "2026-11-02T06:00:00", level_percent: 78 },
  { timestamp: "2026-11-02T08:00:00", level_percent: 64 },
  { timestamp: "2026-11-02T10:00:00", level_percent: 51 },
  { timestamp: "2026-11-02T12:00:00", level_percent: 37 },
  { timestamp: "2026-11-02T14:00:00", level_percent: 24 },
  { timestamp: "2026-11-02T16:00:00", level_percent: 18 },
  { timestamp: "2026-11-02T18:00:00", level_percent: 42 },
  { timestamp: "2026-11-02T20:00:00", level_percent: 55 }
];

const CRITICAL_THRESHOLD = 20.0; // Level falls strictly BELOW 20% (< 20)

// Application State
let activeReadings = [];
let chartInstance = null;

/**
 * Validates a single telemetry reading record.
 * @param {Object} r - Record with timestamp and level_percent
 * @returns {boolean} - True if valid, false otherwise
 */
function isValidReading(r) {
  if (!r || typeof r !== 'object') return false;
  const parsedDate = new Date(r.timestamp);
  if (isNaN(parsedDate.getTime())) return false;
  if (typeof r.level_percent !== 'number' || !isFinite(r.level_percent)) return false;
  if (r.level_percent < 0 || r.level_percent > 100) return false;
  return true;
}

/**
 * Pure function: Checks if water level falls strictly below critical safety threshold.
 * Strict inequality: level < 20.0
 * @param {number} levelPercent 
 * @returns {boolean}
 */
function isAlertActive(levelPercent) {
  return typeof levelPercent === 'number' && levelPercent < CRITICAL_THRESHOLD;
}

/**
 * Sorts readings chronologically by timestamp ascending.
 * Never assumes incoming data array is pre-sorted.
 * @param {Array} list 
 * @returns {Array} sorted clone
 */
function sortChronologically(list) {
  return [...list].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
}

/**
 * Computes current reading, daily min, daily max, and historical threshold events.
 * @param {Array} readings 
 * @returns {Object|null}
 */
function computeMetrics(readings) {
  const valid = readings.filter(isValidReading);
  if (valid.length === 0) return null;

  const sorted = sortChronologically(valid);
  const current = sorted[sorted.length - 1]; // Latest by timestamp

  let min = sorted[0];
  let max = sorted[0];
  const historicalAlerts = [];

  for (const r of sorted) {
    if (r.level_percent < min.level_percent) {
      min = r;
    }
    if (r.level_percent > max.level_percent) {
      max = r;
    }
    if (isAlertActive(r.level_percent)) {
      historicalAlerts.push(r);
    }
  }

  return {
    sorted,
    current,
    min,
    max,
    historicalAlerts,
    isCurrentInAlert: isAlertActive(current.level_percent)
  };
}

/**
 * Formats an ISO timestamp for display.
 * @param {string} isoString 
 * @returns {{ full: string, time: string, date: string }}
 */
function formatTimestamp(isoString) {
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return { full: 'Invalid Date', time: '--:--', date: '----' };
  
  const pad = (n) => String(n).padStart(2, '0');
  const time = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  const date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  return { full: `${date} ${time}`, time, date };
}

/**
 * Renders the Alert Section dynamically.
 */
function renderAlertSection(metrics) {
  const container = document.getElementById('alertContainer');
  container.innerHTML = ''; // safe clear

  if (!metrics) {
    const errorBanner = document.createElement('div');
    errorBanner.className = 'alert-banner alert-banner-danger';
    errorBanner.textContent = 'No valid telemetry data available to evaluate tank status.';
    container.appendChild(errorBanner);
    return;
  }

  // 1. Current Status Banner (Critical Alert vs Optimal)
  const currentBanner = document.createElement('div');
  if (metrics.isCurrentInAlert) {
    currentBanner.className = 'alert-banner alert-banner-danger';
    currentBanner.innerHTML = `
      <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
        <line x1="12" y1="9" x2="12" y2="13"></line>
        <line x1="12" y1="17" x2="12.01" y2="17"></line>
      </svg>
      <div>
        <div class="alert-title">CRITICAL ALERT: Low Tank Level (${metrics.current.level_percent}%)</div>
        <div>Tank level has fallen strictly below the ${CRITICAL_THRESHOLD}% safety threshold. Trigger pump activation immediately.</div>
      </div>
    `;
  } else {
    currentBanner.className = 'alert-banner alert-banner-normal';
    currentBanner.innerHTML = `
      <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
        <polyline points="22 4 12 14.01 9 11.01"></polyline>
      </svg>
      <div>
        <div class="alert-title">Normal Operating Status (Current: ${metrics.current.level_percent}%)</div>
        <div>Current tank water level is above the ${CRITICAL_THRESHOLD}% threshold. Reservoir is operating normally.</div>
      </div>
    `;
  }
  container.appendChild(currentBanner);

  // 2. Historical Alert Note (If any past reading was < 20% but current is >= 20%)
  if (!metrics.isCurrentInAlert && metrics.historicalAlerts.length > 0) {
    const histBanner = document.createElement('div');
    histBanner.className = 'alert-banner alert-banner-history';
    const alertTimes = metrics.historicalAlerts.map(a => `${formatTimestamp(a.timestamp).time} (${a.level_percent}%)`).join(', ');
    histBanner.innerHTML = `
      <svg class="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      <div>
        <strong>Historical Low Level Flagged:</strong> A low-level event was logged earlier today at ${alertTimes}. Current status has recovered.
      </div>
    `;
    container.appendChild(histBanner);
  }
}

/**
 * Updates Metric Cards in the DOM.
 */
function renderMetricCards(metrics) {
  if (!metrics) return;

  // Current
  const currentLevelEl = document.getElementById('currentLevelVal');
  const currentBadge = document.getElementById('currentStatusBadge');
  const currentFillBar = document.getElementById('currentFillBar');
  const currentTimestamp = document.getElementById('currentTimestamp');

  currentLevelEl.textContent = `${metrics.current.level_percent}%`;
  currentFillBar.style.width = `${Math.min(100, Math.max(0, metrics.current.level_percent))}%`;

  if (metrics.isCurrentInAlert) {
    currentBadge.textContent = 'Critical Low';
    currentBadge.className = 'badge badge-danger';
    currentLevelEl.className = 'metric-value text-danger';
    currentFillBar.classList.add('danger-fill');
  } else {
    currentBadge.textContent = 'Normal';
    currentBadge.className = 'badge badge-optimal';
    currentLevelEl.className = 'metric-value';
    currentFillBar.classList.remove('danger-fill');
  }
  currentTimestamp.textContent = `Latest update: ${formatTimestamp(metrics.current.timestamp).full}`;

  // Min
  const minLevelEl = document.getElementById('minLevelVal');
  const minTimestamp = document.getElementById('minTimestamp');
  const minPill = document.getElementById('minAlertPill');
  minLevelEl.textContent = `${metrics.min.level_percent}%`;
  minTimestamp.textContent = `Recorded at: ${formatTimestamp(metrics.min.timestamp).time}`;
  if (isAlertActive(metrics.min.level_percent)) {
    minPill.textContent = 'Under 20% Flag';
    minPill.className = 'badge alert-badge-pill';
  } else {
    minPill.textContent = 'Safe Min';
    minPill.className = 'badge badge-optimal';
  }

  // Max
  const maxLevelEl = document.getElementById('maxLevelVal');
  const maxTimestamp = document.getElementById('maxTimestamp');
  maxLevelEl.textContent = `${metrics.max.level_percent}%`;
  maxTimestamp.textContent = `Recorded at: ${formatTimestamp(metrics.max.timestamp).time}`;

  // Telemetry date badge
  document.getElementById('telemetryDate').textContent = formatTimestamp(metrics.current.timestamp).date;
}

/**
 * Populates the reading history table.
 */
function renderHistoryTable(metrics) {
  const tbody = document.getElementById('telemetryTableBody');
  tbody.innerHTML = ''; // clear

  document.getElementById('readingCountBadge').textContent = `${metrics.sorted.length} Readings`;

  metrics.sorted.forEach((item, index) => {
    const tr = document.createElement('tr');
    const isUnderThreshold = isAlertActive(item.level_percent);
    if (isUnderThreshold) {
      tr.classList.add('table-row-highlight-danger');
    }

    const { full, time } = formatTimestamp(item.timestamp);

    // Columns: #, Timestamp, Time, Level, Status
    const tdIndex = document.createElement('td');
    tdIndex.textContent = String(index + 1);

    const tdTimestamp = document.createElement('td');
    tdTimestamp.textContent = full;

    const tdTime = document.createElement('td');
    tdTime.textContent = time;

    const tdLevel = document.createElement('td');
    tdLevel.style.fontWeight = '600';
    tdLevel.textContent = `${item.level_percent}%`;

    const tdStatus = document.createElement('td');
    const statusPill = document.createElement('span');
    if (isUnderThreshold) {
      statusPill.className = 'badge badge-danger';
      statusPill.textContent = 'LOW (<20%)';
    } else {
      statusPill.className = 'badge badge-optimal';
      statusPill.textContent = 'NORMAL';
    }
    tdStatus.appendChild(statusPill);

    tr.appendChild(tdIndex);
    tr.appendChild(tdTimestamp);
    tr.appendChild(tdTime);
    tr.appendChild(tdLevel);
    tr.appendChild(tdStatus);

    tbody.appendChild(tr);
  });
}

/**
 * Initializes or updates Chart.js time-series graph.
 */
function renderChart(metrics) {
  const ctx = document.getElementById('levelChart').getContext('2d');
  const labels = metrics.sorted.map(r => formatTimestamp(r.timestamp).time);
  const data = metrics.sorted.map(r => r.level_percent);

  // Colors per point: highlight points < 20% in red
  const pointColors = metrics.sorted.map(r => isAlertActive(r.level_percent) ? '#ef4444' : '#38bdf8');
  const pointRadii = metrics.sorted.map(r => isAlertActive(r.level_percent) ? 8 : 5);

  if (chartInstance) {
    chartInstance.destroy();
  }

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Tank Water Level (%)',
          data,
          borderColor: '#38bdf8',
          borderWidth: 2.5,
          backgroundColor: 'rgba(56, 189, 248, 0.1)',
          fill: true,
          tension: 0.3,
          pointBackgroundColor: pointColors,
          pointBorderColor: '#0b1120',
          pointBorderWidth: 2,
          pointRadius: pointRadii,
          pointHoverRadius: 9
        },
        {
          label: '20% Safety Threshold',
          data: labels.map(() => CRITICAL_THRESHOLD),
          borderColor: '#ef4444',
          borderWidth: 2,
          borderDash: [6, 4],
          fill: false,
          pointRadius: 0,
          pointHoverRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          labels: {
            color: '#94a3b8',
            font: { family: 'Inter', size: 12 }
          }
        },
        tooltip: {
          backgroundColor: '#1e293b',
          titleColor: '#f8fafc',
          bodyColor: '#e2e8f0',
          borderColor: '#334155',
          borderWidth: 1,
          callbacks: {
            label: function(context) {
              const val = context.raw;
              if (context.datasetIndex === 1) return `Threshold: ${val}%`;
              return `Level: ${val}% ${val < CRITICAL_THRESHOLD ? '(CRITICAL LOW)' : '(Optimal)'}`;
            }
          }
        }
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: {
            color: '#94a3b8',
            callback: (v) => `${v}%`
          }
        },
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#94a3b8' }
        }
      }
    }
  });
}

/**
 * Master UI update function.
 */
function updateUI() {
  const metrics = computeMetrics(activeReadings);
  renderAlertSection(metrics);
  renderMetricCards(metrics);
  renderHistoryTable(metrics);
  renderChart(metrics);
}

/**
 * Loads telemetry data from mock-data.json or falls back cleanly.
 */
async function loadData() {
  try {
    const response = await fetch('mock-data.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error('Data is not an array');
    activeReadings = data;
    console.log('[AquaSense] Successfully loaded data from mock-data.json');
  } catch (err) {
    console.warn('[AquaSense] Fetch failed (likely file:// protocol without server); using fallback dataset.', err);
    activeReadings = JSON.parse(JSON.stringify(DEFAULT_MOCK_DATA));
  }
  updateUI();
}

/**
 * Attaches event listeners for testing controls and simulation.
 */
function setupSimulator() {
  const btnReset = document.getElementById('btnResetOfficial');
  const btnSimulate15 = document.getElementById('btnSimulate15');
  const btnSimulate199 = document.getElementById('btnSimulate199');
  const btnSimulate200 = document.getElementById('btnSimulate200');
  const btnInjectCustom = document.getElementById('btnInjectCustom');
  const customInput = document.getElementById('customInputLevel');
  const feedback = document.getElementById('injectFeedback');

  btnReset.addEventListener('click', () => {
    activeReadings = JSON.parse(JSON.stringify(DEFAULT_MOCK_DATA));
    feedback.textContent = 'Reset to official 8 readings. Latest: 55%, Min: 18%, Max: 78%.';
    feedback.style.color = '#38bdf8';
    updateUI();
  });

  btnSimulate15.addEventListener('click', () => {
    // Add a new latest reading with 15%
    const now = new Date();
    activeReadings.push({
      timestamp: new Date(Date.now() + 60000).toISOString(),
      level_percent: 15
    });
    feedback.textContent = 'Injected 15% reading. Critical low alert active!';
    feedback.style.color = '#ef4444';
    updateUI();
  });

  btnSimulate199.addEventListener('click', () => {
    // Boundary test: 19.9% should trigger alert (< 20)
    activeReadings.push({
      timestamp: new Date(Date.now() + 120000).toISOString(),
      level_percent: 19.9
    });
    feedback.textContent = 'Boundary test: Injected 19.9%. Alert triggered (< 20%).';
    feedback.style.color = '#f59e0b';
    updateUI();
  });

  btnSimulate200.addEventListener('click', () => {
    // Boundary test: 20.0% should NOT trigger alert (not < 20)
    activeReadings.push({
      timestamp: new Date(Date.now() + 180000).toISOString(),
      level_percent: 20.0
    });
    feedback.textContent = 'Boundary test: Injected 20.0%. No alert (20% is safe threshold boundary).';
    feedback.style.color = '#10b981';
    updateUI();
  });

  btnInjectCustom.addEventListener('click', () => {
    const val = parseFloat(customInput.value);
    if (isNaN(val) || val < 0 || val > 100) {
      feedback.textContent = 'Please enter a valid percentage between 0 and 100.';
      feedback.style.color = '#ef4444';
      return;
    }
    activeReadings.push({
      timestamp: new Date(Date.now() + 240000).toISOString(),
      level_percent: val
    });
    feedback.textContent = `Injected custom reading of ${val}%.`;
    feedback.style.color = '#10b981';
    customInput.value = '';
    updateUI();
  });
}

// Bootstrap on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  setupSimulator();
  loadData();
});

