# SFTP Cloud Connector

A Python-based SFTP server with real-time client tracking and web-based monitoring.

## Features

- **SFTP Server**: Fully functional SFTP server built with Paramiko
- **Client Tracking**: Real-time tracking of connected clients
- **Web Interface**: Auto-refreshing HTML page showing connected clients
- **Session Management**: Track client IP addresses, usernames, and connection times

## Requirements

- Python 3.7 or higher
- paramiko library

## Installation

1. Clone the repository:
```bash
git clone https://github.com/hardikhari96/sftp_cloud_connector.git
cd sftp_cloud_connector
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the SFTP Server

Run the server with:
```bash
python sftp_server.py
```

The server will start on `0.0.0.0:2222` by default.

### Server Configuration

- **Host**: 0.0.0.0 (all interfaces)
- **Port**: 2222
- **Username**: Any username (e.g., `testuser`)
- **Password**: `password`
- **SFTP Root**: `./sftp_root` (created automatically)

### Connecting to the Server

Using `sftp` command-line client:
```bash
sftp -P 2222 testuser@localhost
```

Using FileZilla or other SFTP clients:
- Host: localhost (or your server IP)
- Port: 2222
- Username: testuser (or any username)
- Password: password

### Viewing Connected Clients

Open `clients.html` in your web browser to see the list of connected clients. The page auto-refreshes every 5 seconds to show real-time updates.

The HTML page displays:
- Client ID (IP:Port)
- IP Address
- Username
- Connection time
- Connection status (connected/disconnected)

## Files Generated

- `host_key.pem`: SSH host key (generated on first run)
- `clients.html`: Real-time client list (updated automatically)
- `sftp_root/`: Directory for SFTP file storage

## Security Note

⚠️ **This is a demonstration/development server.** For production use:
- Implement proper authentication (not hardcoded passwords)
- Use SSH keys instead of passwords
- Add proper access controls
- Run on appropriate ports with proper firewall rules
- Use HTTPS for the web interface

## Example Session

```bash
# Terminal 1: Start the server
$ python sftp_server.py
[+] Generating new host key and saving to host_key.pem
[+] SFTP Server started on 0.0.0.0:2222
[+] Username: any (use 'testuser' for example)
[+] Password: password
[+] Client list available at: clients.html
[+] SFTP root directory: ./sftp_root
[+] Waiting for connections...

# Terminal 2: Connect as a client
$ sftp -P 2222 testuser@localhost
testuser@localhost's password: [type: password]
Connected to localhost.
sftp> ls
sftp> put myfile.txt
sftp> ls
myfile.txt
sftp> exit

# View clients.html in browser to see connection details
```

## License

MIT License