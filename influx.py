"""InfluxDB connection utility script.

This script establishes a connection to InfluxDB using environment variables
and provides basic functionality to verify connectivity and list buckets.
"""

import os
import sys
from typing import Optional, Tuple

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient


def get_influx_config() -> Tuple[str, Optional[str], Optional[str]]:
    """Get InfluxDB configuration from environment variables.

    Returns:
        Tuple containing (url, token, org)
    """
    load_dotenv()
    return (
        os.getenv("INFLUXDB_URL", "http://localhost:8086"),
        os.getenv("INFLUXDB_TOKEN"),
        os.getenv("INFLUXDB_ORG"),
    )


def validate_config(token: Optional[str], org: Optional[str]) -> bool:
    """Validate that required InfluxDB configuration is present.

    Args:
        token: InfluxDB API token
        org: InfluxDB organization name

    Returns:
        True if configuration is valid, False otherwise
    """
    if not token or not org:
        print("Error: Missing InfluxDB configuration in environment")
        print("Make sure INFLUXDB_URL, INFLUXDB_TOKEN, and INFLUXDB_ORG are set")
        return False
    return True


def verify_connection(client: InfluxDBClient) -> bool:
    """Verify InfluxDB connection and list available buckets.

    Makes a health check request and lists all available buckets to verify
    both connectivity and permissions are working correctly.

    Args:
        client: Configured InfluxDBClient

    Returns:
        True if connection test succeeded, False otherwise
    """
    try:
        health = client.health()
        print(f"InfluxDB connection: {health.status}")

        buckets_api = client.buckets_api()
        buckets = buckets_api.find_buckets().buckets
        print("\nAvailable buckets:")
        for bucket in buckets:
            print(f"- {bucket.name}")

        print("\nInfluxDB connection test successful!")
        return True
    except Exception as e:
        print(f"Error connecting to InfluxDB: {e}")
        return False


def main() -> int:
    """Execute the InfluxDB connection test.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    url, token, org = get_influx_config()

    if not validate_config(token, org):
        return 1

    if token is None or org is None:
        return 1

    try:
        client = InfluxDBClient(
            url=url,
            token=token,  # type: ignore[arg-type]
            org=org,  # type: ignore[arg-type]
        )
        success = verify_connection(client)
        return 0 if success else 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
