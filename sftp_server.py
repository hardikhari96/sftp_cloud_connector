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


# Define base directory for all file paths
BASE_DIR = Path(__file__).resolve().parent
CLIENTS_HTML = BASE_DIR / 'clients.html'
HOST_KEY_FILE = BASE_DIR / 'host_key.pem'
SFTP_ROOT = BASE_DIR / 'sftp_root'


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
        
        # Write HTML file using absolute path
        with open(CLIENTS_HTML, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # Set restrictive permissions on the HTML file (Unix/Linux only)
        if sys.platform != 'win32':
            os.chmod(CLIENTS_HTML, 0o644)


class SFTPServerInterface(paramiko.SFTPServerInterface):
    """SFTP Server Interface Implementation"""
    
    def __init__(self, server, *args, **kwargs):
        super().__init__(server, *args, **kwargs)
        # Keep everything rooted under the published SFTP directory
        self.server_root = SFTP_ROOT.resolve()
        self.server_root.mkdir(parents=True, exist_ok=True)
    
    def _normalize_posix(self, path):
        """Return a canonical POSIX path string rooted at '/'"""
        if not path or path == '.':
            return '/'
        path = str(path).replace('\\', '/')
        if len(path) >= 2 and path[1] == ':':
            path = path[2:]
        if not path.startswith('/'):
            path = '/' + path
        parts = []
        for part in path.split('/'):
            if not part or part == '.':
                continue
            if part == '..':
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        return '/' + '/'.join(parts) if parts else '/'
    
    def _resolve_local_path(self, path):
        """Map an SFTP path to a local filesystem path within server_root"""
        normalized = self._normalize_posix(path)
        rel_parts = [p for p in normalized.strip('/').split('/') if p]
        rel_path = Path(*rel_parts) if rel_parts else Path()
        local_path = (self.server_root / rel_path).resolve()
        try:
            common = os.path.commonpath([str(local_path), str(self.server_root)])
        except ValueError:
            raise PermissionError(f"Invalid path: {path}")
        if common != str(self.server_root):
            raise PermissionError(f"Path escapes root: {path}")
        return normalized, local_path
    
    def canonicalize(self, path):
        """Return the canonical form of a path"""
        return self._normalize_posix(path)
    
    def list_folder(self, path):
        """List directory contents"""
        try:
            _, local_path = self._resolve_local_path(path)
            if not local_path.exists() or not local_path.is_dir():
                return paramiko.SFTP_NO_SUCH_FILE
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        entries = []
        try:
            for item in sorted(local_path.iterdir(), key=lambda p: p.name.lower()):
                stat_result = item.stat()
                attr = paramiko.SFTPAttributes.from_stat(stat_result, item.name)
                attr.filename = item.name
                entries.append(attr)
        except OSError:
            return paramiko.SFTP_FAILURE
        return entries
    
    def stat(self, path):
        """Get file/directory stats"""
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        real_path = str(local_path)
        try:
            return paramiko.SFTPAttributes.from_stat(os.stat(real_path))
        except OSError:
            return paramiko.SFTP_NO_SUCH_FILE
    
    def lstat(self, path):
        """Get file/directory stats (don't follow symlinks)"""
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        real_path = str(local_path)
        try:
            return paramiko.SFTPAttributes.from_stat(os.lstat(real_path))
        except OSError:
            return paramiko.SFTP_NO_SUCH_FILE
    
    def open(self, path, flags, attr):
        """Open a file"""
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        real_path = str(local_path)
        try:
            # Create parent directories if needed
            os.makedirs(os.path.dirname(real_path), exist_ok=True)
            
            # Determine file mode based on flags
            mode = ''
            if (flags & os.O_WRONLY):
                if (flags & os.O_APPEND):
                    mode = 'ab'
                else:
                    mode = 'wb'
            elif (flags & os.O_RDWR):
                if (flags & os.O_APPEND):
                    mode = 'a+b'
                else:
                    mode = 'r+b'
            else:
                mode = 'rb'
            
            # Try to open the file
            if (flags & os.O_CREAT) and not os.path.exists(real_path):
                # Create the file if it doesn't exist
                f = open(real_path, 'wb')
                f.close()
            
            f = open(real_path, mode)
            fobj = paramiko.SFTPHandle(flags)
            fobj.filename = real_path
            fobj.readfile = f
            fobj.writefile = f
            return fobj
        except IOError as e:
            return paramiko.SFTP_PERMISSION_DENIED
        except Exception as e:
            return paramiko.SFTP_FAILURE
    
    def remove(self, path):
        """Remove a file"""
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        real_path = str(local_path)
        try:
            os.remove(real_path)
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE
    
    def rename(self, oldpath, newpath):
        """Rename a file or directory"""
        try:
            _, local_old = self._resolve_local_path(oldpath)
            _, local_new = self._resolve_local_path(newpath)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        real_oldpath = str(local_old)
        real_newpath = str(local_new)
        try:
            os.rename(real_oldpath, real_newpath)
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE
    
    def mkdir(self, path, attr):
        """Create a directory"""
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        real_path = str(local_path)
        try:
            os.mkdir(real_path)
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE
    
    def rmdir(self, path):
        """Remove a directory"""
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        real_path = str(local_path)
        try:
            os.rmdir(real_path)
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE
    
    def chattr(self, path, attr):
        """Change file attributes"""
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        real_path = str(local_path)
        try:
            if attr.st_mode is not None:
                os.chmod(real_path, attr.st_mode)
            if attr.st_uid is not None or attr.st_gid is not None:
                # Windows doesn't support chown, so we skip this
                pass
            if attr.st_atime is not None or attr.st_mtime is not None:
                times = (attr.st_atime or 0, attr.st_mtime or 0)
                os.utime(real_path, times)
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
        # SECURITY WARNING: In production, use proper authentication:
        # - Store hashed passwords in a database
        # - Use SSH keys instead of passwords
        # - Implement rate limiting and account lockout
        # - Use environment variables for credentials
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
    transport = None
    
    try:
        # Create SSH transport
        transport = paramiko.Transport(client_socket)
        transport.add_server_key(host_key)
        
        # Set up the SSH server
        username = 'unknown'
        server = SSHServer(client_tracker, client_id, address[0], username)
        
        # Start server - this will handle authentication
        transport.start_server(server=server)
        
        # Wait for client to request a channel
        channel = transport.accept(20)
        if channel is None:
            print(f"[-] Client {client_id} - no channel opened")
            return
        
        # Get authenticated username
        username = server.username
        
        # Track the client
        client_tracker.add_client(client_id, address[0], username)
        print(f"[+] Client connected: {client_id} ({username})")
        
        # Start SFTP server on this channel
        sftp_server = paramiko.SFTPServer(channel, 'sftp', server, SFTPServerInterface)
        sftp_server.start()
        
        # Wait for the SFTP server to finish (client disconnects)
        sftp_server.join()
        
    except Exception as e:
        print(f"[-] Error handling client {client_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client_tracker.remove_client(client_id)
        print(f"[-] Client disconnected: {client_id}")
        if transport:
            try:
                transport.close()
            except OSError:
                pass
        try:
            client_socket.close()
        except OSError:
            pass


def generate_host_key():
    """Generate or load SSH host key"""
    if HOST_KEY_FILE.exists():
        print(f"[+] Loading existing host key from {HOST_KEY_FILE}")
        host_key = paramiko.RSAKey.from_private_key_file(str(HOST_KEY_FILE))
    else:
        print(f"[+] Generating new host key and saving to {HOST_KEY_FILE}")
        host_key = paramiko.RSAKey.generate(2048)
        host_key.write_private_key_file(str(HOST_KEY_FILE))
        
        # Set restrictive permissions on the key file (Unix/Linux only)
        if sys.platform != 'win32':
            os.chmod(HOST_KEY_FILE, 0o600)
    
    return host_key


def main():
    """Main server function"""
    # Configuration
    # NOTE: Binding to 0.0.0.0 allows connections from any network interface.
    # This is intentional for a server application. In production:
    # - Consider binding to a specific interface if not needed publicly
    # - Use firewall rules to restrict access
    # - Implement IP whitelisting if appropriate
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
    print(f"[+] Client list available at: {CLIENTS_HTML}")
    print(f"[+] SFTP root directory: {SFTP_ROOT}")
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
