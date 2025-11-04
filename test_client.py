#!/usr/bin/env python3
"""Test SFTP client to connect to the server"""

import paramiko
import sys

def test_sftp_connection():
    """Test connecting to the SFTP server"""
    # Connection parameters
    hostname = 'localhost'
    port = 2222
    username = 'testuser'
    password = 'password'
    
    try:
        # Create transport
        transport = paramiko.Transport((hostname, port))
        transport.connect(username=username, password=password)
        
        # Create SFTP client
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        print(f"[+] Connected to SFTP server as {username}")
        
        # List files
        print("\n[+] Listing files in root directory:")
        files = sftp.listdir('.')
        for f in files:
            print(f"  - {f}")
        
        # Get current directory
        cwd = sftp.getcwd() if sftp.getcwd() else '/'
        print(f"\n[+] Current directory: {cwd}")
        
        # Create a test file
        print("\n[+] Creating test file...")
        with sftp.open('/uploaded_test.txt', 'w') as f:
            f.write('This is a test file uploaded via SFTP\n')
        print("  File created successfully!")
        
        # List files again
        print("\n[+] Listing files after upload:")
        files = sftp.listdir('.')
        for f in files:
            print(f"  - {f}")
        
        # Download and read the test file
        print("\n[+] Reading uploaded file:")
        with sftp.open('/uploaded_test.txt', 'r') as f:
            content = f.read()
            print(f"  Content: {content.decode('utf-8')}")
        
        # Clean up
        sftp.close()
        transport.close()
        
        print("\n[+] Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_sftp_connection()
    sys.exit(0 if success else 1)
