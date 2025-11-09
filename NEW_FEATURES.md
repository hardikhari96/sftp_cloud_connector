# New Features & Improvements

## 🎯 Quick Start Guide

### New API Endpoints

#### 1. Get Current User Info
```http
GET /me
Authorization: Bearer <token>
```
Returns information about the currently authenticated user.

#### 2. Delete User
```http
DELETE /users/{user_id}
Authorization: Bearer <token>
```
Deletes a user (admins cannot delete themselves).

#### 3. Update User with Role Change
```http
PATCH /users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "role": "admin",  // NEW: Can now change roles
  "password": "newpassword123",  // Must be 8+ characters
  "is_active": true,
  "home_dir": "custom/path"
}
```

---

## 🎨 UI Improvements

### User Management Table

#### New Features:
1. **Inline Role Management**
   - Change user roles directly from dropdown in table
   - Automatic confirmation prompt
   - Visual indicator for current user

2. **Delete Button**
   - Red delete button in actions column
   - Confirmation dialog before deletion
   - Cannot delete own account

3. **Search Functionality**
   - Real-time search box above user table
   - Filters by username, role, or home directory
   - No page reload needed

4. **Loading States**
   - Buttons show loading state during operations
   - Prevents double-clicks
   - Better visual feedback

5. **Enhanced Validation**
   - Password must be 8+ characters
   - Client-side validation before API call
   - Clear error messages

---

## 🔒 Security Enhancements

### Password Requirements
- **Minimum Length**: 8 characters (enforced on both frontend and backend)
- **Validation**: Checked before API submission

### Self-Modification Prevention
- Admins **cannot**:
  - Deactivate their own account
  - Delete their own account
  - Change their own role (dropdown disabled)

### Timezone Improvements
- All datetime operations now use UTC timezone
- Consistent timestamp handling across application
- Future-proof against Python deprecations

---

## 💡 Usage Examples

### Example 1: Change User Role
1. Navigate to Users section
2. Find user in table
3. Click role dropdown
4. Select new role (admin/user)
5. Confirm in dialog
6. Role updated immediately

### Example 2: Delete User
1. Navigate to Users section
2. Find user in table
3. Click red "Delete" button
4. Confirm deletion in dialog
5. User removed from system

### Example 3: Search Users
1. Navigate to Users section
2. Type in "Search Users" box
3. Table filters in real-time
4. Search by username, role, or home path

### Example 4: Reset Password
1. Navigate to Users section
2. Click "Reset Password" button
3. Enter new password (8+ chars)
4. Password updated

---

## 🎯 Admin Features Summary

### What Admins Can Do:
✅ Create users with any role
✅ Change any user's role (except own)
✅ Deactivate any user (except self)
✅ Delete any user (except self)
✅ Reset any user's password
✅ View all connections and analytics
✅ Search and filter users

### What Admins Cannot Do:
❌ Deactivate their own account
❌ Delete their own account
❌ Change their own role via UI

---

## 🔧 Configuration

### No Changes Required
All new features work with existing configuration. No environment variables need to be updated.

### Optional Enhancements
To further customize:

1. **JWT Expiration** (default: 12 hours)
   ```env
   JWT_EXP_HOURS=12
   ```

2. **Password Policy** (hardcoded to 8 chars)
   - Modify in `app/services.py` if needed

---

## 🐛 Bug Fixes

### CSS Issues
- Fixed `nth-child(every-odd)` → `nth-child(odd)` (invalid CSS syntax)
- Added proper hover effects

### JavaScript Issues
- Improved token initialization flow
- Better error recovery
- Fixed user info loading

### Backend Issues
- Fixed timezone deprecation warnings
- Improved error handling in password verification
- Added proper JWT issued-at claim

---

## 📊 Performance Improvements

### Database
- Connections endpoint now has pagination (limit parameter)
- Default limit: 100 records

### Frontend
- Real-time filtering without API calls
- Debounced search for better performance
- Efficient DOM updates

---

## 🚀 Migration Guide

### From Previous Version

**No breaking changes!** Simply deploy the updated code.

#### Steps:
1. Pull latest code
2. No database migrations needed
3. Restart services:
   ```bash
   # Restart API server
   # Restart SFTP server
   ```
4. Clear browser cache for UI updates
5. Test new features

---

## 📝 Developer Notes

### Code Organization
```
app/
├── admin_api.py      # API endpoints (added DELETE /users, GET /me)
├── services.py       # Business logic (added delete_user, role management)
├── security.py       # Auth (timezone-aware JWT)
├── schemas.py        # Data models (added role to UserUpdate)
└── static/
    ├── app.js        # UI logic (search, confirmations, loading states)
    └── styles.css    # Styling (fixes, loading states, better UX)
```

### Testing New Features
```python
# Test delete user endpoint
curl -X DELETE http://localhost:8000/users/{user_id} \
  -H "Authorization: Bearer {token}"

# Test role change
curl -X PATCH http://localhost:8000/users/{user_id} \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'

# Test get current user
curl -X GET http://localhost:8000/me \
  -H "Authorization: Bearer {token}"
```

---

## 🎓 Best Practices

### For Administrators
1. **Always use strong passwords** (8+ characters minimum)
2. **Confirm before deleting** users (cannot be undone)
3. **Use search** to quickly find users
4. **Monitor connections** regularly
5. **Review analytics** for usage patterns

### For Developers
1. **Use the `/me` endpoint** to get current user info
2. **Implement proper error handling** for all API calls
3. **Show loading states** during async operations
4. **Validate input** before sending to API
5. **Use confirmation dialogs** for destructive actions

---

## 📞 Support

### Common Issues

**Q: Cannot delete a user**
A: Check if you're trying to delete your own account (not allowed)

**Q: Role dropdown is disabled**
A: You cannot change your own role for security reasons

**Q: Password reset fails**
A: Ensure password is at least 8 characters

**Q: Search not working**
A: Clear browser cache and reload page

---

## 🎉 Summary

This update brings:
- ✨ Enhanced role management
- 🔒 Better security controls
- 🎨 Improved user interface
- 🐛 Critical bug fixes
- 📊 Better performance
- 🔍 Search functionality

Enjoy the improved SFTP Cloud Connector!
