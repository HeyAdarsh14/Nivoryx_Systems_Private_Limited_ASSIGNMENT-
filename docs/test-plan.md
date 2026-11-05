# AquaSense API Test Plan & Strategy

## 1. Scope & Objective
This test plan validates the backend API contracts for the **AquaSense IoT Water Management Platform** (Nivoryx Systems assignment). The system under test provides authentication and real-time device telemetry.

### Assumed API Contracts
* **Authentication**: `POST /login`
  * Input: `{"username": "<string>", "password": "<string>"}`
  * Success (200 OK): `{"token": "<bearer_token_string>"}`
  * Failure (401 Unauthorized): `{"error": "Invalid username or password"}`
* **Telemetry Status**: `GET /device/{id}/status`
  * Headers: `Authorization: Bearer <token>`
  * Success (200 OK):
    ```json
    {
      "level_percent": 55.0,
      "pump_state": "off",
      "last_seen": "2026-11-02T20:00:00Z"
    }
    ```
  * Error (401 Unauthorized): Missing or invalid auth token.
  * Error (404 Not Found): Device ID does not exist.
  * Error (Connection/Offline): Device gateway unreachable or network failure.

---

## 2. Test Cases Matrix

| Test ID | Category | Scenario / Objective | Mock Input / Precondition | Expected Result | Automated |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Positive | Login with valid credentials | Valid username & password | HTTP 200; returns non-empty auth token string | **Yes** (pytest) |
| **TC-02** | Negative | Login with incorrect password | Valid username, invalid password | HTTP 401; `AuthenticationError`; token remains `None` | **Yes** (pytest) |
| **TC-03** | Positive | Fetch device status with valid token | Device `device-001`; valid Bearer token | HTTP 200; `level_percent=55.0`, `pump_state='off'`, valid ISO timestamp | **Yes** (pytest) |
| **TC-04** | Negative | Fetch device status without auth token | Client unauthenticated (no token header) | HTTP 401; raises `AuthenticationError` | **Yes** (pytest) |
| **TC-05** | Negative | Query unknown/non-existent device ID | Valid token; device `device-999-unknown` | HTTP 404; raises `DeviceNotFoundError` | **Yes** (pytest) |
| **TC-06** | Resilience | Network drops or device offline mid-request | Valid token; device `device-offline` (gateway timeout) | Raises controlled `DeviceOfflineError`; does **not** hallucinate pump state | **Yes** (pytest) |
| **TC-07** | Negative | Malformed JSON or missing required contract fields | Valid token; payload lacks `level_percent` & `pump_state` | Raises controlled `ValidationError` | **Yes** (pytest) |
| **TC-08** | Edge | Telemetry timestamp older than stale threshold | Device `device-stale` (`last_seen` 2h old); ref clock 20:00:00Z | Marked `is_stale=True`; UI alerted not to display as live data | **Yes** (pytest) |
| **TC-09** | Boundary | Boundary tank levels: exactly 0.0% and 100.0% | `device-boundary-0` (0%) & `device-boundary-100` (100%) | Both accepted; 0% triggers low-level alert (`< 20%`), 100% does not | **Yes** (pytest) |
| **TC-10** | Negative / Boundary | Tank level out of physical bounds (-5.0% or 105.0%) | `device-invalid-level-negative` (`level_percent: -5.0`) | Rejected; raises `ValidationError` | **Yes** (pytest) |
| **TC-11** | Negative | Invalid pump state enum value | `device-invalid-pump-state` (`pump_state: 'running'`) | Rejected; raises `ValidationError` (must be `'on'` or `'off'`) | **Yes** (pytest) |
| **TC-12** | Boundary | Stale threshold exact boundary check (300.0s vs 301.0s) | Injected reference time exactly at 300s and 301s | At 300.0s `is_stale=False`; at 301.0s `is_stale=True` | **Yes** (pytest) |

---

## 3. Automation Execution
All 12 test cases are automated under `api-testing/test_api.py` using Python 3 and `pytest`. To execute:
```bash
python -m pytest api-testing/ -v
```
Output:
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
```

---

## 4. Mobile Wi-Fi Interruption Testing Strategy
Testing a mobile app's behaviour when the device loses Wi-Fi mid-operation (such as toggling the water pump "ON") requires simulating unpredictable network transit failures via tools like Charles Proxy, network conditioners, or airplane-mode toggle. The test must verify that the app displays an immediate non-blocking progress indicator followed by an explicit timeout/connection error banner, without optimistically flipping the UI toggle to "ON" or assuming the server accepted the command. Because the HTTP request might have reached the cloud before the client lost connection (an ambiguous outcome), the app must avoid automatic non-idempotent retries to prevent duplicate commands or hardware flapping. Upon Wi-Fi reconnection or app foregrounding, the app must initiate a fresh, authoritative `GET /device/{id}/status` handshake, reconcile its local UI state with the confirmed physical telemetry, and flag any intermediate state as unverified or stale until confirmed.
