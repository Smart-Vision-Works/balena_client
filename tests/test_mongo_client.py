import pytest
from unittest.mock import patch, MagicMock
from balena_mongo_cache import BalenaMongoCache
import pickle
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta
import time


@pytest.fixture
def mock_balena():
    with patch('balena_mongo_cache.Balena') as MockBalena:
        # Mock the Balena instance and its methods as needed
        mock_instance = MockBalena.return_value
        mock_instance.auth.login_with_token.return_value = True
        mock_instance.auth.is_logged_in.return_value = True

        with open('tests/data/applications.pkl', 'rb') as f:
            applications = pickle.load(f)
        mock_instance.models.application.get_all.return_value = applications

        with open('tests/data/devices.pkl', 'rb') as f:
            devices = pickle.load(f)
        mock_instance.models.device.get_all.return_value = devices

        with open('tests/data/device_tags.pkl', 'rb') as f:
            device_tags = pickle.load(f)
        mock_instance.models.device.tags.get_all.return_value = device_tags

        with open('tests/data/releases.pkl', 'rb') as f:
            releases = pickle.load(f)
        mock_instance.models.release.get_all_by_application.return_value = releases

        with open('tests/data/release_tags.pkl', 'rb') as f:
            release_tags = pickle.load(f)
        mock_instance.models.release.tags.get_all_by_application.return_value = release_tags
        yield mock_instance

@pytest.fixture
def temporary_storage_location(monkeypatch):
    # Create a temporary directory for the storage_location
    with TemporaryDirectory() as tmp_dir:
        # Use monkeypatch to temporarily replace the global variable
        monkeypatch.setattr('balena_mongo_cache.storage_location', tmp_dir)
        yield tmp_dir  # yields the path to the temporary directory

@pytest.fixture
def balena_cache(mock_balena, temporary_storage_location):
    # Inject the mocked Balena instance into your class constructor if necessary
    cache = BalenaMongoCache(refresh_interval_seconds=2)
    return cache

# Test find with devices collection can find device with device tags
def test_find_devices(balena_cache, mock_balena):
    query = {"device_tags.Customer": "Wada"}
    result = balena_cache.find('devices', query)

    # Assert that the number of documents returned by find is right
    assert len(result) == 67

# Test that we can't do find with the devices collection if we specify a fleet
def test_find_devices_fleet(balena_cache, mock_balena):
    with pytest.raises(ValueError):
        balena_cache.find('devices', {}, {}, bypass_cache=False, fleet="tater_sai")

# Test that we can't do find with the release collection without specifying a fleet
def test_find_releases_no_fleet(balena_cache, mock_balena):
    with pytest.raises(ValueError):
        balena_cache.find('releases', {}, {}, bypass_cache=False)

# Test refreshing applications cache works
def test_find_releases_twice(balena_cache, mock_balena, temporary_storage_location):
    fleet = "tater_sai"
    balena_cache.find('releases', {}, {}, bypass_cache=True, fleet=fleet)
    balena_cache.find('releases', {}, {}, bypass_cache=False, fleet=fleet)
    mock_balena.models.release.get_all_by_application.assert_called_once()
    mock_balena.models.release.tags.get_all_by_application.assert_called_once()

    # Assert that the number of documents in the releases collection is as expected
    assert balena_cache.release_collection.count_documents({}) == 67

    # Assert that there is only one document in the meta collection
    assert balena_cache.meta_collection.count_documents({}) == 1

    # Assert that the meta collection has been updated
    meta = balena_cache.meta_collection.find_one()
    assert meta is not None
    assert meta['value'] is not None
    assert meta['value'] > datetime.now() - timedelta(seconds=1)
    assert meta['collection'] == 'releases'
    assert meta['fleet'] == fleet

# Test refreshing releases
def test_refresh_releases(balena_cache, mock_balena, temporary_storage_location):
    fleet = "tater_sai"
    balena_cache._refresh_releases(fleet)
    mock_balena.models.release.get_all_by_application.assert_called_once()
    mock_balena.models.release.tags.get_all_by_application.assert_called_once()

    # Assert that the number of documents in the releases collection is as expected
    assert balena_cache.release_collection.count_documents({}) == 67

    # Assert that the meta collection has been updated
    meta = balena_cache.meta_collection.find_one()
    assert meta is not None
    assert meta['value'] is not None
    assert meta['value'] > datetime.now() - timedelta(seconds=1)
    assert meta['collection'] == 'releases'
    assert meta['fleet'] == fleet

