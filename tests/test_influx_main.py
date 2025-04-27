"""Tests for InfluxDB utility main function."""

from unittest.mock import MagicMock, patch

import pytest
from influxdb_client import InfluxDBClient

from influx import main


@pytest.fixture
def mock_influx_config() -> dict[str, str]:
    """Mock InfluxDB configuration."""
    return {
        "INFLUXDB_URL": "http://test:8086",
        "INFLUXDB_TOKEN": "test-token",
        "INFLUXDB_ORG": "test-org",
    }


def test_main_success(
    mock_influx_config: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test successful execution of main function."""
    # Set environment variables
    for key, value in mock_influx_config.items():
        monkeypatch.setenv(key, value)

    # Mock InfluxDB client
    mock_client = MagicMock(spec=InfluxDBClient)
    health = MagicMock()
    health.status = "pass"
    mock_client.health.return_value = health

    # Mock bucket listing
    bucket = MagicMock()
    bucket.name = "test-bucket"
    buckets_api = MagicMock()
    buckets_api.find_buckets.return_value.buckets = [bucket]
    mock_client.buckets_api.return_value = buckets_api

    with patch("influx.InfluxDBClient", return_value=mock_client):
        result = main()

    assert result == 0


def test_main_missing_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test main function with missing configuration."""
    # Clear environment variables
    monkeypatch.delenv("INFLUXDB_TOKEN", raising=False)
    monkeypatch.delenv("INFLUXDB_ORG", raising=False)

    result = main()
    assert result == 1


def test_main_connection_error(
    mock_influx_config: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test main function with connection error."""
    # Set environment variables
    for key, value in mock_influx_config.items():
        monkeypatch.setenv(key, value)

    # Mock InfluxDB client with error
    mock_client = MagicMock(spec=InfluxDBClient)
    mock_client.health.side_effect = Exception("Connection failed")

    with patch("influx.InfluxDBClient", return_value=mock_client):
        result = main()

    assert result == 1
