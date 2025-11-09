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
const usersCard = document.getElementById("users-card");
const createUserCard = document.getElementById("create-user-card");

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
    return value.toLocaleString();
}

function renderUsers(users) {
    usersTableBody.innerHTML = "";
    if (!users.length) {
        usersTableBody.innerHTML = '<tr><td colspan="7">No users found</td></tr>';
        return;
    }
    for (const user of users) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${user.username}</td>
            <td>${user.role}</td>
            <td>${user.home_dir}</td>
            <td>${user.is_active ? "Active" : "Inactive"}</td>
            <td>${formatDate(user.created_at)}</td>
            <td>${formatDate(user.last_login)}</td>
            <td class="actions">
                <button data-action="toggle" data-id="${user._id}" data-active="${user.is_active}">
                    ${user.is_active ? "Deactivate" : "Activate"}
                </button>
                <button data-action="password" data-id="${user._id}">Reset Password</button>
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
    summaryEl.textContent = `Total Connections: ${summary.total_connections} | Active: ${summary.active_connections} | Upload: ${formatBytes(summary.total_upload)} | Download: ${formatBytes(summary.total_download)}`;
    analyticsTableBody.innerHTML = "";
    if (!summary.transfers.length) {
        analyticsTableBody.innerHTML = '<tr><td colspan="4">No analytics yet</td></tr>';
        return;
    }
    for (const item of summary.transfers) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${item.username}</td>
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
        usersCard?.classList.remove("hidden");
        createUserCard?.classList.remove("hidden");
        renderUsers(data);
    } catch (error) {
        if (error instanceof ApiError && error.status === 403) {
            usersCard?.classList.add("hidden");
            createUserCard?.classList.add("hidden");
            return;
        }
        showToast(error.message, "error");
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
    const payload = {
        username: document.getElementById("new-username").value.trim(),
        password: document.getElementById("new-password").value,
        role: document.getElementById("new-role").value,
        home_dir: document.getElementById("new-home").value.trim() || null,
        is_active: document.getElementById("new-active").checked,
    };
    try {
        await apiFetch("/users", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        createUserForm.reset();
        document.getElementById("new-active").checked = true;
        showToast("User created", "success");
        await loadUsers();
    } catch (error) {
        showToast(error.message, "error");
    }
});

usersTableBody.addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const { action, id } = button.dataset;
    if (!id || !action) return;

    if (action === "toggle") {
        const isActive = button.dataset.active === "true";
        try {
            await apiFetch(`/users/${id}`, {
                method: "PATCH",
                body: JSON.stringify({ is_active: !isActive }),
            });
            showToast(`User ${isActive ? "deactivated" : "activated"}`, "success");
            await loadUsers();
        } catch (error) {
            showToast(error.message, "error");
        }
    }

    if (action === "password") {
        const newPassword = prompt("Enter new password");
        if (!newPassword) return;
        try {
            await apiFetch(`/users/${id}`, {
                method: "PATCH",
                body: JSON.stringify({ password: newPassword }),
            });
            showToast("Password reset", "success");
        } catch (error) {
            showToast(error.message, "error");
        }
    }
});

refreshConnectionsBtn.addEventListener("click", loadConnections);

document.addEventListener("click", (event) => {
    const button = event.target.closest(".toggle-password");
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
    button.textContent = isHidden ? "Hide" : "Show";
    if (input.hasAttribute("readonly")) {
        input.blur();
    }
});

async function init() {
    if (token) {
        try {
            const payload = await apiFetch("/me/connections");
            setAuthState(true, currentUser || "admin");
            renderConnections(payload);
            await loadUsers();
            await loadAnalytics();
        } catch (error) {
            console.warn("Stored token invalid", error);
            localStorage.removeItem("sftp_token");
            token = null;
            setAuthState(false);
        }
    }
}

init();
