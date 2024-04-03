from montydb import set_storage, MontyClient
from datetime import datetime, timedelta
from typing import Any, Dict
from dotenv import load_dotenv
import os
from pprint import pprint
import json
import requests
from platformdirs import user_cache_dir
import pickle
from balena import Balena

storage_location = user_cache_dir('balena_client')

# Set the storage engine for MontyDB to use a file-based system
set_storage(
        repository=storage_location,
        storage="flatfile",
        mongo_version="4.0"
)

class BalenaMongoCache:
    def __init__(self, balena_sdk, refresh_interval_seconds: int):
        load_dotenv()
        self.refresh_interval = timedelta(seconds=refresh_interval_seconds)
        self.balena = balena_sdk

        # Set up the MontyDB client
        self.client = MontyClient(storage_location)
        self.db = self.client["device_cache_db"]
        self.devices_collection = self.db["devices"]
        self.applications_collection = self.db["applications"]
        self.release_collection = self.db["releases"]
        self.meta_collection = self.db["meta"]  # A special collection for metadata

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

    def _add_device_tags(self, devices, device_tags):
        '''Add device tags to the devices'''
        device_id_to_device = {device["id"]: device for device in devices}  # Create a mapping of device_id to device
        for device_tag in device_tags:
            device_id = device_tag["device"]["__id"]
            if device_id in device_id_to_device:
                device = device_id_to_device[device_id]
                # Ensure the device has a 'device_tags' dictionary
                device_tags = device.setdefault("device_tags", {})
                # Add the tag_key and value
                device_tags[device_tag["tag_key"]] = device_tag["value"]

    def _update_last_refresh_time(self, collection: str, fleet=None):
        '''Update the last refresh time for the collection.
        This ensures that we can check if the data is stale, according to the refresh interval specified.
        In the case of releases collection, we also need to specify the fleet.
        '''
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
        ''' Refresh the applications collection '''
        applications = self.balena.models.application.get_all()

        self.applications_collection.drop()
        self.applications_collection.insert_many(applications)
        self._update_last_refresh_time("applications")

    def _refresh_devices(self):
        ''' Refresh the devices collection
        Add device tags to the devices, since we almost always want them
        '''
        devices = self.balena.models.device.get_all()
        device_tags = self.balena.models.device.tags.get_all()

        self._add_device_tags(devices, device_tags)

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
                "$select": ["id","commit","created_at","belongs_to__application","is_invalided",
                            "known_issue_list","notes","release_version","revision","semver_build",
                            "semver_major","semver_minor","semver_patch","status"]
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
