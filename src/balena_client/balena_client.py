from pathlib import Path
import json
from balena_mongo_cache import BalenaMongoCache
from pprint import pprint
from typing import Any, Dict
from balena import Balena
import os


class BalenaClient:
    def __init__(self, cache_duration=60):
        # Load environment variables from .env file if it exists
        self.setup_balena_client()
        self.mongo_cache = BalenaMongoCache(self.balena, cache_duration)

    def setup_balena_client(self):
        # Set up the Balena client
        self.balena = Balena({
            "api_version": "v6",
            "retry_rate_limited_request":True})
        self.auth_token = self.load_auth_token()
        if self.auth_token:
            self.balena.auth.login_with_token(self.auth_token)
        else:
            raise ValueError("Balena Authentication Token not found.")

        logged_in = self.balena.auth.is_logged_in()
        if not logged_in:
            raise ValueError("Token didn't allow us to log in to balena.")

    @staticmethod
    def load_auth_token():
        """Load the Balena Auth Token from environment or file."""
        token = os.getenv('BALENA_AUTH_TOKEN')
        if token:
            return token
        token_file = Path.home() / '.balena/token'
        if token_file.exists():
            with open(token_file, 'r') as file:
                token = file.read().strip()
            return token
        return None

    def preload_devices(self):
        ''' Preload devices from balena API '''
        self.mongo_cache.refresh_data('devices')

    def preload_applications(self):
        ''' Preload applications from balena API '''
        self.mongo_cache.refresh_data('applications')

    def preload_releases(self, fleet:str):
        ''' Preload releases from balena API '''
        self.mongo_cache.refresh_data('releases', fleet)
        
    def get_devices(self, query: Dict[str, Any], projection={}, bypass_cache=False):
        """Retrieve balena devices with optional filtering.

        Sample device document:
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

          },
        """
        # TODO: document this function and point to json files
        devices = self.mongo_cache.find('devices', query, projection, bypass_cache=bypass_cache)
        return devices

    def get_releases(self, fleet, query: Dict[str, Any], projection={}, bypass_cache=False):
        ''' Retrieve balena releases with optional filtering.
        Because the API can be slow for getting all releases you are required to pass a fleet eg (fm_sai, tater_sai).

        Sample release document:
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
        '''

        releases = self.mongo_cache.find('releases', query, projection, bypass_cache=bypass_cache, fleet=fleet)
        return releases

    def get_applications(self, query: Dict[str, Any], projection={}, bypass_cache=False):
        ''' Retrieve balena applications with optional filtering.

        Filtering is a mongo query and projection. For example, to filter by application name:
        mongo_query = {"app_name": "Tater_SAI"}

        Sample application document:
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
        '''
        applications = self.mongo_cache.find('applications', query, projection, bypass_cache=bypass_cache)
        return applications

    def enable_public_url(self, device_uuids: list):
        for uuid in device_uuids:
            self.balena.models.device.enable_device_url(uuid)

    def disable_public_url(self, device_uuids: list):
        for uuid in device_uuids:
            self.balena.models.device.disable_device_url(uuid)


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





