"""
Integration test configuration.
"""
import pytest
import os


@pytest.fixture
def api_base_url():
    """Base URL for API tests."""
    return os.getenv("TEST_API_URL", "http://localhost:8000")


@pytest.fixture
def test_token():
    """Mock JWT token for testing."""
    # In real tests, generate a valid Supabase JWT or use a test token
    return os.getenv("TEST_JWT_TOKEN", "test-token-not-validated-in-mock-mode")


@pytest.fixture
def sample_image_path():
    """Path to sample test image."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "sample.png")


@pytest.fixture
def use_mock_adapter():
    """Whether to use mock adapter for tests."""
    return os.getenv("USE_MOCK_ADAPTER", "true").lower() == "true"
