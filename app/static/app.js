const loginSection = document.getElementById("login-section");
const dashboardSection = document.getElementById("dashboard");
const statusEl = document.getElementById("status");
const logoutBtn = document.getElementById("logout-btn");
const loginForm = document.getElementById("login-form");
const createUserForm = document.getElementById("create-user-form");
const usersTableBody = document.querySelector("#users-table tbody");
const connectionsTableBody = document.querySelector("#connections-table tbody");
const analyticsTableBody = document.querySelector("#analytics-table tbody");
const summaryEl = document.getElementById("summary");
const toast = document.getElementById("toast");
const connectionsFilter = document.getElementById("connections-filter");
const refreshConnectionsBtn = document.getElementById("refresh-connections");
const userSearchInput = document.getElementById("user-search");

let allUsers = [];

// Tab switching functionality
function switchTab(tabName) {
    // Update tab buttons
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(btn => {
        if (btn.dataset.tab === tabName) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
    
    // Update tab contents
    const tabContents = document.querySelectorAll(".tab-content");
    tabContents.forEach(content => {
        if (content.id === `${tabName}-tab`) {
            content.classList.add("active");
        } else {
            content.classList.remove("active");
        }
    });
}

// Initialize tab handlers
function initializeTabs() {
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            switchTab(btn.dataset.tab);
        });
    });
}

class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}

let token = localStorage.getItem("sftp_token") || null;
let currentUser = localStorage.getItem("sftp_username") || "";

function showToast(message, type = "info") {
    toast.textContent = message;
    toast.classList.remove("hidden", "show", "error", "success");
    if (type !== "info") {
        toast.classList.add(type);
    }
    requestAnimationFrame(() => {
        toast.classList.add("show");
    });
    setTimeout(() => {
        toast.classList.remove("show");
        toast.classList.add("hidden");
    }, 3200);
}

function setAuthState(isAuthenticated, username = "") {
    if (isAuthenticated) {
        currentUser = username;
        if (username) {
            localStorage.setItem("sftp_username", username);
        }
        statusEl.textContent = `Logged in as ${username}`;
        loginSection.classList.add("hidden");
        dashboardSection.classList.remove("hidden");
        logoutBtn.classList.remove("hidden");
    } else {
        currentUser = "";
        statusEl.textContent = "Not authenticated";
        loginSection.classList.remove("hidden");
        dashboardSection.classList.add("hidden");
        logoutBtn.classList.add("hidden");
        localStorage.removeItem("sftp_username");
    }
}

async function apiFetch(path, options = {}) {
    const headers = options.headers ? { ...options.headers } : {};
    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }
    if (options.body && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }
    const response = await fetch(path, { ...options, headers });
    if (response.status === 401) {
        localStorage.removeItem("sftp_token");
        token = null;
        setAuthState(false);
        throw new ApiError("Unauthorized", 401);
    }
    if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new ApiError(detail.detail || response.statusText || "Request failed", response.status);
    }
    if (response.status === 204) {
        return null;
    }
    return response.json();
}

function formatDate(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString();
}

