import socket
import threading
import paramiko
import os
import sys

# Configuration for the SSH server
# Change this to a file path for the Unix socket
UNIX_SOCKET_PATH = "/home/tanjim/paramiko_ssh.sock"
HOST_KEY_PATH = "test_rsa.key" # Path for a generated host key

class ParamikoServer(paramiko.ServerInterface):
    """
    Custom Paramiko ServerInterface to handle client requests.
    """
    def __init__(self):
        self.event = threading.Event()
        self.terminal_width = 'N/A'
        self.terminal_height = 'N/A'

    def check_auth_none(self, username):
        """
        Allows authentication without a password or key.
        """
        print(f"Authentication attempt with 'none' method for user: {username}")
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        """
        Checks if the requested channel type is allowed.
        """
        print(f"Channel request: kind={kind}, chanid={chanid}")
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        """
        Captures and prints the requested PTY dimensions.
        """
        print(f"PTY requested for channel {channel.get_id()}:")
        print(f"  Terminal type: {term}")
        print(f"  Terminal size (chars): {width}x{height}")
        print(f"  Terminal size (pixels): {pixelwidth}x{pixelheight}")
        
        self.terminal_width = width
        self.terminal_height = height
        
        return True

    def check_channel_shell_request(self, channel):
        """
        Grants a shell request.
        """
        print(f"Shell requested for channel {channel.get_id()}")
        self.event.set() 
        return True

    def check_channel_exec_request(self, channel, command):
        """
        Handles execute command requests.
        """
        print(f"Exec request for channel {channel.get_id()}: command='{command}'")
        channel.send(f"This server received an exec command: '{command.decode('utf-8')}'\n")
        
        if self.terminal_width != 'N/A':
             channel.send(f"Previously requested PTY size (if any): {self.terminal_width}x{self.terminal_height} characters.\n")
        else:
             channel.send("No PTY was requested for this exec session.\n")
        
        channel.send("Closing connection after exec command.\n")
        channel.close()
        return True

    def check_port_forward_request(self, address, port):
        """Disallow port forwarding."""
        print(f"Port forward request to {address}:{port}")
        return False

    def check_global_request(self, kind, msg):
        """Disallow all global requests."""
        print(f"Global request: kind={kind}, msg={msg}")
        return False, None

def generate_host_key():
    """Generates an RSA host key if one doesn't exist."""
    if not os.path.exists(HOST_KEY_PATH):
        print(f"Generating host key at {HOST_KEY_PATH}...")
        try:
            key = paramiko.RSAKey.generate(2048)
            key.write_private_key_file(HOST_KEY_PATH)
            print("Host key generated successfully.")
        except Exception as e:
            print(f"Error generating host key: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Using existing host key: {HOST_KEY_PATH}")

def handle_client(client_socket):
    """
    Handles a single client connection.
    """
    transport = paramiko.Transport(client_socket)
    
    try:
        host_key = paramiko.RSAKey(filename=HOST_KEY_PATH)
        transport.add_server_key(host_key)
    except paramiko.SSHException as e:
        print(f"Failed to load host key: {e}", file=sys.stderr)
        return

    server = ParamikoServer()
    try:
        transport.start_server(server=server)
        
        channel = transport.accept(20)
        
        if channel is None:
            print("Client did not open a channel within 20 seconds.")
            return

        print(f"Client opened channel: {channel.get_id()}")
        
        server.event.wait(10)
        
        if server.event.is_set():
            width = server.terminal_width
            height = server.terminal_height
            
            channel.send(f"Welcome to the Paramiko Terminal Size Server!\r\n")
            channel.send(f"Your terminal size is: {width}x{height} characters.\r\n")
            channel.send("Type 'exit' to disconnect.\r\n")

            while True:
                try:
                    data = channel.recv(1024)
                    if not data:
                        break
                    command = data.decode('utf-8').strip()
                    print(f"Received command from client: {command}")
                    if command == 'exit':
                        channel.send("Goodbye!\r\n")
                        break
                    elif command:
                        channel.send(f"You typed: {command}\r\n")
                    channel.send("$ ")
                except EOFError:
                    break
        
    except paramiko.SSHException as e:
        print(f"SSH negotiation failed: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Error handling client: {e}", file=sys.stderr)
    finally:
        transport.close()
        print("Client disconnected.")

def main():
    """
    Main function to start the SSH server.
    """
    generate_host_key()
    
    # Clean up old socket file if it exists
    if os.path.exists(UNIX_SOCKET_PATH):
        try:
            os.remove(UNIX_SOCKET_PATH)
            print(f"Removed old Unix socket: {UNIX_SOCKET_PATH}")
        except OSError as e:
            print(f"Error removing old Unix socket {UNIX_SOCKET_PATH}: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        # Create a Unix domain socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(UNIX_SOCKET_PATH)
        sock.listen(5)
        print(f"Listening for incoming connections on Unix socket: {UNIX_SOCKET_PATH}")

        # Ensure proper permissions on the socket file (optional, but good for security)
        # os.chmod(UNIX_SOCKET_PATH, 0o660) # Read/write for owner and group

        while True:
            conn, addr = sock.accept()
            print(f"Accepted connection on Unix socket.")
            client_thread = threading.Thread(target=handle_client, args=(conn,))
            client_thread.start()

    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
    finally:
        sock.close()
        # It's good practice to remove the socket file when the server shuts down gracefully
        if os.path.exists(UNIX_SOCKET_PATH):
            try:
                os.remove(UNIX_SOCKET_PATH)
                print(f"Removed Unix socket: {UNIX_SOCKET_PATH}")
            except OSError as e:
                print(f"Error removing Unix socket on shutdown {UNIX_SOCKET_PATH}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()