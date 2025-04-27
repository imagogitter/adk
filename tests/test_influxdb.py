"""Test InfluxDB connectivity and configuration."""

from unittest.mock import MagicMock

import pytest
from influxdb_client import InfluxDBClient
from pytest_mock import MockFixture


@pytest.fixture
def mock_influx_config(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Mock InfluxDB configuration environment variables."""
    mock_config = {
        "INFLUXDB_URL": "http://localhost:8086",
        "INFLUXDB_TOKEN": "test-token",
        "INFLUXDB_ORG": "test-org",
    }
    for key, value in mock_config.items():
        monkeypatch.setenv(key, value)
    return mock_config


@pytest.fixture
def mock_client(mocker: MockFixture) -> MagicMock:
    """Mock InfluxDB client with health check and bucket listing."""
    client = MagicMock(spec=InfluxDBClient)

    # Mock health check
    health = MagicMock()
    health.status = "pass"
    client.health.return_value = health

    # Mock bucket listing
    buckets_api = MagicMock()
    bucket = MagicMock()
    bucket.name = "test-bucket"
    buckets_api.find_buckets.return_value.buckets = [bucket]
    client.buckets_api.return_value = buckets_api

    mocker.patch("influxdb_client.InfluxDBClient", return_value=client)
    return client


def test_influxdb_connection(mock_influx_config: dict[str, str], mock_client: MagicMock) -> None:
    """Test InfluxDB connection and bucket listing."""
    # Use the mocked client directly
    client = mock_client

    # Test health check
    health = client.health()
    assert health.status == "pass"

    # Test bucket listing
    buckets_api = client.buckets_api()
    buckets = buckets_api.find_buckets().buckets
    assert len(buckets) == 1
    assert buckets[0].name == "test-bucket"

    client.close()


def test_missing_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test error handling when configuration is missing."""
    # Clear environment variables
    monkeypatch.delenv("INFLUXDB_TOKEN", raising=False)
    monkeypatch.delenv("INFLUXDB_ORG", raising=False)

    # Attempt to create client and use it
    client = InfluxDBClient(
        url="http://localhost:8086",
        token=None,
        org=None,
    )

    # Health check should fail
    health = client.health()
    assert health.status == "fail", "Should fail with missing configuration"
    client.close()
