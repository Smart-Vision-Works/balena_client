import subprocess
import time
import socket

class BalenaTunnel:
    def __init__(self, uuid, remote_port=27017):
        """
        Initialize the BalenaTunnel object.

        :param uuid: UUID of the balena device.
        :param remote_port: Remote port to tunnel to.
        """
        self.uuid = uuid
        self.remote_port = remote_port
        self.local_port = self._find_free_port()
        self.process = None

    def _find_free_port(self):
        """
        Find a free port on the local machine.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            return s.getsockname()[1]

    def open(self):
        """
        Opens a tunnel to the specified balena device.
        """
        try:
            tunnel_command = [
                "balena", "device", "tunnel", self.uuid,
                "-p", f"{self.remote_port}:{self.local_port}"
            ]
            print(f"Starting tunnel with command: {' '.join(tunnel_command)}")
            self.process = subprocess.Popen(tunnel_command, 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE)
            
            # Wait for tunnel to be established and verify it's running
            for _ in range(10):  # Try for up to 10 seconds
                time.sleep(1)
                if self.process.poll() is not None:  # Process has terminated
                    stdout, stderr = self.process.communicate()
                    print(f"Tunnel failed to establish. Exit code: {self.process.returncode}")
                    print(f"stdout: {stdout.decode() if stdout else ''}")
                    print(f"stderr: {stderr.decode() if stderr else ''}")
                    self.process = None
                    break
                # Check if tunnel is actually listening
                try:
                    result = subprocess.run(['lsof', '-i', f':{self.local_port}'], 
                                          capture_output=True, 
                                          text=True)
                    if 'LISTEN' in result.stdout:
                        print(f"Tunnel established and listening on port {self.local_port}")
                        return
                except Exception as e:
                    print(f"Error checking port: {e}")
                    
            if self.process and self.process.poll() is None:
                print("Balena tunnel established.")
            else:
                print("Failed to establish tunnel within timeout period")
                self.process = None
                
        except Exception as e:
            print(f"Failed to open balena tunnel: {e}")
            self.process = None

    def close(self):
        """
        Closes the tunnel by terminating the process.
        """
        if self.process:
            self.process.terminate()
            self.process.wait()
            print("Balena tunnel closed.")
        else:
            print("No active balena tunnel to close.")

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
    uuid = "your_device_uuid_here"
    
    # Using the class with a context manager
    with BalenaTunnel(uuid) as tunnel:
        # The tunnel is now open and available for use
        print("Tunnel is active. You can now interact with the device.")
        # Perform any operations here that need the tunnel
        time.sleep(5)  # Simulate some work being done with the tunnel
    # Tunnel automatically closed after the 'with' block
