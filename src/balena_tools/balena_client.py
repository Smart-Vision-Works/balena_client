'''
BalenaClient is a class that wraps the Balena SDK and BalenaMongoCache to provide a more user-friendly interface to the Balena API.

The BalenaMongoCache is a class that caches data from the Balena API to avoid making unnecessary API calls. The cached data is stored in a local MongoDB database using montydb.

The BalenaClient class requires an authentication token to be set in the BALENA_AUTH_TOKEN environment variable or in a .balena/token file in the user's home directory (this is what is generated with `balena login`).

When adding additional methods to the BalenaClient class, used the cached data from BalenaMongoCache to avoid making unnecessary API calls, where it makes sense to do so.

## Example code

```python
    
client = BalenaClient(1000)

query = {"device_name":{"$regex": "SVW-CB.*"}}
projection = {"device_name": 1, "uuid": 1, "is_online": 1, "device_tags": 1}
devices = client.get_devices(query, projection)

applications = client.get_applications({"app_name": "Tater_SAI"}, {"app_name": 1, "id": 1, "uuid": 1})

releases = client.get_releases(fleet="FM_HUB_K1", query={"release_tags.version": "v1.0.10"})
```

'''

from pathlib import Path
import json
from .balena_mongo_cache import BalenaMongoCache
from pprint import pprint
from typing import Any, Dict
from balena import Balena
import os
import re

def auth_token():
    """Load the Balena Auth Token from environment or file and returns it. Can be used outside of BalenaClient."""
    token = os.getenv('BALENA_AUTH_TOKEN')
    if token:
        return token
    token_file = Path.home() / '.balena/token'
    if token_file.exists():
        with open(token_file, 'r') as file:
            token = file.read().strip()
        return token
    return None