def test_initialization(balena_cache, mock_balena, temporary_storage_location):
    assert balena_cache.balena is mock_balena
    assert balena_cache.refresh_interval.seconds == 2

    assert balena_cache.client.address == temporary_storage_location
    assert balena_cache.client.db is not None

def test_refresh_devices(balena_cache, mock_balena, temporary_storage_location):
    balena_cache._refresh_devices()

    # Verify methods were called
    mock_balena.models.device.get_all.assert_called_once()
    # Further assertions depending on your test requirements
    assert balena_cache.devices_collection.count_documents({}) == 1308

    # assert that the meta collection has been updated and the timestamp is within 1 second of the current time
    # meta collection: {'meta_key': 'last_refresh_time', 'collection': 'devices', '_id': ObjectId('660c7dfd97df5c1f379eaf2e'), 'value': datetime.datetime(2024, 4, 2, 15, 51, 57, 423000)}
    meta = balena_cache.meta_collection.find_one()
    assert meta is not None
    assert meta['value'] is not None
    assert meta['value'] > datetime.now() - timedelta(seconds=1)

    # assert that the collection in meta is 'devices'
    assert meta['collection'] == 'devices'

def test_refresh_applications(balena_cache, mock_balena, temporary_storage_location):
    balena_cache._refresh_applications()
    mock_balena.models.application.get_all.assert_called_once()

    # Assert that the number of documents in the applications collection is as expected
    assert balena_cache.applications_collection.count_documents({}) == 28

    # Assert that the meta collection has been updated
    meta = balena_cache.meta_collection.find_one()
    assert meta is not None
    assert meta['value'] is not None
    assert meta['value'] > datetime.now() - timedelta(seconds=1)
    assert meta['collection'] == 'applications'

# Test doing two refreshes in the same test and making sure meta collection is updated correctly
def test_refresh_devices_and_applications(balena_cache, mock_balena, temporary_storage_location):
    balena_cache._refresh_devices()
    balena_cache._refresh_applications()

    # Assert that the number of documents in the applications collection is as expected
    assert balena_cache.applications_collection.count_documents({}) == 28

    # Assert that the number of documents in the devices collection is as expected
    assert balena_cache.devices_collection.count_documents({}) == 1308

    # Assert that there are two documents in the meta collection
    assert balena_cache.meta_collection.count_documents({}) == 2

    # Assert that the meta collection has been updated for both devices and applications
    devices_meta = balena_cache.meta_collection.find_one({"collection": "devices"})
    assert devices_meta is not None
    assert devices_meta['value'] is not None
    assert devices_meta['value'] > datetime.now() - timedelta(seconds=1)

    applications_meta = balena_cache.meta_collection.find_one({"collection": "applications"})
    assert applications_meta is not None
    assert applications_meta['value'] is not None
    assert applications_meta['value'] > datetime.now() - timedelta(seconds=1)

# Test that the cache is not refreshed if the last refresh time is within the refresh interval
def test_refresh_devices_twice(balena_cache, mock_balena, temporary_storage_location):
    balena_cache.find('devices', {}, {}, bypass_cache=False)
    balena_cache.find('devices', {}, {}, bypass_cache=False)
    mock_balena.models.device.get_all.assert_called_once()

    # Assert that the number of documents in the devices collection is as expected
    assert balena_cache.devices_collection.count_documents({}) == 1308

    # Assert that there is only one document in the meta collection
    assert balena_cache.meta_collection.count_documents({}) == 1

    # Assert that the meta collection has been updated
    meta = balena_cache.meta_collection.find_one()
    assert meta is not None
    assert meta['value'] is not None
    assert meta['value'] > datetime.now() - timedelta(seconds=1)
    assert meta['collection'] == 'devices'

# Test that the cache is refreshed if the last refresh time is outside the refresh interval
def test_refresh_devices_twice_outside_refresh_interval(balena_cache, mock_balena, temporary_storage_location):
    balena_cache.find('devices', {}, {}, bypass_cache=False)
    time.sleep(3)
    balena_cache.find('devices', {}, {}, bypass_cache=False)
    mock_balena.models.device.get_all.call_count == 2

# Test that the cache is refreshed if bypass_cache is True
def test_refresh_devices_twice_bypass_cache(balena_cache, mock_balena, temporary_storage_location):
    balena_cache.find('devices', {}, {}, bypass_cache=False)
    balena_cache.find('devices', {}, {}, bypass_cache=True)
    mock_balena.models.device.get_all.call_count == 2

