# SFTP Cloud Connector

A Python-based SFTP service with MongoDB-backed user management, admin API, telemetry, and real-time client tracking.

## Features

- **Dynamic SFTP Authentication**: Users and admins stored in MongoDB with per-user home directories
- **Admin API**: FastAPI-powered endpoints to manage accounts, review sessions, and view analytics
- **Client Tracking Dashboard**: Auto-refreshing HTML page listing connected clients
- **Connection & Transfer Analytics**: MongoDB collections capture session durations and transferred bytes
- **Secure Defaults**: Password hashing (bcrypt), JWT-protected admin endpoints, and environment-driven configuration

## Requirements

- Python 3.10 or higher
- MongoDB deployment (Atlas or self-hosted)
- The dependencies listed in `requirements.txt`

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

3. Provide configuration (environment variables or `.env` file):

```
MONGODB_URI=mongodb+srv://<user>:<pass>@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=sftp_cloud_connector          # optional
JWT_SECRET=super-secret-string           # required for admin API tokens
ADMIN_DEFAULT_USERNAME=admin             # optional override
ADMIN_DEFAULT_PASSWORD=ChangeMe123!      # optional override (change after first login)
```

4. (Optional) Activate `python-dotenv` by creating a `.env` file in the project root with the variables above.

## Usage

### Starting the SFTP Server

Run the server with:
```bash
python sftp_server.py
```

The server will start on `0.0.0.0:2222` by default.

### Running the Admin API

Launch the management API (default on `127.0.0.1:8000`):

```bash
uvicorn app.admin_api:app --reload
```

Authenticate with the default admin credentials printed when the SFTP server starts (change them immediately). The API exposes endpoints to:

- Obtain a JWT (`POST /auth/login`)
- List, create, and update users (`/users`)
- Inspect active and historical connections (`/connections`, `/me/connections`)
- View aggregate transfer analytics (`/analytics`)

### SFTP Server Configuration

- **Host**: 0.0.0.0 (all interfaces)
- **Port**: 2222
- **Authentication**: MongoDB-backed user accounts (created via admin API)
- **Per-user home directories**: Automatically created under `sftp_root/<home_dir>`

### Connecting to the Server

Create a user via the admin API, then connect using any SFTP client:

```bash
sftp -P 2222 your-user@localhost
```

Using FileZilla or other SFTP clients:
- Host: localhost (or server IP)
- Port: 2222
- Username / Password: values created via API

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
- `sftp_root/<user>/`: Per-user directories automatically created when accounts are provisioned
- MongoDB collections: `users`, `connections`, `transfers`

## Security Note

⚠️ **This is a demonstration/development server.** For production use:
- Rotate the default admin password immediately and enforce strong credentials
- Use network restrictions and TLS/SSL for MongoDB and the admin API
- Consider SSH key authentication and MFA for admins
- Run behind a reverse proxy with HTTPS termination
- Apply rate limiting and audit logging suited to your environment

## Example Workflow

```bash
# Terminal 1: Start the SFTP server
python sftp_server.py

# Terminal 2: Run the admin API
uvicorn app.admin_api:app --reload

# Terminal 3: Authenticate as admin and create a user (pseudo commands)
TOKEN=$(curl -sX POST http://127.0.0.1:8000/auth/login -d '{"username":"admin","password":"ChangeMe123!"}')
curl -X POST http://127.0.0.1:8000/users \
	-H "Authorization: Bearer $TOKEN" \
	-H "Content-Type: application/json" \
	-d '{"username":"testuser","password":"S3cur3Pa55!"}'

# Terminal 4: Connect via SFTP using the newly created account
sftp -P 2222 testuser@localhost
```

## License

MIT License