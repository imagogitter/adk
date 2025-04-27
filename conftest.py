"""Pytest configuration and fixtures for testing."""
import pytest


# Add your shared fixtures here
@pytest.fixture
def sample_data() -> dict[str, str]:
    """Provide sample data for tests."""
    return {"key": "value"}