class BalenaClient:
    def __init__(self, cache_duration_seconds:int=3600):
        '''
        Initialize the BalenaClient.

        :param cache_duration_seconds (int): The duration in seconds for which to cache data from the Balena API.
        The default is 3600 seconds (1 hour).
        '''
        # Load environment variables from .env file if it exists
        self._setup_balena_client()
        self._mongo_cache = BalenaMongoCache(self.balena, cache_duration_seconds)

    @property
    def auth_token(self):
        """Expose the auth token outside of BalenaClient."""
        return self._auth_token

    def _setup_balena_client(self):
        # Set up the Balena client
        self.balena = Balena({
            "api_version": "v7",
            "retry_rate_limited_request":True})
        self._auth_token = auth_token()
        if self._auth_token:
            self.balena.auth.login_with_token(self._auth_token)
        else:
            raise ValueError("Balena Authentication Token not found.")

        logged_in = self.balena.auth.is_logged_in()
        if not logged_in:
            raise ValueError("Token didn't allow us to log in to balena.")


    def preload_devices(self):
        ''' Preload devices from balena API. Helpful if you want to avoid the delay of the first API call and have time before you need the data. '''
        print('Preloading devices from balena API...')
        self._mongo_cache.refresh_data('devices')

    def preload_applications(self):
        ''' Preload applications from balena API. Helpful if you want to avoid the delay of the first API call and have time before you need the data. '''
        self._mongo_cache.refresh_data('applications')

    def preload_releases(self, fleet:str):
        ''' Preload releases from balena API. Helpful if you want to avoid the delay of the first API call and have time before you need the data. '''
        self._mongo_cache.refresh_data('releases', fleet)
        
    def get_devices(self, query: Dict[str, Any], projection={}, bypass_cache=False):
        """
        Retrieve balena devices with optional filtering.

        :param query (Dict[str, Any]): A mongo query to filter the devices.
        :param projection (Dict[str, Any]): A mongo projection to shape the returned data.
        :param bypass_cache (bool): If True, bypass the cache and retrieve the data from the Balena API.

        ### Sample device document:
        ```json
        {
            "id": 6984936,
            "belongs_to__application": {
              "__id": 1803989
            },
            "belongs_to__user": null,
            "actor": 10360108,
            "should_be_running__release": {
              "__id": 2347217
            },
            "device_name": "Wilcox Lane 8",
            "is_of__device_type": {
              "__id": 58
            },
            "uuid": "107d9719651cdc7c53040eda1ba3f352",
            "is_running__release": {
              "__id": 2347217
            },
            "note": null,
            "local_id": null,
            "status": "Idle",
            "is_online": true,
            "last_connectivity_event": "2024-03-22T05:07:26.026Z",
            "is_connected_to_vpn": true,
            "last_vpn_event": "2024-03-22T05:07:26.026Z",
            "ip_address": "10.201.1.99",
            "mac_address": "B8:27:EB:7C:48:57 96:AE:A1:03:FA:98",
            "public_address": "199.19.118.130",
            "os_version": "balenaOS 2.98.12",
            "os_variant": "prod",
            "supervisor_version": "12.11.38",
            "should_be_managed_by__supervisor_release": null,
            "should_be_operated_by__release": {
              "__id": 2160616
            },
            "is_managed_by__service_instance": {
              "__id": 131437
            },
            "provisioning_progress": null,
            "provisioning_state": "",
            "download_progress": null,
            "is_web_accessible": false,
            "longitude": "-111.7855",
            "latitude": "43.8125",
            "location": "Rexburg, Idaho, United States",
            "custom_longitude": null,
            "custom_latitude": null,
            "is_locked_until__date": null,
            "is_accessible_by_support_until__date": null,
            "created_at": "2022-06-02T22:46:09.108Z",
            "modified_at": "2024-04-01T14:05:01.458Z",
            "is_active": true,
            "api_heartbeat_state": "online",
            "memory_usage": 245,
            "memory_total": 970,
            "storage_block_device": "/dev/mmcblk0p6",
            "storage_usage": 9998,
            "storage_total": 29098,
            "cpu_temp": 49,
            "cpu_usage": 3,
            "cpu_id": "000000008f7c4857",
            "is_undervolted": false,
            "logs_channel": null,
            "vpn_address": null,
            "device_tags": {
                "Customer": "Mart",
                "Location": "Robot 02",
                "Plant": "Rupert"
            }
        }
        ```
        """
        devices = self._mongo_cache.find('devices', query, projection, bypass_cache=bypass_cache)
        return devices

    def get_releases(self, fleet, query: Dict[str, Any], projection={}, bypass_cache=False):
        ''' Retrieve balena releases with optional filtering.
        Because the API can be slow for getting all releases you are required to pass a fleet(e.g. fm_sai, tater_sai).

        :param fleet (str): The fleet to get releases for.
        :param query (Dict[str, Any]): A mongo query to filter the releases.
        :param projection (Dict[str, Any]): A mongo projection to shape the returned data.

        ### Sample release document:
        ```json
        {
            "id": 1469485,
            "commit": "bf95b87d4db2f6e17bbbe35b4fd3a10b",
            "created_at": "2020-07-21T15:06:46.272Z",
            "belongs_to__application": {
                "__id": 1590199
            },
            "known_issue_list": null,
            "release_version": null,
            "revision": 58,
            "semver_build": "",
            "semver_major": 0,
            "semver_minor": 0,
            "semver_patch": 0,
            "status": "success",
            "release_tags": {
                "git-sha": "7482dad8a710b04bd1f050a4ea9f0d22c5209640",
                "version": "v1.0.10"
            }
        }
        ```
        '''

        releases = self._mongo_cache.find('releases', query, projection, bypass_cache=bypass_cache, fleet=fleet)
        return releases

    def get_applications(self, query: Dict[str, Any], projection={}, bypass_cache=False):
        ''' Retrieve balena applications with optional filtering.

        Filtering is a mongo query and projection. For example, to filter by application name:
        `mongo_query = {"app_name": "Tater_SAI"}`

        :param query (Dict[str, Any]): A mongo query to filter the applications.
        :param projection (Dict[str, Any]): A mongo projection to shape the returned data.

        ### Sample application document:
        ```json
        {
        	"actor": 7341999,
        	"app_name": "camera_forwarding_sai",
        	"application_type": {"__id": 4},
        	"created_at": "2021-05-26T18:25:25.671Z",
        	"id": 1833192,
        	"is_accessible_by_support_until__date": null,
        	"is_archived": false,
        	"is_discoverable": true,
        	"is_for__device_type": {"__id": 30},
        	"is_host": false,
        	"is_of__class": "fleet",
        	"is_public": false,
        	"is_stored_at__repository_url": null,
        	"organization": {"__id": 56049},
        	"should_be_running__release": {"__id": 2779115},
        	"should_track_latest_release": false,
        	"slug": "admin53/camera_forwarding_sai",
        	"uuid": "44f78cb985994c09a954442cf23b48fa"
        }
        ```
        '''
        applications = self._mongo_cache.find('applications', query, projection, bypass_cache=bypass_cache)
        return applications

    def enable_public_url(self, device_uuids: list):
        '''
        Enable public URLs for devices.

        :param device_uuids (list): A list of device uuids to enable public URLs for.
        '''
        for uuid in device_uuids:
            self.balena.models.device.enable_device_url(uuid)

    def disable_public_url(self, device_uuids: list):
        '''
        Disable public URLs for devices.

        :param device_uuids (list): A list of device uuids to disable public URLs for.
        '''
        for uuid in device_uuids:
            self.balena.models.device.disable_device_url(uuid)

    def reboot_devices(self, device_uuids: list):
        '''
        Reboot devices by their uuids.
        Is possible that the device won't reboot if the update lock is on.

        :param device_uuids (list): A list of device uuids to reboot.
        '''
        for uuid in device_uuids:
            self.balena.models.device.reboot(uuid)

    def _get_release_id_from_identifier(self, fleet: str, release_identifier: str):
        ''' Convert release commit, id, or version to release id. '''
        commit_pattern = r'^[0-9a-f]{32}$'
        id_pattern = r'^\d+$'
        if re.match(commit_pattern, release_identifier):
            releases = self.get_releases(fleet, {"commit": release_identifier}, {'id': 1})
            if len(releases) != 1:
                raise ValueError(f"Expected 1 release for commit {release}, got {len(releases)}")
            release_id = releases[0]['id']
        elif re.match(id_pattern, release_identifier):
            release_id = release_identifier
        else:
            releases = self.get_releases(fleet, {"release_tags.version": release_identifier}, {'id': 1})
            if len(releases) != 1:
                raise ValueError(f"Expected 1 release for version {release}, got {len(releases)}")
            release_id = releases[0]['id']

        return release_id


    def update_device_to_release(self, device_uuid: str, release_identifier: str):
        ''' Update devices to a specific release.

        :param device_uuid (str): The uuid of the device to update.
        :param release_identifier (str): The release to update the device to, can be specified by commit, id, or version (e.g. v1.0.10).
        '''
        # Get fleet from the device so we can get the release_id from the release_identifier
        application_id = self.get_devices({"uuid": device_uuid}, {"belongs_to__application.__id": 1})[0]['belongs_to__application']['__id']
        fleet = self.get_applications({"id": application_id}, {"app_name": 1})[0]['app_name']

        # Get the release_id from the release_identifier
        release_id = self._get_release_id_from_identifier(fleet, release_identifier)

        # Get the release id that the device is currently running
        current_release_id = self.get_devices({"uuid": device_uuid}, {"should_be_running__release.__id": 1})[0]['should_be_running__release']['__id']

        if current_release_id == release_id:
            return False, f"Already at {release_identifier}"

        # Using the API because the SDK device pinning is not working: self.balena.models.device.pin_to_release(device_uuid, int(release_id))
        # https://github.com/balena-io/balena-sdk-python/issues/374
        import requests
        url = f'https://api.balena-cloud.com/v7/device(uuid=\'{device_uuid}\')'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.auth_token}'
        }
        data = {"is_pinned_on__release": int(release_id)}
        response = requests.patch(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            return True, None
        else:
            print(f'response.json(): {response.json()}')
            return False, response.json()

    def is_device_updated(self, device_uuid: str, release_identifier: str):
        ''' Check if a device is updated to a specific release.

        :param device_uuid (str): The uuid of the device to check.
        :param release_identifier (str): The release to check if the device is updated to, can be specified by commit, id, or version (e.g. v1.0.10).
        '''
        # Get fleet from the device so we can get the release_id from the release_identifier
        application_id = self.get_devices({"uuid": device_uuid}, {"belongs_to__application.__id": 1})[0]['belongs_to__application']['__id']
        fleet = self.get_applications({"id": application_id}, {"app_name": 1})[0]['app_name']

        release_id = self._get_release_id_from_identifier(fleet, release_identifier)

        # Makes sense to not use the cache here because we want to know the current state of the device
        device = self.balena.models.device.get(device_uuid)
        return device['is_running__release']['__id'] == int(release_id)

    def is_device_in_local_mode(self, device_uuid_or_id: str):
        ''' Checks if a device is in local mode

        :param device_uuid_or_id (str): The uuid or id of the device to check.
        '''
        return self.balena.models.device.is_in_local_mode(device_uuid_or_id)


if __name__ == "__main__":
    # Example on how to use the BalenaClient
    client = BalenaClient(10000)

    query = {"device_name":{"$regex": "SVW-CB.*"}}
    projection = {"device_name": 1, "uuid": 1, "is_online": 1, "device_tags": 1}
    devices = client.get_devices(query, projection)
    print(f'devices:\n{json.dumps(devices[:5], indent=4)}')

    applications = client.get_applications({"app_name": "Tater_SAI"}, {"app_name": 1, "id": 1, "uuid": 1})
    print(f'applications:\n{json.dumps(applications, indent=4)}')

    releases = client.get_releases(fleet="FM_HUB_K1", query={"release_tags.version": "v1.0.10"})
    print(f'releases:\n{json.dumps(releases, indent=4)}')

    ## Didn't want to put this in a test because it would reboot the device.
    ##client.reboot_devices(["eb43ce84bad4a3f51c3eaba1a8e2ed8b"])

    ## Didn't want to put this in a test because it will update a device
    ##client.update_device_to_release("eb43ce84bad4a3f51c3eaba1a8e2ed8b", "1.11.10")

    ## Check if the device is updated
    ##print('client.is_device_updated("eb43ce84bad4a3f51c3eaba1a8e2ed8b", "f5a48b18902b2ecdf0bf70d7f94c2c30"))
    ##print('device is updated:', client.is_device_updated("eb43ce84bad4a3f51c3eaba1a8e2ed8b", "1.11.10"))



