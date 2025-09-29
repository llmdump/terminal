import paramiko
import socket
import threading
import sys

#this function handles the pseudo-terminal streams
def run_app(stdin:SSHChannelHandler, stdout:SSHChannelHandler):
    #send a welcome message to the client
    print("Welcome to SSH demo!", file=stdout)
    
    #echo back whatever the client types
    while True:
        try:
            #read input from the client
            data:str = stdin
            if not data:
                break
            # Check for Ctrl+D (EOF) or Ctrl+C (interrupt)
            if  '\x04' in data or '\x03' in data:
                print("Session closed.", file=stdout)
                break

            # Process the input (echo it back)
            print(f"You typed: {data.strip()}", file=stdout)

            # Exit command
            if data.strip().lower() == "exit":
                break
        except Exception as e:
            print(f"error in run_app: {e}")
            break

#custom ssh server interface
class SimpleSSHServer(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()
    
    def check_channel_request(self, kind, chanid):
        #only allow session channels
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
    
    def check_auth_password(self, username, password):
        #accept any username/password combination
        print(f"authentication attempt with username: {username}, password: {password}")
        return paramiko.AUTH_SUCCESSFUL
    
    def check_auth_publickey(self, username, key):
        #accept any public key
        print(f"public key authentication attempt with username: {username}")
        return paramiko.AUTH_SUCCESSFUL
    
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        #accept PTY requests
        print(f"pty request received for term: {term}")
        return True
    
    def check_channel_shell_request(self, channel):
        #accept shell requests
        print("shell request received")
        self.event.set()
        return True

#custom channel handler
class SSHChannelHandler:
    def __init__(self, channel):
        self.channel = channel
        self.buffer = ""
    
    def readline(self):
        #read a line from the channel
        while True:
            if '\n' in self.buffer:
                line, self.buffer = self.buffer.split('\n', 1)
                return line + '\n'
            
            try:
                chunk = self.channel.recv(1024)
                if not chunk:
                    #connection closed
                    if self.buffer:
                        line = self.buffer
                        self.buffer = ""
                        return line
                    return None
                
                self.buffer += chunk.decode('utf-8')
            except Exception as e:
                print(f"error reading from channel: {e}")
                return None
    
    def write(self, data):
        #write data to the channel
        try:
            self.channel.send(data.encode('utf-8'))
        except Exception as e:
            print(f"error writing to channel: {e}")
    
    def flush(self):
        #flush is a no-op for ssh channels
        pass

#main ssh server function
def start_ssh_server(host='localhost', port=2200):
    #create a socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    #bind and listen
    try:
        sock.bind((host, port))
        sock.listen(100)
        print(f"ssh server listening on {host}:{port}")
    except Exception as e:
        print(f"failed to bind socket: {e}")
        sys.exit(1)
    
    #handle connections
    while True:
        try:
            client, addr = sock.accept()
            print(f"connection from {addr[0]}:{addr[1]}")
            
            #create a transport
            transport = paramiko.Transport(client)
            transport.load_server_moduli()
            transport.add_server_key(paramiko.RSAKey(filename='/workspaces/terminal/test_rsa.key'))
            
            #create a server interface
            server = SimpleSSHServer()
            try:
                transport.start_server(server=server)
            except paramiko.ssh_exception.SSHException as e:
                print(f"ssh negotiation failed: {e}")
                continue
            
            #accept a channel
            channel = transport.accept(20)
            if channel is None:
                print("no channel")
                continue
            
            #wait for shell request event
            server.event.wait(10)
            if not server.event.is_set():
                print("shell request not received")
                continue
            
            #create pseudo streams
            stdin = SSHChannelHandler(channel)
            stdout = SSHChannelHandler(channel)
            
            #call the run_app function
            run_app(stdin, stdout)
            
            #close the channel and transport
            channel.close()
            transport.close()
        except KeyboardInterrupt:
            print("\nshutting down server")
            break
        except Exception as e:
            print(f"error: {e}")

if __name__ == "__main__":
    start_ssh_server()