function formatBytes(value) {
    if (!value && value !== 0) return "-";
    
    const bytes = Number(value);
    if (isNaN(bytes)) return value;
    
    if (bytes === 0) return "0 Bytes";
    
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function renderUsers(users) {
    usersTableBody.innerHTML = "";
    if (!users.length) {
        usersTableBody.innerHTML = '<tr><td colspan="7">No users found</td></tr>';
        return;
    }
    for (const user of users) {
        const tr = document.createElement("tr");
        const isCurrentUser = user.username === currentUser;
        tr.innerHTML = `
            <td>${user.username}${isCurrentUser ? ' <strong>(You)</strong>' : ''}</td>
            <td>
                <select data-action="change-role" data-id="${user._id}" data-current="${user.role}" ${isCurrentUser ? 'disabled' : ''}>
                    <option value="user" ${user.role === 'user' ? 'selected' : ''}>User</option>
                    <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Admin</option>
                </select>
            </td>
            <td>${user.home_dir}</td>
            <td>${user.is_active ? "Active" : "Inactive"}</td>
            <td>${formatDate(user.created_at)}</td>
            <td>${formatDate(user.last_login)}</td>
            <td class="actions">
                <button data-action="toggle" data-id="${user._id}" data-active="${user.is_active}" ${isCurrentUser ? 'disabled' : ''}>
                    ${user.is_active ? "Deactivate" : "Activate"}
                </button>
                <button data-action="password" data-id="${user._id}">Reset Password</button>
                <button data-action="delete" data-id="${user._id}" ${isCurrentUser ? 'disabled' : ''}>Delete</button>
            </td>
        `;
        usersTableBody.appendChild(tr);
    }
}

function renderConnections(connections) {
    connectionsTableBody.innerHTML = "";
    if (!connections.length) {
        connectionsTableBody.innerHTML = '<tr><td colspan="8">No connection records</td></tr>';
        return;
    }
    for (const conn of connections) {
        const status = conn.active ? "Active" : "Closed";
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${conn.username}</td>
            <td>${conn.client_id}</td>
            <td>${conn.remote_ip}</td>
            <td>${formatDate(conn.started_at)}</td>
            <td>${formatDate(conn.ended_at)}</td>
            <td>${formatBytes(conn.bytes_uploaded)}</td>
            <td>${formatBytes(conn.bytes_downloaded)}</td>
            <td>${status}</td>
        `;
        connectionsTableBody.appendChild(tr);
    }
}

function renderAnalytics(summary) {
    // Render stats cards
    summaryEl.innerHTML = `
        <div class="stat-card connection-card">
            <div class="stat-label">Total Connections</div>
            <div class="stat-value">${summary.total_connections}</div>
        </div>
        <div class="stat-card connection-card">
            <div class="stat-label">Active Now</div>
            <div class="stat-value">${summary.active_connections}</div>
        </div>
        <div class="stat-card upload-card">
            <div class="stat-label">Total Upload</div>
            <div class="stat-value">${formatBytes(summary.total_upload)}</div>
        </div>
        <div class="stat-card download-card">
            <div class="stat-label">Total Download</div>
            <div class="stat-value">${formatBytes(summary.total_download)}</div>
        </div>
    `;
    
    analyticsTableBody.innerHTML = "";
    if (!summary.transfers.length) {
        analyticsTableBody.innerHTML = '<tr><td colspan="4">No analytics yet</td></tr>';
        return;
    }
    for (const item of summary.transfers) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${item.username}</strong></td>
            <td>${formatBytes(item.total_upload)}</td>
            <td>${formatBytes(item.total_download)}</td>
            <td>${item.transfer_count}</td>
        `;
        analyticsTableBody.appendChild(tr);
    }
}

async function loadUsers() {
    try {
        const data = await apiFetch("/users");
        allUsers = data;
        renderUsers(data);
    } catch (error) {
        if (error instanceof ApiError && error.status === 403) {
            // Hide create user tab if not admin
            const createUserTab = document.querySelector('[data-tab="create-user"]');
            if (createUserTab) {
                createUserTab.style.display = 'none';
            }
            return;
        }
        showToast(error.message, "error");
    }
}

function filterUsers(searchTerm) {
    const term = searchTerm.toLowerCase().trim();
    if (!term) {
        return allUsers;
    }
    return allUsers.filter(user => 
        user.username.toLowerCase().includes(term) || 
        user.role.toLowerCase().includes(term) ||
        user.home_dir.toLowerCase().includes(term)
    );
}

function setLoading(element, isLoading) {
    if (isLoading) {
        element.classList.add("loading");
        element.disabled = true;
    } else {
        element.classList.remove("loading");
        element.disabled = false;
    }
}

async function loadConnections() {
    try {
        const userId = connectionsFilter.value.trim();
        const url = userId ? `/connections?user_id=${encodeURIComponent(userId)}` : "/connections";
        const data = await apiFetch(url);
        renderConnections(data);
    } catch (error) {
        showToast(error.message, "error");
    }
}

async function loadAnalytics() {
    try {
        const data = await apiFetch("/analytics");
        renderAnalytics(data);
    } catch (error) {
        showToast(error.message, "error");
    }
}

async function loadDashboard() {
    await Promise.all([loadUsers(), loadConnections(), loadAnalytics()]);
}

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value;
    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        if (!response.ok) {
            const detail = await response.json().catch(() => ({}));
            throw new Error(detail.detail || "Login failed");
        }
        const data = await response.json();
        token = data.access_token;
        localStorage.setItem("sftp_token", token);
        setAuthState(true, username);
        showToast("Logged in successfully", "success");
        await loadDashboard();
    } catch (error) {
        showToast(error.message, "error");
    }
});

logoutBtn.addEventListener("click", () => {
    token = null;
    localStorage.removeItem("sftp_token");
    setAuthState(false);
});

createUserForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const password = document.getElementById("new-password").value;
    
    if (password.length < 8) {
        showToast("Password must be at least 8 characters", "error");
        return;
    }
    
    const payload = {
        username: document.getElementById("new-username").value.trim(),
        password: password,
        role: document.getElementById("new-role").value,
        home_dir: document.getElementById("new-home").value.trim() || null,
        is_active: document.getElementById("new-active").checked,
    };
    
    setLoading(submitBtn, true);
    try {
        await apiFetch("/users", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        createUserForm.reset();
        document.getElementById("new-active").checked = true;
        showToast("User created successfully", "success");
        await loadUsers();
    } catch (error) {
        showToast(error.message, "error");
    } finally {
        setLoading(submitBtn, false);
    }
});

usersTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const { action, id } = button.dataset;
    if (!id || !action) return;

    if (action === "toggle") {
        const isActive = button.dataset.active === "true";
        const confirmMsg = `Are you sure you want to ${isActive ? "deactivate" : "activate"} this user?`;
        if (!confirm(confirmMsg)) return;
        
        setLoading(button, true);
        try {
            await apiFetch(`/users/${id}`, {
                method: "PATCH",
                body: JSON.stringify({ is_active: !isActive }),
            });
            showToast(`User ${isActive ? "deactivated" : "activated"}`, "success");
            await loadUsers();
        } catch (error) {
            showToast(error.message, "error");
        } finally {
            setLoading(button, false);
        }
    }

    if (action === "password") {
        const newPassword = prompt("Enter new password (min 8 characters):");
        if (!newPassword) return;
        if (newPassword.length < 8) {
            showToast("Password must be at least 8 characters", "error");
            return;
        }
        
        setLoading(button, true);
        try {
            await apiFetch(`/users/${id}`, {
                method: "PATCH",
                body: JSON.stringify({ password: newPassword }),
            });
            showToast("Password reset successfully", "success");
        } catch (error) {
            showToast(error.message, "error");
        } finally {
            setLoading(button, false);
        }
    }

    if (action === "delete") {
        const confirmMsg = "Are you sure you want to DELETE this user? This action cannot be undone.";
        if (!confirm(confirmMsg)) return;
        
        setLoading(button, true);
        try {
            await apiFetch(`/users/${id}`, {
                method: "DELETE",
            });
            showToast("User deleted successfully", "success");
            await loadUsers();
        } catch (error) {
            showToast(error.message, "error");
        } finally {
            setLoading(button, false);
        }
    }
});

usersTableBody.addEventListener("change", async (event) => {
    const select = event.target.closest("select[data-action='change-role']");
    if (!select) return;
    
    const { id, current } = select.dataset;
    const newRole = select.value;
    
    if (newRole === current) return;
    
    const confirmMsg = `Are you sure you want to change this user's role to ${newRole}?`;
    if (!confirm(confirmMsg)) {
        select.value = current;
        return;
    }
    
    setLoading(select, true);
    try {
        await apiFetch(`/users/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ role: newRole }),
        });
        showToast("Role updated successfully", "success");
        await loadUsers();
    } catch (error) {
        showToast(error.message, "error");
        select.value = current;
    } finally {
        setLoading(select, false);
    }
});

refreshConnectionsBtn.addEventListener("click", loadConnections);

if (userSearchInput) {
    userSearchInput.addEventListener("input", (event) => {
        const filtered = filterUsers(event.target.value);
        renderUsers(filtered);
    });
}

document.addEventListener("click", (event) => {
    const button = event.target.closest(".toggle-password, .toggle-password-inline");
    if (!button) {
        return;
    }
    const targetId = button.dataset.target;
    if (!targetId) {
        return;
    }
    const input = document.getElementById(targetId);
    if (!input) {
        return;
    }
    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";
    
    // Update button text for regular toggle buttons
    if (button.classList.contains("toggle-password")) {
        button.textContent = isHidden ? "Hide" : "Show";
    } else if (button.classList.contains("toggle-password-inline")) {
        // For inline buttons, just use emoji
        button.textContent = isHidden ? "🔒" : "👁️";
    }
    
    if (input.hasAttribute("readonly")) {
        input.blur();
    }
});

async function init() {
    // Initialize tab handlers
    initializeTabs();
    
    if (token) {
        try {
            const me = await apiFetch("/me");
            currentUser = me.username;
            setAuthState(true, currentUser);
            await loadDashboard();
        } catch (error) {
            console.warn("Stored token invalid", error);
            localStorage.removeItem("sftp_token");
            token = null;
            setAuthState(false);
        }
    }
}

init();
