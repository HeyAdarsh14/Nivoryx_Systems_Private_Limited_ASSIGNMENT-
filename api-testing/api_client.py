"""
AquaSense Python API Client
Handles authentication, telemetry retrieval, schema validation, and stale detection.
Designed for deterministic testing and dependency injection.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
import requests

from mock_api import MockAquaSenseBackend, MockAPIResponse


class AquaSenseAPIError(Exception):
  """Base exception for AquaSense client errors."""
  pass


class AuthenticationError(AquaSenseAPIError):
  """Raised when authentication fails or token is rejected (401)."""
  pass


class DeviceNotFoundError(AquaSenseAPIError):
  """Raised when device ID does not exist on server (404)."""
  pass


class DeviceOfflineError(AquaSenseAPIError):
  """Raised when device is unreachable due to network disconnect or timeout."""
  pass


class ValidationError(AquaSenseAPIError):
  """Raised when response schema or field values violate invariants."""
  pass


@dataclass
class DeviceStatusResult:
  device_id: str
  level_percent: float
  pump_state: str  # "on" | "off"
  last_seen: datetime
  is_stale: bool
  is_low_level_alert: bool  # True strictly when level_percent < 20.0
  raw_payload: Dict[str, Any]


class AquaSenseClient:
  """
  Client for interacting with AquaSense Device API.
  Accepts an optional transport function for seamless mocking/testing without live servers.
  """
  DEFAULT_STALE_THRESHOLD_SECONDS = 300  # 5 minutes

  def __init__(
    self,
    base_url: str = "https://api.aquasense.nivoryx.local",
    stale_threshold_seconds: int = DEFAULT_STALE_THRESHOLD_SECONDS,
    mock_mode: bool = True
  ):
    self.base_url = base_url.rstrip("/")
    self.stale_threshold_seconds = stale_threshold_seconds
    self.mock_mode = mock_mode
    self.auth_token: Optional[str] = None

  def login(self, username: str, password: str) -> str:
    """
    Authenticates user and saves the returned bearer token.
    POST /login
    """
    payload = {"username": username, "password": password}

    if self.mock_mode:
      response = MockAquaSenseBackend.handle_post_login(payload)
    else:
      try:
        response = requests.post(f"{self.base_url}/login", json=payload, timeout=5)
      except requests.RequestException as e:
        raise DeviceOfflineError(f"Network error during login: {e}") from e

    if response.status_code == 401:
      raise AuthenticationError("Authentication failed: invalid username or password.")
    if response.status_code != 200:
      raise AquaSenseAPIError(f"Unexpected status code {response.status_code}: {response.text}")

    data = response.json()
    if not isinstance(data, dict) or "token" not in data or not data["token"]:
      raise ValidationError("Login response missing valid 'token' field.")

    self.auth_token = data["token"]
    return self.auth_token

  def get_device_status(
    self,
    device_id: str,
    reference_time: Optional[datetime] = None
  ) -> DeviceStatusResult:
    """
    Fetches status for specified device ID.
    GET /device/{id}/status
    Validates schema, checks stale status against reference_time, and checks < 20% alert.
    """
    headers = {}
    if self.auth_token:
      headers["Authorization"] = f"Bearer {self.auth_token}"

    if self.mock_mode:
      try:
        response = MockAquaSenseBackend.handle_get_device_status(device_id, headers)
      except ConnectionError as ce:
        raise DeviceOfflineError(f"Device offline or network disconnected: {ce}") from ce
    else:
      try:
        response = requests.get(
          f"{self.base_url}/device/{device_id}/status",
          headers=headers,
          timeout=5
        )
      except requests.RequestException as re:
        raise DeviceOfflineError(f"Network error: {re}") from re

    # HTTP Status Handling
    if response.status_code == 401:
      raise AuthenticationError("Unauthorized: Token missing, invalid, or expired.")
    if response.status_code == 404:
      raise DeviceNotFoundError(f"Device '{device_id}' was not found.")
    if response.status_code != 200:
      raise AquaSenseAPIError(f"Server returned status {response.status_code}: {response.text}")

    # Parse and Validate Payload
    try:
      data = response.json()
    except Exception as parse_err:
      raise ValidationError(f"Response is not valid JSON: {parse_err}") from parse_err

    return self._validate_and_build_status(device_id, data, reference_time)

  def _validate_and_build_status(
    self,
    device_id: str,
    data: Dict[str, Any],
    reference_time: Optional[datetime]
  ) -> DeviceStatusResult:
    """Validates contract invariants and computes stale / alert state."""
    if not isinstance(data, dict):
      raise ValidationError("Status payload must be a JSON object.")

    # 1. level_percent validation
    if "level_percent" not in data:
      raise ValidationError("Payload missing required field 'level_percent'.")
    raw_level = data["level_percent"]
    if not isinstance(raw_level, (int, float)):
      raise ValidationError(f"'level_percent' must be numeric, got {type(raw_level).__name__}.")
    level_percent = float(raw_level)
    if level_percent < 0.0 or level_percent > 100.0:
      raise ValidationError(f"'level_percent' must be within [0, 100], got {level_percent}.")

    # 2. pump_state validation
    if "pump_state" not in data:
      raise ValidationError("Payload missing required field 'pump_state'.")
    pump_state = data["pump_state"]
    if pump_state not in ("on", "off"):
      raise ValidationError(f"'pump_state' must be 'on' or 'off', got '{pump_state}'.")

    # 3. last_seen validation
    if "last_seen" not in data:
      raise ValidationError("Payload missing required field 'last_seen'.")
    raw_timestamp = data["last_seen"]
    try:
      # Parse ISO 8601 timestamp
      # Handle trailing 'Z' if present
      iso_str = raw_timestamp.replace("Z", "+00:00") if isinstance(raw_timestamp, str) else ""
      last_seen_dt = datetime.fromisoformat(iso_str)
      if last_seen_dt.tzinfo is None:
        last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)
    except Exception as dt_err:
      raise ValidationError(f"Invalid ISO timestamp in 'last_seen': {raw_timestamp}") from dt_err

    # 4. Deterministic Stale Detection
    ref = reference_time or datetime.now(timezone.utc)
    if ref.tzinfo is None:
      ref = ref.replace(tzinfo=timezone.utc)
    
    elapsed_seconds = (ref - last_seen_dt).total_seconds()
    # Boundary: strictly greater than stale_threshold_seconds
    is_stale = elapsed_seconds > self.stale_threshold_seconds

    # 5. Alert Trigger: strictly below 20.0%
    is_low_alert = level_percent < 20.0

    return DeviceStatusResult(
      device_id=device_id,
      level_percent=level_percent,
      pump_state=pump_state,
      last_seen=last_seen_dt,
      is_stale=is_stale,
      is_low_level_alert=is_low_alert,
      raw_payload=data
    )

