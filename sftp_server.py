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
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import paramiko

from app.config import get_settings
from app.db import get_database
from app.services import ConnectionService, UserService


# Define base directory for all file paths
BASE_DIR = Path(__file__).resolve().parent
CLIENTS_HTML = BASE_DIR / 'clients.html'
HOST_KEY_FILE = BASE_DIR / 'host_key.pem'


try:
    settings = get_settings()
except Exception as exc:  # noqa: BLE001
    print(f"[!] Configuration error: {exc}")
    sys.exit(1)

SFTP_ROOT = settings.sftp_root.resolve()
SFTP_ROOT.mkdir(parents=True, exist_ok=True)

db = get_database()
user_service = UserService(db)
connection_service = ConnectionService(db)
user_service.ensure_default_admin()


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
    """SFTP Server Interface tied to a specific authenticated user."""

    class _CountingIO:
        """Wrap a file object to record transfer metrics."""

        def __init__(self, wrapped, interface: 'SFTPServerInterface', path: str):
            self._wrapped = wrapped
            self._interface = interface
            self._path = path

        def read(self, size=-1):  # noqa: ANN001
            data = self._wrapped.read(size)
            if data:
                self._interface._record_transfer('download', self._path, len(data))
            return data

        def write(self, data):  # noqa: ANN001
            written = self._wrapped.write(data)
            if written:
                size = written if isinstance(written, int) else len(data)
                self._interface._record_transfer('upload', self._path, size)
            return written

        def close(self):
            return self._wrapped.close()

        def __getattr__(self, item):
            return getattr(self._wrapped, item)

    def __init__(self, server, *args, **kwargs):
        super().__init__(server, *args, **kwargs)
        self.server_iface = server
        self.user_doc = server.user_doc or {}
        self.username = self.user_doc.get('username', 'unknown')
        self.global_root = SFTP_ROOT
        home_dir = self.user_doc.get('home_dir') or self.username
        self.user_root = self._compute_user_root(home_dir)
        self.user_root.mkdir(parents=True, exist_ok=True)
        server.transfer_totals = {'upload': 0, 'download': 0}
        server.transfer_log = []

    def _compute_user_root(self, home_dir: str) -> Path:
        candidate = Path(home_dir.strip().replace('\\', '/'))
        safe_parts = [segment for segment in candidate.parts if segment not in ('', '.', '..')]
        safe_path = Path(*safe_parts) if safe_parts else Path(self.username)
        resolved = (self.global_root / safe_path).resolve()
        resolved.relative_to(self.global_root)
        return resolved

    def _normalize_posix(self, path):
        if not path or path == '.':
            return '/'
        path = str(path).replace('\\', '/')
        if len(path) >= 2 and path[1] == ':':
            path = path[2:]
        if not path.startswith('/'):
            path = '/' + path
        parts = []
        for part in path.split('/'):
            if part in ('', '.'):  # skip empty
                continue
            if part == '..':
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        return '/' + '/'.join(parts) if parts else '/'

    def _resolve_local_path(self, path):
        normalized = self._normalize_posix(path)
        rel_path = normalized.strip('/')
        local_path = (self.user_root / rel_path).resolve()
        try:
            local_path.relative_to(self.user_root)
        except ValueError as exc:  # noqa: BLE001
            raise PermissionError(f"Path escapes root: {path}") from exc
        return normalized, local_path

    def _stat_attributes(self, local_path, *, follow_symlinks=True):
        stat_fn = os.stat if follow_symlinks else os.lstat
        try:
            stat_result = stat_fn(local_path)
        except OSError:
            return paramiko.SFTP_NO_SUCH_FILE
        return paramiko.SFTPAttributes.from_stat(stat_result)

    def _record_transfer(self, direction: str, path: str, size: int) -> None:
        if size <= 0:
            return
        record = {
            'path': path,
            'direction': direction,
            'size': size,
            'username': self.username,
            'timestamp': datetime.utcnow(),
        }
        if self.user_doc.get('_id') is not None:
            record['user_id'] = str(self.user_doc['_id'])
        self.server_iface.transfer_log.append(record)
        totals = self.server_iface.transfer_totals
        totals[direction] = totals.get(direction, 0) + size

    def canonicalize(self, path):
        return self._normalize_posix(path)

    def list_folder(self, path):
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        if not local_path.exists() or not local_path.is_dir():
            return paramiko.SFTP_NO_SUCH_FILE
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
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        return self._stat_attributes(local_path)

    def lstat(self, path):
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        return self._stat_attributes(local_path, follow_symlinks=False)

    def open(self, path, flags, attr):  # noqa: ANN001, ARG002
        try:
            normalized, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            mode = ''
            if flags & os.O_WRONLY:
                mode = 'ab' if flags & os.O_APPEND else 'wb'
            elif flags & os.O_RDWR:
                mode = 'a+b' if flags & os.O_APPEND else 'r+b'
            else:
                mode = 'rb'
            if (flags & os.O_CREAT) and not local_path.exists():
                local_path.touch()
            file_obj = open(local_path, mode)
            wrapped = self._CountingIO(file_obj, self, normalized)
            handle = paramiko.SFTPHandle(flags)
            handle.filename = str(local_path)
            if 'r' in mode or '+' in mode:
                handle.readfile = wrapped
            if any(ch in mode for ch in ('w', 'a', '+')):
                handle.writefile = wrapped
            return handle
        except OSError:
            return paramiko.SFTP_PERMISSION_DENIED
        except Exception:
            return paramiko.SFTP_FAILURE
    
    def remove(self, path):
        """Remove a file"""
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        try:
            local_path.unlink()
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
        try:
            local_old.rename(local_new)
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE
    
    def mkdir(self, path, attr):
        """Create a directory"""
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        try:
            local_path.mkdir()
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE
    
    def rmdir(self, path):
        """Remove a directory"""
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        try:
            local_path.rmdir()
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE
    
    def chattr(self, path, attr):
        """Change file attributes"""
        try:
            _, local_path = self._resolve_local_path(path)
        except PermissionError:
            return paramiko.SFTP_PERMISSION_DENIED
        try:
            if attr.st_mode is not None:
                os.chmod(local_path, attr.st_mode)
            if attr.st_uid is not None or attr.st_gid is not None:
                # Windows doesn't support chown, so we skip this
                pass
            if attr.st_atime is not None or attr.st_mtime is not None:
                times = (attr.st_atime or 0, attr.st_mtime or 0)
                os.utime(local_path, times)
            return paramiko.SFTP_OK
        except OSError:
            return paramiko.SFTP_FAILURE


