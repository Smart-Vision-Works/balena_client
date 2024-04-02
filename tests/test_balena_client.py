import pytest
from unittest.mock import MagicMock
from balena_client import BalenaClient

@pytest.fixture
def mock_cache():
    """Fixture to create a mock BalenaMongoCache instance."""
    return MagicMock()

@pytest.fixture
def balena_client(mock_cache):
    """Fixture to create a BalenaClient instance with a mocked cache."""
    client = BalenaClient()
    client.mongo_cache = mock_cache
    return client

def test_preload_devices(balena_client, mock_cache):
    balena_client.preload_devices()
    mock_cache.refresh_data.assert_called_once_with('devices')

def test_preload_applications(balena_client, mock_cache):
    balena_client.preload_applications()
    mock_cache.refresh_data.assert_called_once_with('applications')

def test_preload_releases(balena_client, mock_cache):
    fleet = "test_fleet"
    balena_client.preload_releases(fleet)
    mock_cache.refresh_data.assert_called_once_with('releases', fleet)

def test_get_devices(balena_client, mock_cache):
    query = {"device_name": {"$regex": "SVW-CB.*"}}
    projection = {"device_name": 1, "uuid": 1, "is_online": 1}
    balena_client.get_devices(query, projection)
    mock_cache.find.assert_called_once_with('devices', query, projection, bypass_cache=False)

def test_get_releases(balena_client, mock_cache):
    fleet = "FM_HUB_K1"
    query = {"release_tags.version": "v1.0.10"}
    balena_client.get_releases(fleet, query)
    mock_cache.find.assert_called_once_with('releases', query, {}, bypass_cache=False, fleet=fleet)

def test_get_applications(balena_client, mock_cache):
    query = {"app_name": "Tater_SAI"}
    projection = {"app_name": 1, "id": 1, "uuid": 1}
    balena_client.get_applications(query, projection)
    mock_cache.find.assert_called_once_with('applications', query, projection, bypass_cache=False)
