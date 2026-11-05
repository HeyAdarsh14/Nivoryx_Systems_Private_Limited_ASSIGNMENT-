# AquaSense Mini-Build — IoT Tank Level Monitoring & API Testing

[![Tests](https://img.shields.io/badge/pytest-12%20passed-brightgreen.svg)](#part-b--automated-api-testing)
[![Platform](https://img.shields.io/badge/JavaScript-Vanilla%20ES6-yellow.svg)](#part-a--tank-level-dashboard)
[![Assignment](https://img.shields.io/badge/Nivoryx%20Systems-Internship%20Assignment-blue.svg)](#overview)

This repository contains the complete implementation for the **AquaSense Mini-Build** assignment for **Nivoryx Systems Private Limited**, submitted by **Adarsh Gupta**.

The project is split into two parts:
* **Part A (Tank Level Dashboard):** A lightweight, responsive telemetry dashboard built with semantic HTML5, modern CSS3, vanilla JavaScript, and Chart.js.
* **Part B (API Testing):** An automated Python `pytest` test suite with 12 test cases covering positive, negative, edge, and boundary conditions for IoT device authentication and status APIs using deterministic mocks.

---

## Repository Structure

```
.
├── dashboard/
│   ├── index.html          # Semantic, accessible dashboard layout
│   ├── styles.css          # Responsive styling, color hierarchy & alert themes
│   ├── app.js              # Pure computation functions, safe DOM updates, Chart.js logic
│   └── mock-data.json      # Exact 8 telemetry readings supplied by Nivoryx Systems
├── api-testing/
│   ├── __init__.py
│   ├── api_client.py       # Resilient Python client with schema validation & clock injection
│   ├── mock_api.py         # In-memory mock server simulating IoT REST API contracts
│   ├── test_api.py         # 12 automated pytest cases with deterministic assertions
│   └── requirements.txt    # Python dependencies (pytest, requests)
├── docs/
│   ├── test-plan.md        # Comprehensive 12-case QA test plan matrix
│   └── ai-usage-note.md    # 5-10 line truthful AI assistant usage note
├── README.md               # Setup guide, architecture, and evaluation details
└── .gitignore
```

---

## Part A — Tank Level Dashboard

### 1. Telemetry Dataset & Expected Metrics
Based on the supplied dataset for **2 November 2026**:
* **Current Tank Level:** `55%` (determined dynamically by chronological latest timestamp: `20:00:00`).
* **Today's Minimum:** `18%` (recorded at `16:00:00`).
* **Today's Maximum:** `78%` (recorded at `06:00:00`).

### 2. Alert Semantics & Boundary Logic
* **Alert Rule:** The critical alert triggers strictly when `level < 20.0%`.
* **Current Status:** Because the latest reading is **55%**, the **active critical alert is NOT triggered** (reservoir is normal).
* **Historical Flagging:** The historical drop to **18%** at 16:00 is clearly flagged in the reading history table, highlighted with a distinct red data point on the time-series chart, and documented in a separate historical notice banner.
* **Interactive Evaluator:** The UI includes quick buttons to simulate:
  * `15.0%` (Critical Alert active)
  * `19.9%` (Boundary check: Alert triggers `< 20%`)
  * `20.0%` (Boundary check: Safe threshold, no alert)
  * Custom reading injection with bounds checking `[0, 100]`.

### 3. Frontend Quality Highlights
* **Pure computation functions:** `sortChronologically()`, `isValidReading()`, `isAlertActive()`, `computeMetrics()`.
* **Defensive parsing:** Handles unsorted data, non-numeric values, or invalid timestamps safely.
* **Safe DOM updates:** Uses `textContent` and `createElement` for untrusted dynamic data (no raw `innerHTML` injections).
* **Graceful fallback:** Attempts `fetch('mock-data.json')` when served over HTTP, with fallback to bundled data if opened via `file://`.

---

## Part B — API Testing

### 1. Assumed API Contracts
* `POST /login`: Accepts `{"username": "<str>", "password": "<str>"}`. Returns `{"token": "<auth_token>"}` on HTTP 200, or HTTP 401 on bad credentials.
* `GET /device/{id}/status`: Requires header `Authorization: Bearer <token>`. Returns:
  ```json
  {
    "level_percent": 55.0,
    "pump_state": "off",
    "last_seen": "2026-11-02T20:00:00Z"
  }
  ```
* **Stale Threshold:** Telemetry with `last_seen` older than **300 seconds (5 minutes)** relative to an injected reference clock is flagged as stale (`is_stale: True`).

### 2. Test Plan Matrix (12 Cases Automated)
Detailed in [`docs/test-plan.md`](docs/test-plan.md):

| Test ID | Category | Objective | Status |
| :--- | :--- | :--- | :--- |
| **TC-01** | Positive | Login with valid credentials returns auth token | **PASSED** |
| **TC-02** | Negative | Login with incorrect password returns 401 | **PASSED** |
| **TC-03** | Positive | Fetch device status with valid token and schema | **PASSED** |
| **TC-04** | Negative | Fetch device status without token returns 401 | **PASSED** |
| **TC-05** | Negative | Query non-existent device returns 404 | **PASSED** |
| **TC-06** | Resilience | Network failure/offline returns controlled error | **PASSED** |
| **TC-07** | Negative | Malformed JSON / missing fields raises ValidationError | **PASSED** |
| **TC-08** | Edge | Old timestamp correctly marked `is_stale=True` | **PASSED** |
| **TC-09** | Boundary | Boundary levels 0.0% and 100.0% validated | **PASSED** |
| **TC-10** | Negative | Level out of range (-5%) raises ValidationError | **PASSED** |
| **TC-11** | Negative | Invalid `pump_state` ('running') raises ValidationError | **PASSED** |
| **TC-12** | Boundary | Exact stale threshold boundary (300.0s vs 301.0s) | **PASSED** |

---

## Mobile Wi-Fi Interruption Testing Strategy

> **How would you test a mobile app's behaviour when the device loses Wi-Fi mid-operation?**
>
> Testing a mobile app's behaviour when the device loses Wi-Fi mid-operation (such as toggling the water pump "ON") requires simulating unpredictable network transit failures via tools like Charles Proxy, network conditioners, or airplane-mode toggle. The test must verify that the app displays an immediate non-blocking progress indicator followed by an explicit timeout/connection error banner, without optimistically flipping the UI toggle to "ON" or assuming the server accepted the command. Because the HTTP request might have reached the cloud before the client lost connection (an ambiguous outcome), the app must avoid automatic non-idempotent retries to prevent duplicate commands or hardware flapping. Upon Wi-Fi reconnection or app foregrounding, the app must initiate a fresh, authoritative `GET /device/{id}/status` handshake, reconcile its local UI state with the confirmed physical telemetry, and flag any intermediate state as unverified or stale until confirmed.

---

## AI Usage Disclosure Note

**Tool Used:** Antigravity / Gemini 3.8

* **Prompt 1 (Dashboard Generation):**
  > "Build a responsive tank level dashboard using vanilla HTML, CSS, JavaScript, and Chart.js based on the supplied 8 mock telemetry readings. Calculate the latest level, daily minimum, daily maximum, and show an alert if level falls below 20%."
* **Prompt 2 (API Test Automation):**
  > "Create a Python pytest suite that mocks the POST /login and GET /device/{id}/status endpoints. Include positive, negative, and edge test cases covering token authorization, stale timestamps, malformed schemas, and boundary percentages."
* **One Issue in AI Suggestion & Correction:**
  > The assistant initially used non-strict inequality (`<= 20%`) and rendered an active critical alert on the main screen because of the historical 18% reading at 16:00, despite the current (latest) reading at 20:00 being 55%. I corrected the logic to strict inequality (`level < 20.0%`), ensured only the latest timestamped reading drives the active alert banner, and moved the historical 18% event into an informative notice and highlighted chart marker.

---

## Quickstart & Run Instructions

### 1. Run the Dashboard Locally
From the repository root:
```bash
python -m http.server 8000
```
Open your browser at:
```
http://localhost:8000/dashboard/
```

### 2. Run the Automated API Tests
Install dependencies and run pytest:
```bash
pip install -r api-testing/requirements.txt
python -m pytest api-testing/ -v
```

Expected output:
```
collected 12 items
api-testing/test_api.py::test_tc01_login_success PASSED                  [  8%]
api-testing/test_api.py::test_tc02_login_invalid_credentials PASSED      [ 16%]
api-testing/test_api.py::test_tc03_get_device_status_success PASSED      [ 25%]
api-testing/test_api.py::test_tc04_get_device_status_unauthorized_without_token PASSED [ 33%]
api-testing/test_api.py::test_tc05_get_device_status_unknown_device PASSED [ 41%]
api-testing/test_api.py::test_tc06_device_offline_network_resilience PASSED [ 50%]
api-testing/test_api.py::test_tc07_malformed_response_schema PASSED      [ 58%]
api-testing/test_api.py::test_tc08_stale_last_seen_detection PASSED      [ 66%]
api-testing/test_api.py::test_tc09_boundary_tank_levels_0_and_100 PASSED [ 75%]
api-testing/test_api.py::test_tc10_out_of_bounds_tank_level_rejected PASSED [ 83%]
api-testing/test_api.py::test_tc11_invalid_pump_state_rejected PASSED    [ 91%]
api-testing/test_api.py::test_tc12_stale_boundary_exact_seconds PASSED   [100%]

============================= 12 passed in 0.80s ==============================
```

---

## Interview Discussion Points

1. **Why vanilla JavaScript instead of React/Vue?**
   * Eliminates unnecessary build-step overhead for a static, data-driven telemetry widget while cleanly showing pure JavaScript DOM manipulation, event handling, and data transformation fundamentals.
2. **How is the current tank level selected?**
   * By sorting records chronologically by timestamp (`sortChronologically`) and taking the latest record. We never assume array index order equals chronological order.
3. **Why is the active alert not triggered for the 18% reading?**
   * The 18% reading occurred at 16:00, whereas the latest reading at 20:00 is 55%. Current status reflects real-time physical conditions; historical anomalies are displayed as historical context rather than an ongoing emergency.
4. **Why inject clock references in API tests?**
   * Prevents time-dependent test flakiness (e.g., CI failures when clock rolls over midnight) and allows microsecond-precise boundary validation of the 300-second stale policy.
5. **How does the client differentiate device offline from pump state off?**
   * "Offline" indicates an unconfirmed communication loss or network failure, where pump state is unknown. "Pump off" is an authoritative hardware state confirmed by device telemetry.
