"""
AquaSense Automated API Test Suite
Automates mock API test cases for POST /login and GET /device/{id}/status.
Uses deterministic time injection and strict boundary assertions.
"""

from datetime import datetime, timezone, timedelta
import pytest

from api_client import (
  AquaSenseClient,
  AuthenticationError,
  DeviceNotFoundError,
  DeviceOfflineError,
  ValidationError,
  DeviceStatusResult
)
from mock_api import VALID_USERNAME, VALID_PASSWORD, VALID_MOCK_TOKEN


@pytest.fixture
def client() -> AquaSenseClient:
  """Returns a freshly instantiated AquaSenseClient in mock mode."""
  return AquaSenseClient(mock_mode=True, stale_threshold_seconds=300)


@pytest.fixture
def authenticated_client(client: AquaSenseClient) -> AquaSenseClient:
  """Returns an AquaSenseClient that has already authenticated."""
  client.login(VALID_USERNAME, VALID_PASSWORD)
  return client


# ============================================================================
# PART B TEST CASES
# ============================================================================

def test_tc01_login_success(client: AquaSenseClient):
  """
  TC-01 [Positive]: Successful login with valid credentials.
  Expectation: Returns non-empty auth token and caches it on client.
  """
  token = client.login(VALID_USERNAME, VALID_PASSWORD)
  assert token is not None
  assert token == VALID_MOCK_TOKEN
  assert client.auth_token == VALID_MOCK_TOKEN


def test_tc02_login_invalid_credentials(client: AquaSenseClient):
  """
  TC-02 [Negative]: Login with invalid password.
  Expectation: Raises AuthenticationError (401), token remains None.
  """
  with pytest.raises(AuthenticationError) as exc_info:
    client.login(VALID_USERNAME, "WrongPassword123!")
  assert "invalid username or password" in str(exc_info.value).lower()
  assert client.auth_token is None


def test_tc03_get_device_status_success(authenticated_client: AquaSenseClient):
  """
  TC-03 [Positive]: Retrieve status for known online device with valid token.
  Expectation: 200 OK, level=55%, pump_state='off', alert=False, parsed timestamp.
  """
  fixed_ref = datetime(2026, 11, 2, 20, 2, 0, tzinfo=timezone.utc) # 2 mins after last_seen
  result = authenticated_client.get_device_status("device-001", reference_time=fixed_ref)

  assert isinstance(result, DeviceStatusResult)
  assert result.device_id == "device-001"
  assert result.level_percent == 55.0
  assert result.pump_state == "off"
  assert result.is_low_level_alert is False  # 55 >= 20
  assert result.is_stale is False            # 120s <= 300s threshold
  assert result.last_seen == datetime(2026, 11, 2, 20, 0, 0, tzinfo=timezone.utc)


def test_tc04_get_device_status_unauthorized_without_token(client: AquaSenseClient):
  """
  TC-04 [Negative]: Attempt to fetch device status without authenticating.
  Expectation: Raises AuthenticationError (401 Unauthorized).
  """
  assert client.auth_token is None
  with pytest.raises(AuthenticationError) as exc_info:
    client.get_device_status("device-001")
  assert "unauthorized" in str(exc_info.value).lower()


def test_tc05_get_device_status_unknown_device(authenticated_client: AquaSenseClient):
  """
  TC-05 [Negative]: Query device ID that does not exist.
  Expectation: Raises DeviceNotFoundError (404 Not Found).
  """
  with pytest.raises(DeviceNotFoundError) as exc_info:
    authenticated_client.get_device_status("device-999-unknown")
  assert "not found" in str(exc_info.value).lower()


def test_tc06_device_offline_network_resilience(authenticated_client: AquaSenseClient):
  """
  TC-06 [Negative / Resilience]: Device is unreachable or network times out mid-request.
  Expectation: Controlled DeviceOfflineError; client never hallucinates pump status.
  """
  with pytest.raises(DeviceOfflineError) as exc_info:
    authenticated_client.get_device_status("device-offline")
  assert "offline or network disconnected" in str(exc_info.value).lower()


def test_tc07_malformed_response_schema(authenticated_client: AquaSenseClient):
  """
  TC-07 [Negative]: Device response missing required contract fields.
  Expectation: Controlled ValidationError raised, not an unhandled crash.
  """
  with pytest.raises(ValidationError) as exc_info:
    authenticated_client.get_device_status("device-malformed-schema")
  assert "missing required field" in str(exc_info.value).lower()


def test_tc08_stale_last_seen_detection(authenticated_client: AquaSenseClient):
  """
  TC-08 [Edge]: last_seen timestamp is older than the 300s threshold.
  Expectation: result.is_stale is True, flagged so UI does not present it as live.
  """
  # device-stale has last_seen: 2026-11-02T18:00:00Z.
  # Reference clock at 20:00:00Z is 2 hours later (7200s > 300s threshold).
  fixed_ref = datetime(2026, 11, 2, 20, 0, 0, tzinfo=timezone.utc)
  result = authenticated_client.get_device_status("device-stale", reference_time=fixed_ref)

  assert result.is_stale is True
  assert result.level_percent == 42.0


def test_tc09_boundary_tank_levels_0_and_100(authenticated_client: AquaSenseClient):
  """
  TC-09 [Boundary]: Tank level exactly at 0.0% and 100.0%.
  Expectation: Both valid; 0.0% activates critical low alert (<20), 100.0% is safe.
  """
  ref = datetime(2026, 11, 2, 20, 1, 0, tzinfo=timezone.utc)

  res_0 = authenticated_client.get_device_status("device-boundary-0", reference_time=ref)
  assert res_0.level_percent == 0.0
  assert res_0.is_low_level_alert is True  # 0.0 < 20.0

  res_100 = authenticated_client.get_device_status("device-boundary-100", reference_time=ref)
  assert res_100.level_percent == 100.0
  assert res_100.is_low_level_alert is False


def test_tc10_out_of_bounds_tank_level_rejected(authenticated_client: AquaSenseClient):
  """
  TC-10 [Negative / Boundary]: Tank level below 0% (-5.0%).
  Expectation: Raises ValidationError.
  """
  with pytest.raises(ValidationError) as exc_info:
    authenticated_client.get_device_status("device-invalid-level-negative")
  assert "within [0, 100]" in str(exc_info.value)


def test_tc11_invalid_pump_state_rejected(authenticated_client: AquaSenseClient):
  """
  TC-11 [Negative]: pump_state is an unexpected value ('running' instead of 'on'/'off').
  Expectation: Raises ValidationError.
  """
  with pytest.raises(ValidationError) as exc_info:
    authenticated_client.get_device_status("device-invalid-pump-state")
  assert "'pump_state' must be 'on' or 'off'" in str(exc_info.value)


def test_tc12_stale_boundary_exact_seconds(authenticated_client: AquaSenseClient):
  """
  TC-12 [Boundary]: Evaluate exact threshold boundary:
  At exactly 300 seconds elapsed: NOT stale (> 300 rule).
  At 301 seconds elapsed: IS stale.
  """
  device_time = datetime(2026, 11, 2, 20, 0, 0, tzinfo=timezone.utc)

  # Exactly 300 seconds later
  ref_exact = device_time + timedelta(seconds=300)
  res_exact = authenticated_client.get_device_status("device-001", reference_time=ref_exact)
  assert res_exact.is_stale is False

  # 301 seconds later (boundary exceeded)
  ref_stale = device_time + timedelta(seconds=301)
  res_stale = authenticated_client.get_device_status("device-001", reference_time=ref_stale)
  assert res_stale.is_stale is True