class SSHServer(paramiko.ServerInterface):
    """SSH authentication backend backed by MongoDB."""

    def __init__(self, client_tracker, client_id, address, user_service: UserService, connection_service: ConnectionService):
        self.client_tracker = client_tracker
        self.client_id = client_id
        self.address = address
        self.user_service = user_service
        self.connection_service = connection_service
        self.username = 'unknown'
        self.user_doc: Dict | None = None
        self.connection_id = None
        self.transfer_totals = {'upload': 0, 'download': 0}
        self.transfer_log: List[Dict] = []

    def check_auth_password(self, username, password):  # noqa: ANN001
        user = self.user_service.authenticate(username, password)
        if not user:
            return paramiko.AUTH_FAILED
        self.username = user['username']
        self.user_doc = user
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):  # noqa: ANN001, ARG002
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_subsystem_request(self, channel, name):  # noqa: ANN001, ARG002
        return name == 'sftp'

    def get_allowed_auths(self, username):  # noqa: ANN001
        return 'password'


def handle_client(client_socket, address, host_key, client_tracker):
    """Handle individual client connection"""
    client_id = f"{address[0]}:{address[1]}"
    transport = None
    server = None
    connection_id = None
    
    try:
        # Create SSH transport
        transport = paramiko.Transport(client_socket)
        transport.add_server_key(host_key)
        
        # Set up the SSH server
        server = SSHServer(client_tracker, client_id, address[0], user_service, connection_service)
        
        # Start server - this will handle authentication
        transport.start_server(server=server)
        
        # Wait for client to request a channel
        channel = transport.accept(20)
        if channel is None:
            print(f"[-] Client {client_id} - no channel opened")
            return
        
        # Get authenticated username
        username = server.username
        if not server.user_doc:
            print(f"[-] Authentication failed for client {client_id}")
            return

        # Record connection in the database
        connection_id = connection_service.start_connection(server.user_doc, client_id, address[0])
        server.connection_id = connection_id
        
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
        if connection_id and server is not None:
            try:
                totals = server.transfer_totals if hasattr(server, 'transfer_totals') else {'upload': 0, 'download': 0}
                transfers = server.transfer_log if hasattr(server, 'transfer_log') else []
                connection_service.end_connection(connection_id, totals.get('upload', 0), totals.get('download', 0), transfers)
            except Exception as exc:  # noqa: BLE001
                print(f"[!] Failed to finalize connection record {connection_id}: {exc}")
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
    print(f"[+] Client list available at: {CLIENTS_HTML}")
    print(f"[+] SFTP root directory: {SFTP_ROOT}")
    print("[+] Manage users via the Admin API (uvicorn app.admin_api:app --reload)")
    print(f"[+] Default admin credentials: {settings.admin_default_username} / {settings.admin_default_password}")
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
