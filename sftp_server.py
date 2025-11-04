#!/usr/bin/env python3
"""
SFTP Server with Client Tracking
This module implements an SFTP server that tracks connected clients
and generates an HTML file showing the list of connected clients.
"""

import os
import socket
import sys
import threading
import paramiko
from datetime import datetime
from pathlib import Path


class ClientTracker:
    """Tracks connected SFTP clients"""
    
    def __init__(self):
        self.clients = {}
        self.lock = threading.Lock()
    
    def add_client(self, client_id, address, username):
        """Add a new connected client"""
        with self.lock:
            self.clients[client_id] = {
                'address': address,
                'username': username,
                'connected_at': datetime.now(),
                'status': 'connected'
            }
            self.generate_html()
    
    def remove_client(self, client_id):
        """Remove a disconnected client"""
        with self.lock:
            if client_id in self.clients:
                self.clients[client_id]['status'] = 'disconnected'
                self.clients[client_id]['disconnected_at'] = datetime.now()
            self.generate_html()
    
    def generate_html(self):
        """Generate HTML file showing connected clients"""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="5">
    <title>SFTP Server - Connected Clients</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .info {{
            background-color: #e7f3fe;
            border-left: 4px solid #2196F3;
            padding: 10px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .status-connected {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .status-disconnected {{
            color: #f44336;
            font-weight: bold;
        }}
        .timestamp {{
            font-size: 0.9em;
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>SFTP Server - Connected Clients</h1>
    <div class="info">
        <strong>Last Updated:</strong> {timestamp}<br>
        <strong>Total Clients:</strong> {total_clients}<br>
        <strong>Active Connections:</strong> {active_clients}
    </div>
    <table>
        <thead>
            <tr>
                <th>Client ID</th>
                <th>IP Address</th>
                <th>Username</th>
                <th>Connected At</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
{rows}
        </tbody>
    </table>
    <p class="timestamp">Page auto-refreshes every 5 seconds</p>
</body>
</html>
"""
        
        rows = []
        active_count = 0
        
        for client_id, info in self.clients.items():
            status_class = 'status-connected' if info['status'] == 'connected' else 'status-disconnected'
            if info['status'] == 'connected':
                active_count += 1
            
            row = f"""            <tr>
                <td>{client_id}</td>
                <td>{info['address']}</td>
                <td>{info['username']}</td>
                <td>{info['connected_at'].strftime('%Y-%m-%d %H:%M:%S')}</td>
                <td class="{status_class}">{info['status']}</td>
            </tr>"""
            rows.append(row)
        
        if not rows:
            rows.append("""            <tr>
                <td colspan="5" style="text-align: center; color: #999;">No clients connected yet</td>
            </tr>""")
        
        html = html_content.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_clients=len(self.clients),
            active_clients=active_count,
            rows='\n'.join(rows)
        )
        
        with open('clients.html', 'w') as f:
            f.write(html)


class SFTPServerInterface(paramiko.SFTPServerInterface):
    """SFTP Server Interface Implementation"""
    
    def __init__(self, server, *args, **kwargs):
        super().__init__(server, *args, **kwargs)
        self.server_root = os.path.abspath('./sftp_root')
        os.makedirs(self.server_root, exist_ok=True)
    
    def _realpath(self, path):
        """Convert SFTP path to real filesystem path"""
        path = os.path.normpath(path)
        if path.startswith('/'):
            path = path[1:]
        return os.path.join(self.server_root, path)
    
    def list_folder(self, path):
        """List directory contents"""
        real_path = self._realpath(path)
        try:
            entries = []
            for item in os.listdir(real_path):
                item_path = os.path.join(real_path, item)
                stat = os.stat(item_path)
                attr = paramiko.SFTPAttributes.from_stat(stat, item)
                entries.append(attr)
            return entries
        except OSError as e:
            return paramiko.SFTP_FAILURE
    
    def stat(self, path):
        """Get file/directory stats"""
        real_path = self._realpath(path)
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(real_path))
        except OSError:
            return paramiko.SFTP_NO_SUCH_FILE
    
    def lstat(self, path):
        """Get file/directory stats (don't follow symlinks)"""
        real_path = self._realpath(path)
        try:
            return paramiko.SFTPAttributes.from_stat(os.lstat(real_path))
        except OSError:
            return paramiko.SFTP_NO_SUCH_FILE
    
    def open(self, path, flags, attr):
        """Open a file"""
        real_path = self._realpath(path)
        try:
            # Create parent directories if needed
            os.makedirs(os.path.dirname(real_path), exist_ok=True)
            
            mode = 'r'
            if (flags & os.O_WRONLY):
                mode = 'w'
            elif (flags & os.O_RDWR):
                mode = 'r+'
            if (flags & os.O_APPEND):
                mode = 'a'
            
            binary_flag = 'b' if flags & os.O_BINARY else ''
            f = open(real_path, mode + binary_flag)
            fobj = paramiko.SFTPHandle(flags)
            fobj.filename = real_path
            fobj.readfile = f
            fobj.writefile = f
            return fobj
        except Exception as e:
            return paramiko.SFTP_FAILURE
    
    def remove(self, path):
        """Remove a file"""
        real_path = self._realpath(path)
        try:
            os.remove(real_path)
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE
    
    def rename(self, oldpath, newpath):
        """Rename a file or directory"""
        real_oldpath = self._realpath(oldpath)
        real_newpath = self._realpath(newpath)
        try:
            os.rename(real_oldpath, real_newpath)
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE
    
    def mkdir(self, path, attr):
        """Create a directory"""
        real_path = self._realpath(path)
        try:
            os.mkdir(real_path)
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE
    
    def rmdir(self, path):
        """Remove a directory"""
        real_path = self._realpath(path)
        try:
            os.rmdir(real_path)
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE


class SSHServer(paramiko.ServerInterface):
    """SSH Server Interface for authentication"""
    
    def __init__(self, client_tracker, client_id, address, username):
        self.client_tracker = client_tracker
        self.client_id = client_id
        self.address = address
        self.username = username
    
    def check_auth_password(self, username, password):
        """Check password authentication"""
        # For demo purposes, accept any username with password 'password'
        # In production, use proper authentication
        if password == 'password':
            self.username = username
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED
    
    def check_channel_request(self, kind, chanid):
        """Handle channel requests"""
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
    
    def check_channel_subsystem_request(self, channel, name):
        """Handle subsystem requests"""
        if name == 'sftp':
            return True
        return False
    
    def get_allowed_auths(self, username):
        """Return allowed authentication methods"""
        return 'password'


def handle_client(client_socket, address, host_key, client_tracker):
    """Handle individual client connection"""
    client_id = f"{address[0]}:{address[1]}"
    
    try:
        # Create SSH transport
        transport = paramiko.Transport(client_socket)
        transport.add_server_key(host_key)
        transport.set_subsystem_handler('sftp', paramiko.SFTPServer, SFTPServerInterface)
        
        # Set up the SSH server
        username = 'unknown'
        server = SSHServer(client_tracker, client_id, address[0], username)
        transport.start_server(server=server)
        
        # Wait for authentication and channel
        channel = transport.accept(20)
        if channel is None:
            print(f"[-] Client {client_id} failed to open channel")
            return
        
        # Get authenticated username
        username = server.username
        
        # Track the client
        client_tracker.add_client(client_id, address[0], username)
        print(f"[+] Client connected: {client_id} ({username})")
        
        # Wait for the client to disconnect
        while transport.is_active():
            if channel.closed:
                break
            import time
            time.sleep(0.5)
        
    except Exception as e:
        print(f"[-] Error handling client {client_id}: {e}")
    finally:
        client_tracker.remove_client(client_id)
        print(f"[-] Client disconnected: {client_id}")
        try:
            client_socket.close()
        except:
            pass


def generate_host_key():
    """Generate or load SSH host key"""
    key_file = 'host_key.pem'
    
    if os.path.exists(key_file):
        print(f"[+] Loading existing host key from {key_file}")
        host_key = paramiko.RSAKey.from_private_key_file(key_file)
    else:
        print(f"[+] Generating new host key and saving to {key_file}")
        host_key = paramiko.RSAKey.generate(2048)
        host_key.write_private_key_file(key_file)
    
    return host_key


def main():
    """Main server function"""
    # Configuration
    HOST = '0.0.0.0'
    PORT = 2222
    
    # Initialize client tracker
    client_tracker = ClientTracker()
    client_tracker.generate_html()  # Generate initial HTML
    
    # Generate or load host key
    host_key = generate_host_key()
    
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    print(f"[+] SFTP Server started on {HOST}:{PORT}")
    print(f"[+] Username: any (use 'testuser' for example)")
    print(f"[+] Password: password")
    print(f"[+] Client list available at: clients.html")
    print(f"[+] SFTP root directory: ./sftp_root")
    print("[+] Waiting for connections...")
    
    try:
        while True:
            client_socket, address = server_socket.accept()
            print(f"[+] Connection from {address[0]}:{address[1]}")
            
            # Handle each client in a separate thread
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, address, host_key, client_tracker)
            )
            client_thread.daemon = True
            client_thread.start()
    
    except KeyboardInterrupt:
        print("\n[!] Server shutting down...")
    finally:
        server_socket.close()


if __name__ == '__main__':
    main()
