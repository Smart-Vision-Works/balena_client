import subprocess
from balena_tools import BalenaClient, BalenaTunnel
from pprint import pprint

def test_connect_to_online_device():
    # Initialize the BalenaClient
    client = BalenaClient()

    # Query for online devices
    query = {"is_online": True}
    projection = {"uuid": 1, "device_name": 1, "device_tags": 1}
    devices = client.get_devices(query, projection)

    # Ensure there is at least one online device
    assert devices, "No online devices found."

    # Select a random online device
    device = devices[0]  # For simplicity, just take the first one
    device_uuid = device['uuid']

    # Initialize the BalenaTunnel
    tunnel = BalenaTunnel(device_uuid, remote_port=48484)

    # Use the tunnel in a context manager
    with tunnel:
        # Use curl to check the root URL
        curl_command = ["curl", f"http://localhost:{tunnel.local_port}/ping"]
        result = subprocess.run(curl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Check if the expected message is in the response
        assert "OK" in result.stdout, \
            "Expected message not found in the response."