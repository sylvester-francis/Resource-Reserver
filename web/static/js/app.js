// API Base URL - Update this to match your backend URL
const API_BASE_URL = 'http://localhost:8000';

// Global state
let currentUser = null;
let resources = [];
let reservations = [];

// DOM Elements
const appElement = document.getElementById('app');

// Initialize the application
async function init() {
    // Check if user is already logged in
    const token = localStorage.getItem('token');
    if (token) {
        try {
            // Try to get current user info
            const response = await fetch(`${API_BASE_URL}/users/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                currentUser = await response.json();
                await loadDashboard();
            } else {
                // If token is invalid, redirect to login
                localStorage.removeItem('token');
                renderLogin();
            }
        } catch (error) {
            console.error('Error initializing app:', error);
            localStorage.removeItem('token');
            renderLogin();
        }
    } else {
        renderLogin();
    }
}

// API Helper Functions
async function apiCall(endpoint, options = {}) {
    const defaultHeaders = {
        'Content-Type': 'application/json'
    };

    // Add auth token if available
    const token = localStorage.getItem('token');
    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        headers: {
            ...defaultHeaders,
            ...(options.headers || {})
        },
        ...options
    };

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
        
        // Handle 401 Unauthorized
        if (response.status === 401) {
            localStorage.removeItem('token');
            renderLogin();
            throw new Error('Session expired. Please log in again.');
        }

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Something went wrong');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        showMessage(error.message || 'An error occurred', 'error');
        throw error;
    }
}

// Authentication Functions
async function login(username, password) {
    try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);
        formData.append('grant_type', 'password');
        formData.append('scope', '');
        formData.append('client_id', '');
        formData.append('client_secret', '');

        const response = await apiCall('/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData.toString()
        });

        localStorage.setItem('token', response.access_token);
        currentUser = { username };
        
        await loadDashboard();
        showMessage('Login successful!', 'success');
        
        return true;
    } catch (error) {
        showMessage('Invalid username or password', 'error');
        return false;
    }
}

async function register(username, password) {
    try {
        await apiCall('/register', {
            method: 'POST',
            body: JSON.stringify({
                username,
                password,
                email: `${username}@example.com` // You might want to collect email separately
            })
        });
        
        showMessage('Registration successful! Please log in.', 'success');
        return true;
    } catch (error) {
        showMessage('Registration failed: ' + error.message, 'error');
        return false;
    }
}

function logout() {
    localStorage.removeItem('token');
    currentUser = null;
    renderLogin();
}

// Resource Management
async function loadResources() {
    try {
        resources = await apiCall('/resources/');
        return resources;
    } catch (error) {
        console.error('Error loading resources:', error);
        return [];
    }
}

async function searchResources(params = {}) {
    try {
        const queryParams = new URLSearchParams();
        
        // Add non-null parameters to query
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                queryParams.append(key, value);
            }
        });
        
        const queryString = queryParams.toString();
        const url = `/resources/search${queryString ? `?${queryString}` : ''}`;
        
        resources = await apiCall(url);
        return resources;
    } catch (error) {
        console.error('Error searching resources:', error);
        return [];
    }
}

// Reservation Management
async function createReservation(resourceId, startTime, endTime, notes = '') {
    try {
        const reservation = await apiCall('/reservations/', {
            method: 'POST',
            body: JSON.stringify({
                resource_id: resourceId,
                start_time: startTime.toISOString(),
                end_time: endTime.toISOString(),
                notes
            })
        });
        
        showMessage('Reservation created successfully!', 'success');
        return reservation;
    } catch (error) {
        showMessage('Failed to create reservation: ' + error.message, 'error');
        throw error;
    }
}

async function getMyReservations(includeCancelled = false) {
    try {
        reservations = await apiCall(`/reservations/me?include_cancelled=${includeCancelled}`);
        return reservations;
    } catch (error) {
        console.error('Error loading reservations:', error);
        return [];
    }
}

async function cancelReservation(reservationId, reason = '') {
    try {
        await apiCall(`/reservations/${reservationId}/cancel`, {
            method: 'POST',
            body: JSON.stringify({ reason })
        });
        
        showMessage('Reservation cancelled successfully', 'success');
        return true;
    } catch (error) {
        showMessage('Failed to cancel reservation: ' + error.message, 'error');
        return false;
    }
}

// UI Rendering Functions
function renderLogin() {
    appElement.innerHTML = `
        <div class="container">
            <div class="card" style="max-width: 400px; margin: 2rem auto;">
                <div class="card-header">
                    <h2>Resource Reservation System</h2>
                </div>
                <div class="card-body">
                    <div class="tabs">
                        <button class="tab-btn active" data-tab="login">Login</button>
                        <button class="tab-btn" data-tab="register">Register</button>
                    </div>
                    
                    <form id="loginForm" class="auth-form">
                        <div class="form-group">
                            <label for="username">Username</label>
                            <input type="text" id="username" name="username" class="form-control" required>
                        </div>
                        <div class="form-group">
                            <label for="password">Password</label>
                            <input type="password" id="password" name="password" class="form-control" required>
                        </div>
                        <button type="submit" class="btn btn-primary">Sign In</button>
                    </form>
                    
                    <form id="registerForm" class="auth-form hidden">
                        <div class="form-group">
                            <label for="regUsername">Username</label>
                            <input type="text" id="regUsername" name="username" class="form-control" required>
                        </div>
                        <div class="form-group">
                            <label for="regPassword">Password</label>
                            <input type="password" id="regPassword" name="password" class="form-control" required>
                        </div>
                        <div class="form-group">
                            <label for="confirmPassword">Confirm Password</label>
                            <input type="password" id="confirmPassword" name="confirmPassword" class="form-control" required>
                        </div>
                        <button type="submit" class="btn btn-success">Register</button>
                    </form>
                </div>
            </div>
        </div>
    `;
    
    // Add event listeners
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            document.querySelectorAll('.auth-form').forEach(form => form.classList.add('hidden'));
            document.getElementById(`${e.target.dataset.tab}Form`).classList.remove('hidden');
        });
    });
    
    // Login form submission
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        await login(username, password);
    });
    
    // Register form submission
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('regUsername').value;
        const password = document.getElementById('regPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        if (password !== confirmPassword) {
            showMessage('Passwords do not match', 'error');
            return;
        }
        
        const success = await register(username, password);
        if (success) {
            // Switch to login tab after successful registration
            document.querySelector('.tab-btn[data-tab="login"]').click();
        }
    });
}

async function loadDashboard() {
    try {
        // Load resources and reservations in parallel
        const [resourcesData, reservationsData] = await Promise.all([
            loadResources(),
            getMyReservations()
        ]);
        
        resources = resourcesData;
        reservations = reservationsData;
        
        renderDashboard();
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showMessage('Failed to load dashboard data', 'error');
    }
}

function renderDashboard() {
    appElement.innerHTML = `
        <div class="container">
            <header class="header">
                <div>
                    <h1>Resource Reservation System</h1>
                    <div class="user-info">
                        Welcome, ${currentUser.username} | 
                        <a href="#" id="logoutBtn" style="color: #4f46e5; margin-left: 4px;">Logout</a>
                    </div>
                </div>
                <div class="header-actions">
                    <button class="btn btn-primary" id="createReservationBtn">
                        <span class="material-icons">add</span>
                        New Reservation
                    </button>
                </div>
            </header>
            
            <div class="tabs">
                <button class="tab-btn active" data-tab="resources">Resources</button>
                <button class="tab-btn" data-tab="myReservations">My Reservations</button>
                <button class="tab-btn" data-tab="upcoming">Upcoming</button>
                <button class="tab-btn" data-tab="analytics">Analytics</button>
            </div>
            
            <div id="tabContent">
                <!-- Tab content will be loaded here -->
            </div>
        </div>
        
        <!-- Modals will be appended here -->
    `;
    
    // Add event listeners
    document.getElementById('logoutBtn').addEventListener('click', (e) => {
        e.preventDefault();
        logout();
    });
    
    document.getElementById('createReservationBtn').addEventListener('click', () => {
        showCreateReservationModal();
    });
    
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            switch(btn.dataset.tab) {
                case 'resources':
                    renderResourcesTab();
                    break;
                case 'myReservations':
                    renderReservationsTab();
                    break;
                case 'upcoming':
                    renderUpcomingTab();
                    break;
                case 'analytics':
                    renderAnalyticsTab();
                    break;
            }
        });
    });
    
    // Load initial tab
    document.querySelector('.tab-btn.active').click();
}

// UI Utility Functions
function showMessage(message, type = 'info') {
    // Remove any existing messages
    const existingMessage = document.getElementById('flashMessage');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.id = 'flashMessage';
    messageDiv.className = `flash-message flash-${type}`;
    messageDiv.textContent = message;
    
    document.body.appendChild(messageDiv);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        messageDiv.remove();
    }, 5000);
}

function showModal(modalId, content) {
    // Close any open modals
    closeAllModals();
    
    const modal = document.createElement('div');
    modal.id = modalId;
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">${content.title || 'Modal'}</h2>
                <button class="close-btn">&times;</button>
            </div>
            <div class="modal-body">
                ${content.body || ''}
            </div>
            ${content.footer ? `
                <div class="modal-footer">
                    ${content.footer}
                </div>
            ` : ''}
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Add close button event
    modal.querySelector('.close-btn').addEventListener('click', () => {
        modal.remove();
    });
    
    return modal;
}

function closeAllModals() {
    document.querySelectorAll('.modal').forEach(modal => modal.remove());
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', init);
