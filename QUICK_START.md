# Quick Start Guide - SFTP Cloud Connector

## 🚀 Getting Started

### 1. Activate Virtual Environment
```powershell
.\sftp_env\Scripts\Activate.ps1
```

### 2. Start the Server
```powershell
python sftp_server.py
```

The application will start on:
- **Admin Panel:** http://localhost:8000
- **SFTP Server:** localhost:2222

---

## 🔑 Default Credentials

**Admin User:**
- Username: `admin`
- Password: `admin123` (change immediately!)

**Test User:**
- Username: `admin1`
- Password: `password` (if exists)

---

## 📖 Features Overview

### 👥 Users Tab
- View all SFTP users
- Search users by username, role, or home directory
- Change user roles (admin/user)
- Toggle user active/inactive status
- Reset user passwords
- Delete users (except yourself)

### 🔌 Connections Tab
- View all SFTP connection history
- Filter connections by user ID
- See active and closed connections
- Monitor upload/download data in GB/MB/KB

### 📊 Analytics Tab
- **Admin:** See all users' statistics
- **User:** See only your own statistics
- View total upload/download per user
- Monitor connection counts

### ➕ Create User Tab
- Create new SFTP users
- Set username and password (min 8 chars)
- Assign role (admin/user)
- Configure home directory
- Set initial active status

---

## 🎨 UI Features

### Tab Navigation
- Click tabs to switch between sections
- Active tab has gradient underline
- Smooth animations on tab switch

### Status Badges
- **Green (Active):** User/Connection is active
- **Gray (Inactive):** User/Connection is inactive

### File Sizes
- Automatically formatted (Bytes → KB → MB → GB → TB)
- Example: `1536` displays as `1.5 KB`

### Loading States
- Skeleton animations while data loads
- Error messages if loading fails

### Info Banner
- Shows SFTP connection details
- Host, Port, Username displayed
- Hover effects for better visibility

---

## 🔒 Security Notes

### Role-Based Access
- **Admin:** Full access to all features
- **User:** Limited to own data and analytics

### Self-Protection
- Admins cannot deactivate themselves
- Admins cannot delete their own account
- Prevents accidental lockout

### Password Security
- Minimum 8 characters required
- Hashed with bcrypt
- Salted for extra security

---

## 📱 Mobile Usage

### Responsive Design
- Works on phones, tablets, and desktops
- Touch-friendly buttons and inputs
- Horizontal scroll for tables on small screens
- Adaptive layouts for different screen sizes

### Tips
- Swipe horizontally to see all table columns
- Tap tabs to navigate (no hover needed)
- Forms stack vertically on mobile

---

## 🛠️ Common Tasks

### Create a New User
1. Go to **Create User** tab
2. Fill in username and password (min 8 chars)
3. Select role (admin/user)
4. Optionally customize home directory
5. Click **Create User**

### Change User Role
1. Go to **Users** tab
2. Find the user in the table
3. Use dropdown to select new role
4. Changes save automatically

### Reset User Password
1. Go to **Users** tab
2. Click **Reset Password** for the user
3. Enter new password (min 8 chars)
4. Click **Reset Password** in modal

### Delete a User
1. Go to **Users** tab
2. Click **Delete** button for the user
3. Confirm the action
4. User is permanently removed

### View Connection History
1. Go to **Connections** tab
2. Optionally filter by user ID
3. See all connection records with timestamps
4. Upload/download data shown in readable format

### Check Analytics
1. Go to **Analytics** tab
2. **Admin:** See all users' stats
3. **User:** See only your stats
4. View total data transferred and connection counts

---

## 🐛 Troubleshooting

### Can't Login
- Check username and password
- Ensure SFTP server is running
- Clear browser cache and try again
- Check browser console for errors

### Tabs Not Switching
- Refresh the page
- Clear browser cache
- Check browser console for JavaScript errors
- Ensure modern browser (Chrome, Edge, Firefox)

### Data Not Loading
- Check internet connection
- Ensure backend server is running
- Check MongoDB is accessible
- Look for error messages in console

### Mobile Layout Issues
- Try rotating device (portrait/landscape)
- Zoom out if content is too large
- Scroll horizontally for wide tables
- Update to latest browser version

---

## 💡 Tips & Tricks

### Search Users
- Type in the search box above the users table
- Searches username, role, and home directory
- Updates in real-time as you type

### Keyboard Shortcuts
- **Tab:** Navigate between form fields
- **Enter:** Submit forms
- **Esc:** Close modals (if implemented)

### Performance
- Loading skeletons show while data fetches
- Data is cached to reduce server requests
- Smooth animations for better UX

---

## 📞 Support

### Logs Location
- Check terminal/console for backend errors
- Browser Developer Tools → Console for frontend errors
- MongoDB logs if database issues

### Common Error Messages
- **401 Unauthorized:** Token expired, login again
- **403 Forbidden:** Insufficient permissions
- **404 Not Found:** Resource doesn't exist
- **500 Server Error:** Backend issue, check logs

---

## 🔄 Updates & Maintenance

### Regular Tasks
- Monitor disk space in `sftp_root/`
- Review connection logs periodically
- Update passwords regularly
- Backup MongoDB database

### Security Best Practices
- Change default admin password immediately
- Use strong passwords (8+ chars, mixed case, numbers)
- Regularly audit user access
- Monitor for unusual connection patterns
- Keep dependencies updated

---

## 📄 File Structure

```
sftp_root/
├── admin/          # Admin user's directory
├── admin1/         # admin1 user's directory
├── uploads/        # Shared uploads folder
└── [username]/     # Each user's home directory
```

---

Enjoy using your SFTP Cloud Connector! 🎉
