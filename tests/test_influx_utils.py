"""Tests for InfluxDB utility functions."""

from unittest.mock import MagicMock

import pytest
from influxdb_client import InfluxDBClient

from influx import get_influx_config, validate_config, verify_connection


def test_get_influx_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test getting InfluxDB configuration from environment."""
    # Set environment variables
    test_config = {
        "INFLUXDB_URL": "http://test:8086",
        "INFLUXDB_TOKEN": "test-token",
        "INFLUXDB_ORG": "test-org",
    }
    for key, value in test_config.items():
        monkeypatch.setenv(key, value)

    # Get config
    url, token, org = get_influx_config()

    assert url == test_config["INFLUXDB_URL"]
    assert token == test_config["INFLUXDB_TOKEN"]
    assert org == test_config["INFLUXDB_ORG"]


def test_get_influx_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test default values when environment variables are missing."""
    # Clear environment variables
    monkeypatch.delenv("INFLUXDB_URL", raising=False)
    monkeypatch.delenv("INFLUXDB_TOKEN", raising=False)
    monkeypatch.delenv("INFLUXDB_ORG", raising=False)

    # Get config
    url, token, org = get_influx_config()

    assert url == "http://localhost:8086"
    assert token is None
    assert org is None


def test_validate_config(capsys: pytest.CaptureFixture[str]) -> None:
    """Test configuration validation."""
    # Valid config
    assert validate_config("token", "org") is True

    # Invalid config - missing token
    assert validate_config(None, "org") is False
    out, _ = capsys.readouterr()
    assert "Missing InfluxDB configuration" in out

    # Invalid config - missing org
    assert validate_config("token", None) is False
    out, _ = capsys.readouterr()
    assert "Missing InfluxDB configuration" in out


def test_verify_connection_success(capsys: pytest.CaptureFixture[str]) -> None:
    """Test successful InfluxDB connection verification."""
    # Mock client
    client = MagicMock(spec=InfluxDBClient)

    # Mock successful health check
    health = MagicMock()
    health.status = "pass"
    client.health.return_value = health

    # Mock bucket listing
    bucket = MagicMock()
    bucket.name = "test-bucket"
    buckets_api = MagicMock()
    buckets_api.find_buckets.return_value.buckets = [bucket]
    client.buckets_api.return_value = buckets_api

    # Test connection
    assert verify_connection(client) is True

    # Check output
    out, _ = capsys.readouterr()
    assert "connection: pass" in out
    assert "test-bucket" in out
    assert "successful" in out


def test_verify_connection_failure(capsys: pytest.CaptureFixture[str]) -> None:
    """Test failed InfluxDB connection verification."""
    # Mock client with error
    client = MagicMock(spec=InfluxDBClient)
    client.health.side_effect = Exception("Connection failed")

    # Test connection
    assert verify_connection(client) is False

    # Check output
    out, _ = capsys.readouterr()
    assert "Error connecting to InfluxDB: Connection failed" in out
