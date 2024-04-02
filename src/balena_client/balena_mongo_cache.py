from montydb import set_storage, MontyClient
from datetime import datetime, timedelta
from typing import Any, Dict
from dotenv import load_dotenv
from balena import Balena
import os
from pprint import pprint
import json
import requests
from platformdirs import user_cache_dir
import pickle

storage_location = user_cache_dir('balena_client')

# Set the storage engine for MontyDB to use a file-based system
set_storage(
        repository=storage_location,
        storage="flatfile",
        mongo_version="4.0"
)

class BalenaMongoCache:
    def __init__(self, refresh_interval_seconds: int):
        load_dotenv()

        # Set up the MontyDB client
        self.client = MontyClient(storage_location)
        self.db = self.client["device_cache_db"]
        self.devices_collection = self.db["devices"]
        self.applications_collection = self.db["applications"]
        self.release_collection = self.db["releases"]
        self.meta_collection = self.db["meta"]  # A special collection for metadata
        
        self.refresh_interval = timedelta(seconds=refresh_interval_seconds)

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

    def _add_release_tags(self, releases, release_tags):
        '''Add release tags to the releases'''
        for release_tag in release_tags:
            release_id = release_tag["release"]["__id"]
            for release in releases:
                if release["id"] == release_id:
                    if not "release_tags" in release:
                        release["release_tags"] = {}
                    release["release_tags"][release_tag["tag_key"]] = release_tag["value"]
                    break

    def __add_device_tags(self, devices, device_tags):
        '''Add device tags to the devices'''
        for device_tag in device_tags:
            device_id = device_tag["device"]["__id"]
            for device in devices:
                if device["id"] == device_id:
                    if not "device_tags" in device:
                        device["device_tags"] = {}
                    device["device_tags"][device_tag["tag_key"]] = device_tag["value"]
                    break

    def _update_last_refresh_time(self, collection: str, fleet=None):
        if fleet is not None:
            self.meta_collection.update_one(
                {"meta_key": "last_refresh_time", "collection": collection, "fleet": fleet},
                {"$set": {"value": datetime.now()}},
                upsert=True
            )
        else:
            self.meta_collection.update_one(
                {"meta_key": "last_refresh_time", "collection": collection},
                {"$set": {"value": datetime.now()}},
                upsert=True
            )

    def _refresh_applications(self):
        applications = self.balena.models.application.get_all()

        self.applications_collection.drop()
        self.applications_collection.insert_many(applications)
        self._update_last_refresh_time("applications")

    def _refresh_devices(self):
        devices = self.balena.models.device.get_all()
        device_tags = self.balena.models.device.tags.get_all()

        self.__add_device_tags(devices, device_tags)

        self.devices_collection.drop()
        self.devices_collection.insert_many(devices)
        self._update_last_refresh_time("devices")
        
    def _refresh_releases(self, fleet):
        '''
        Since the API calls for getting releases are slower, we require that the fleet is specified
        '''

        # Check if fleet is specified
        if fleet is None:
            raise ValueError("Fleet must be specified to refresh releases.")

        # Contruct application slug
        application_slug = f"admin53/{fleet.lower()}"

        options = {
                "$select": ["id","commit","created_at","belongs_to__application","is_invalided","known_issue_list","notes","release_version","revision","semver_build","semver_major","semver_minor","semver_patch","status"]
        }
        releases = self.balena.models.release.get_all_by_application(application_slug, options)
        release_tags = self.balena.models.release.tags.get_all_by_application(application_slug)
        self._add_release_tags(releases, release_tags)

        # Insert the releases into the collection
        self.release_collection.drop()
        self.release_collection.insert_many(releases)

        #self.release_collection.insert_many(releases)
        self._update_last_refresh_time("releases", fleet)
        return releases


    def refresh_data(self, collection: str, fleet:str=None):
        match collection:
            case "devices":
                self._refresh_devices()
            case "applications":
                self._refresh_applications()
            case "releases":
                self._refresh_releases(fleet)
            case _:
                raise ValueError(f"Unknown collection: {collection}")

    def _is_refresh_needed(self, collection, fleet=None) -> bool:
        if fleet is not None:
            meta_info = self.meta_collection.find_one({"meta_key": "last_refresh_time", "collection": collection, "fleet": fleet})
        else:
            meta_info = self.meta_collection.find_one({"meta_key": "last_refresh_time", "collection": collection})
        if not meta_info:
            # If no metadata is present, refresh is needed
            return True
        last_refresh_time = meta_info["value"]
        return datetime.now() - last_refresh_time >= self.refresh_interval

    def find(self, collection: str, query: Dict[str, Any], projection: Dict[str, Any]={}, bypass_cache=False, fleet=None):
        # Make sure that we only specify the fleet if the collection is releases
        if collection != "releases" and fleet is not None:
            raise ValueError("Fleet should only be specified for releases collection.")
        if self._is_refresh_needed(collection) or bypass_cache:
            self.refresh_data(collection, fleet)
        
        projection["_id"] = 0
        data = list(self.db[collection].find(query, projection))
        return data

def main():
    cache = BalenaMongoCache(refresh_interval_seconds=10)
    # Give some time to simulate delay, then try find
    print(cache.find(collection='devices', query = {"device_id": "device1"}))
    print(cache.find(collection='applications', query = {"app_name": "Lane_Monitoring"}))

if __name__ == "__main__":
    main()
