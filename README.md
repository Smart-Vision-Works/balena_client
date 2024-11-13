# Balena Tools

This is made to be a more robust method to giving access to Balena for different python project that what we have done in the past at Smart Vision Works. It simplifies and streamlines our use of the Balena SDK and parts of the CLI.

## Features
* Uses a configurable on-disk cache (BalenaMongoCache) to store the balena data to speed up the use of the balena SDK. The first calls will take awhile but all subsequent calls will be fast. All calls have the option to bypass the cache.
* Uses MontyDB as the cache, which allows us to search the balena data using mongo queries. More than 90% of other balena wrappers were functions to filter the API data in different ways. This greatly simplifies the interface
* The package is published to the Smart Vision Works GitHub package registry and can be more easily integrated into other projects. You can use it in your project by:

```bash
pip install -e git+https://github.com/Smart-Vision-Works/balena_tools#egg=balena_tools
```
or
```bash
pdm add git+https://github.com/Smart-Vision-Works/balena_tools#egg=balena_tools
```

* Dependencies for this python module are managed by PDM.
* Gives the ability to preload balena data if you wanted to do it at program startup to speed up the use of the balena SDK. Best to make calls in a thread.

## Example usage of BalenaClient
```python
    client = BalenaClient(1000)

    query = {"device_name":{"$regex": "SVW-CB.*"}}
    projection = {"device_name": 1, "uuid": 1, "is_online": 1, "device_tags": 1}
    devices = client.get_devices(query, projection)

    applications = client.get_applications({"app_name": "Tater_SAI"}, {"app_name": 1, "id": 1, "uuid": 1})

    releases = client.get_releases(fleet="FM_HUB_K1", query={"release_tags.version": "v1.0.10"})
```

## Example device document
Here is an example of a device document that shows what fields are available:

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

## BalenaTunnel
BalenaTunnel allows you to programmatically create a tunnel to a device and use it in a context manager. It will pick a random port, that is available on your local machine, to forward to the device.

## Example usage of BalenaTunnel
```python

# Create tunnel with the Balena Supervisor port
tunnel = BalenaTunnel(device_uuid, remote_port=48484)

# Use the tunnel in a context manager
with tunnel:
    # Use curl to check the root URL
    print(f"Using tunnel to {tunnel.device_uuid} on port {tunnel.local_port}")
    curl_command = ["curl", f"http://localhost:{tunnel.local_port}/ping"]
    result = subprocess.run(curl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # Check if the expected message is in the response
    assert "OK" in result.stdout, \
        "Expected message not found in the response."
```

## Running the development environment
PDM is used to manage the dependencies for this project. PDM sets up its own virtual environment and installs the dependencies in that environment. To run the development environment, run the following commands:

```bash
pdm install
pdm run python src/balena_client/balena_client.py
```
By prepending pdm run before anything you want to run it ensures that the correct virtual environment is used. To run the tests, run the following command:

```bash
pdm run pytest
```

## Using secrets in development
The scripts uses secrets for accessing balena. For development use a
.env file with the secrets listed there. It will get loaded automatically if it exists.

```
BALENA_AUTH_TOKEN=GarbageymkUdhgjGo32C2WBlUXfwdno0C
```
