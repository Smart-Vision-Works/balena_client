'''
This module contains a class to open a tunnel to a balena device and interact with it. It uses the balena CLI command `balena device tunnel`.

It will automatically find a free port on the local machine to listen on.

If used with a context manager, it will automatically open and close the tunnel when the context manager block is left.
```python
from balena_tools import BalenaTunnel
import logging

logging.basicConfig(level=logging.INFO)  # Configure logging level
uuid = "your_device_uuid_here"

# Using the class with a context manager
with BalenaTunnel(uuid, remote_port=27017) as tunnel:
    if tunnel.is_open():
        logging.info("Tunnel is active. You can now interact with the device.")
        # Perform any operations here that need the tunnel
        time.sleep(5)  # Simulate some work being done with the tunnel
    else:
        logging.error("Failed to open tunnel.")
# Tunnel automatically closed after the 'with' block
```
'''

import subprocess
import time
import socket
import logging

class BalenaTunnel:
    def __init__(self, uuid, remote_port=27017):
        """
        Initialize the BalenaTunnel object.

        :param uuid: UUID of the balena device.
        :param remote_port: Remote port to tunnel to.
        """
        self._uuid = uuid
        self._remote_port = remote_port
        self._process = None
        self.local_port = self._find_free_port()
        ''' The local port that the tunnel is listening on '''
        self.logger = logging.getLogger(__name__)

    def _find_free_port(self):
        """
        Find a free port on the local machine.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            return s.getsockname()[1]

    def is_open(self):
        """
        Check if the tunnel is open.
        """
        return self._process is not None

    def open(self):
        """
        Opens a tunnel to the specified balena device.
        """
        try:
            tunnel_command = [
                "balena", "device", "tunnel", self._uuid,
                "-p", f"{self._remote_port}:{self.local_port}"
            ]
            self._process = subprocess.Popen(tunnel_command, 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE)
            
            # Wait for tunnel to be established and verify it's running
            for _ in range(10):  # Try for up to 10 seconds
                time.sleep(1)
                if self._process.poll() is not None:  # Process has terminated
                    stdout, stderr = self._process.communicate()
                    self.logger.error(
                        f"Tunnel failed to establish. Exit code: {self._process.returncode}\n"
                        f"stdout: {stdout.decode() if stdout else ''}\n"
                        f"stderr: {stderr.decode() if stderr else ''}"
                    )
                    self._process = None
                    break
                # Check if tunnel is actually listening
                try:
                    result = subprocess.run(['lsof', '-i', f':{self.local_port}'], 
                                          capture_output=True, 
                                          text=True)
                    if 'LISTEN' in result.stdout:
                        return
                except Exception as e:
                    self.logger.error(f"Error checking port: {e}")
                    
            if self._process and self._process.poll() is None:
                pass
            else:
                self.logger.error("Failed to establish tunnel within timeout period")
                self._process = None
                
        except Exception as e:
            self.logger.error(f"Failed to open balena tunnel: {e}")
            self._process = None

    def close(self):
        """
        Closes the tunnel by terminating the process.
        """
        if self._process:
            self._process.terminate()
            self._process.wait()
        else:
            self.logger.warning("No active balena tunnel to close.")

    def __enter__(self):
        """
        Context manager entry point to open the tunnel.
        """
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context manager exit point to close the tunnel.
        """
        self.close()

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)  # Configure logging level
    uuid = "your_device_uuid_here"
    
    # Using the class with a context manager
    with BalenaTunnel(uuid) as tunnel:
        if tunnel.is_open():
            logging.info("Tunnel is active. You can now interact with the device.")
            # Perform any operations here that need the tunnel
            time.sleep(5)  # Simulate some work being done with the tunnel
        else:
            logging.error("Failed to open tunnel.")
# Tunnel automatically closed after the 'with' block
