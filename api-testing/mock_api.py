"""
AquaSense Mock API Service
Simulates IoT Device Cloud API for deterministic, network-free automated testing.
Assumed Contracts:
  POST /login              -> {"token": "<auth_token>"}
  GET  /device/{id}/status -> {"level_percent": float, "pump_state": "on"|"off", "last_seen": ISO8601}
"""

import json
from typing import Any, Dict, Optional, Tuple

VALID_MOCK_TOKEN = "mock-bearer-token-aqua-2026"
VALID_USERNAME = "adarsh@nivoryx.local"
VALID_PASSWORD = "AquaSenseSecurePassword2026!"

KNOWN_DEVICES = {
  "device-001": {
    "level_percent": 55.0,
    "pump_state": "off",
    "last_seen": "2026-11-02T20:00:00Z"
  },
  "device-low-level": {
    "level_percent": 18.0,
    "pump_state": "on",
    "last_seen": "2026-11-02T16:00:00Z"
  },
  "device-boundary-0": {
    "level_percent": 0.0,
    "pump_state": "on",
    "last_seen": "2026-11-02T20:00:00Z"
  },
  "device-boundary-100": {
    "level_percent": 100.0,
    "pump_state": "off",
    "last_seen": "2026-11-02T20:00:00Z"
  },
  "device-stale": {
    "level_percent": 42.0,
    "pump_state": "off",
    "last_seen": "2026-11-02T18:00:00Z" # older than reference 20:00
  },
  "device-malformed-schema": {
    "invalid_key": "bad_data"
    # missing level_percent, pump_state, last_seen
  },
  "device-invalid-level-negative": {
    "level_percent": -5.0,
    "pump_state": "off",
    "last_seen": "2026-11-02T20:00:00Z"
  },
  "device-invalid-pump-state": {
    "level_percent": 50.0,
    "pump_state": "running", # invalid: must be "on" or "off"
    "last_seen": "2026-11-02T20:00:00Z"
  }
}


class MockAPIResponse:
  """Lightweight mock response object matching requests.Response interface."""
  def __init__(self, status_code: int, json_data: Optional[Dict[str, Any]] = None, raw_text: str = ""):
    self.status_code = status_code
    self._json_data = json_data
    self.text = raw_text if raw_text else (json.dumps(json_data) if json_data is not None else "")

  def json(self) -> Any:
    if self._json_data is not None:
      return self._json_data
    return json.loads(self.text)

  def raise_for_status(self):
    if 400 <= self.status_code < 600:
      raise ConnectionError(f"HTTP Error {self.status_code}: {self.text}")


class MockAquaSenseBackend:
  """In-memory mock router simulating the AquaSense REST API."""

  @classmethod
  def handle_post_login(cls, payload: Dict[str, Any]) -> MockAPIResponse:
    if not isinstance(payload, dict):
      return MockAPIResponse(400, {"error": "Malformed JSON payload"})
    
    username = payload.get("username")
    password = payload.get("password")

    if username == VALID_USERNAME and password == VALID_PASSWORD:
      return MockAPIResponse(200, {"token": VALID_MOCK_TOKEN})
    return MockAPIResponse(401, {"error": "Invalid username or password"})

  @classmethod
  def handle_get_device_status(cls, device_id: str, headers: Optional[Dict[str, str]] = None) -> MockAPIResponse:
    headers = headers or {}
    auth_header = headers.get("Authorization", "")
    expected_header = f"Bearer {VALID_MOCK_TOKEN}"

    # Token check
    if auth_header != expected_header:
      return MockAPIResponse(401, {"error": "Unauthorized: Missing or invalid token"})

    # Offline device simulation
    if device_id == "device-offline":
      # Simulates network connectivity drop or device gateway offline
      raise ConnectionError("Mock ConnectionError: Failed to reach device gateway. Network timeout.")

    # Device lookup
    if device_id not in KNOWN_DEVICES:
      return MockAPIResponse(404, {"error": f"Device '{device_id}' not found"})

    # Return device payload
    data = KNOWN_DEVICES[device_id]
    return MockAPIResponse(200, data)
