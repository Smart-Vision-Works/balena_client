# Balena Client

This is made to be a more robust method to giving access to Balena for different python project that what we have done in the past at Smart Vision Works. It simplifies and streamlines our use of the Balena SDK.

## Features
* Uses a configurable on-disk cache to store the balena data to speed up the use of the balena SDK. The first calls will take awhile but all subsequent calls will be fast. All calls have the option to bypass the cache.
* Uses MontyDB as the cache, which allows us to search the balena data using mongo queries. More than 90% of other balena wrappers were functions to filter the API data in different ways. This greatly simplifies the interface
* The package is published to the Smart Vision Works GitHub package registry and can be more easily integrated into other projects. You can use it in your project by pip install -e git+https://github.com/Smart-Vision-Works/balena_client.
* Dependencies for this python module are managed by PDM.
* Gives the ability to preload balena data if you wanted to do it at program startup to speed up the use of the balena SDK. Best to make calls in a thread.

## Example usage
```python
    client = BalenaClient(1000)

    query = {"device_name":{"$regex": "SVW-CB.*"}}
    projection = {"device_name": 1, "uuid": 1, "is_online": 1, "device_tags": 1}
    devices = client.get_devices(query, projection)

    applications = client.get_applications({"app_name": "Tater_SAI"}, {"app_name": 1, "id": 1, "uuid": 1})

    releases = client.get_releases(fleet="FM_HUB_K1", query={"release_tags.version": "v1.0.10"})
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
BALENA_AUTH_TOKEN=Gmh4v8ymkUdhgjGo32C2WBlUXfwdno0C
```
