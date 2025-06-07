// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// Global state
let currentUser = JSON.parse(localStorage.getItem('user')) || null;
let authToken = localStorage.getItem('auth_token') || null;
let currentView = 'login';
let activeTab = 'resources';
let loading = false;

// Data storage
let resources = [];
let reservations = [];
let filteredResources = [];
let searchQuery = '';
let currentFilter = 'all'; // 'all', 'available', 'unavailable'
let viewMode = 'grid'; // 'grid', 'list'

// Initialize app
function init() {
    if (authToken && currentUser) {
        currentView = 'dashboard';
        loadDashboard();
    } else {
        currentView = 'login';
        renderLogin();
    }
}

// API Helper Functions
async function apiCall(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(authToken && { 'Authorization': `Bearer ${authToken}` }),
        ...options.headers
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'API request failed');
    }

    return await response.json();
}

async function login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/token`, {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        throw new Error('Invalid credentials');
    }

    const data = await response.json();
    authToken = data.access_token;
    currentUser = { username };

    localStorage.setItem('auth_token', authToken);
    localStorage.setItem('user', JSON.stringify(currentUser));

    return data;
}

async function register(username, password) {
    const response = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(error || 'Registration failed');
    }

    return await response.json();
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    currentView = 'login';
    renderLogin();
}

// Data Loading Functions
async function loadResources() {
    try {
        resources = await apiCall('/resources');
        filterResources();
    } catch (error) {
        console.error('Failed to load resources:', error);
    }
}

async function loadReservations() {
    try {
        reservations = await apiCall('/reservations/my');
    } catch (error) {
        console.error('Failed to load reservations:', error);
    }
}

function filterResources() {
    let filtered = resources;

    // Apply status filter
    if (currentFilter === 'available') {
        filtered = filtered.filter(r => r.available);
    } else if (currentFilter === 'unavailable') {
        filtered = filtered.filter(r => !r.available);
    }

    // Apply search query
    if (searchQuery) {
        filtered = filtered.filter(resource =>
            resource.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            resource.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
        );
    }

    filteredResources = filtered;
}

async function loadDashboard() {
    await Promise.all([loadResources(), loadReservations()]);
    renderDashboard();
}

// Render Functions
function renderLogin() {
    const app = document.getElementById('app');
    app.innerHTML = `
                <div class="login-container">
                    <div class="login-card">
                        <div class="login-header">
                            <h1>Resource Reservation System</h1>
                            <p>Please sign in to your account</p>
                        </div>
                        
                        <div class="auth-tabs">
                            <button class="auth-tab active" onclick="switchAuthTab(event, 'login')">Sign In</button>
                            <button class="auth-tab" onclick="switchAuthTab(event, 'register')">Register</button>
                        </div>

                        <form id="authForm" onsubmit="handleAuth(event)">
                            <div class="form-group">
                                <label class="form-label">Username</label>
                                <input type="text" class="form-input" name="username" required>
                            </div>
                            
                            <div class="form-group">
                                <label class="form-label">Password</label>
                                <input type="password" class="form-input" name="password" required>
                            </div>
                            
                            <div class="form-group" id="confirmPasswordGroup" style="display: none;">
                                <label class="form-label">Confirm Password</label>
                                <input type="password" class="form-input" name="confirmPassword">
                            </div>
                            
                            <div id="authError" class="alert alert-error hidden"></div>
                            
                            <button type="submit" class="btn btn-primary" style="width: 100%;" id="authSubmit">
                                Sign In
                            </button>
                        </form>
                    </div>
                </div>
            `;
}

function renderDashboard() {
    const stats = calculateStats();
    const upcomingReservations = getUpcomingReservations();

    const app = document.getElementById('app');
    app.innerHTML = `
                <div class="container">
                    <div class="header">
                        <div>
                            <h1>Resource Reservation System</h1>
                            <div class="user-info">Welcome back, ${currentUser.username}</div>
                        </div>
                        <button class="btn btn-secondary" onclick="logout()">Sign Out</button>
                    </div>

                    <div class="stats-grid">
                        <div class="stat-card">
                            <span class="stat-number">${stats.totalResources}</span>
                            <div class="stat-label">Total Resources</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-number">${stats.availableResources}</span>
                            <div class="stat-label">Available Now</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-number">${stats.activeReservations}</span>
                            <div class="stat-label">Active Bookings</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-number">${stats.upcomingReservations}</span>
                            <div class="stat-label">Upcoming</div>
                        </div>
                    </div>

                    <div class="nav-tabs">
                        <button class="nav-tab ${activeTab === 'resources' ? 'active' : ''}" onclick="switchTab('resources')">
                            Resources
                        </button>
                        <button class="nav-tab ${activeTab === 'reservations' ? 'active' : ''}" onclick="switchTab('reservations')">
                            My Reservations
                        </button>
                        <button class="nav-tab ${activeTab === 'upcoming' ? 'active' : ''}" onclick="switchTab('upcoming')">
                            Upcoming
                        </button>
                    </div>

                    <div class="card">
                        <div id="tabContent">
                            ${renderTabContent()}
                        </div>
                    </div>
                </div>
            `;
}

function renderTabContent() {
    switch (activeTab) {
        case 'resources':
            return renderResourcesTab();
        case 'reservations':
            return renderReservationsTab();
        case 'upcoming':
            return renderUpcomingTab();
        default:
            return '';
    }
}

function renderResourcesTab() {
    return `
                <div class="resources-header">
                    <div class="search-and-filters">
                        <div class="search-row">
                            <div class="search-container">
                                <input type="text" class="form-input search-input" placeholder="Search resources by name or tags..." 
                                       value="${searchQuery}" onkeyup="handleSearch(this.value)">
                                <span class="search-icon">🔍</span>
                            </div>
                            <div class="action-buttons">
                                <button class="btn btn-secondary" onclick="showAdvancedSearchModal()">
                                    🔍 Advanced Search
                                </button>
                                <button class="btn btn-secondary" onclick="loadResources(); renderDashboard();">
                                    🔄 Refresh
                                </button>
                                <button class="btn btn-success" onclick="showCreateResourceModal()">
                                    ➕ Add Resource
                                </button>
                                <button class="btn btn-primary" onclick="showUploadCSVModal()">
                                    📤 Upload CSV
                                </button>
                            </div>
                        </div>
                        
                        <div class="filter-pills">
                            <span style="font-weight: 600; color: #64748b; font-size: 14px;">Filter:</span>
                            <div class="filter-pill ${currentFilter === 'all' ? 'active' : ''}" onclick="handleFilterChange('all')">
                                All Resources
                            </div>
                            <div class="filter-pill ${currentFilter === 'available' ? 'active' : ''}" onclick="handleFilterChange('available')">
                                🟢 Available
                            </div>
                            <div class="filter-pill ${currentFilter === 'unavailable' ? 'active' : ''}" onclick="handleFilterChange('unavailable')">
                                🔴 Unavailable
                            </div>
                        </div>
                    </div>
                </div>

                <div class="results-summary">
                    <div class="results-count">
                        Showing ${filteredResources.length} of ${resources.length} resources
                    </div>
                    <div class="view-toggle">
                        <button class="view-btn ${viewMode === 'grid' ? 'active' : ''}" onclick="handleViewModeChange('grid')">
                            ⊞ Grid
                        </button>
                        <button class="view-btn ${viewMode === 'list' ? 'active' : ''}" onclick="handleViewModeChange('list')">
                            ☰ List
                        </button>
                    </div>
                </div>

                ${filteredResources.length === 0 ? `
                    <div class="empty-state">
                        <div class="empty-state-icon">📦</div>
                        <h3>No resources found</h3>
                        <p>${searchQuery || currentFilter !== 'all' ? 'Try adjusting your search or filters' : 'Get started by adding your first resource'}</p>
                        <button class="btn btn-primary" onclick="showCreateResourceModal()">
                            ➕ Add Your First Resource
                        </button>
                    </div>
                ` : `
                    <div class="resources-grid ${viewMode === 'grid' ? 'active' : ''}" style="${viewMode === 'grid' ? 'display: grid' : 'display: none'}">
                        ${filteredResources.map(resource => `
                            <div class="resource-card">
                                <div class="resource-header">
                                    <h3 class="resource-title">${resource.name}</h3>
                                    <span class="status-badge ${resource.available ? 'status-available' : 'status-unavailable'}">
                                        ${resource.available ? '🟢 Available' : '🔴 Unavailable'}
                                    </span>
                                </div>
                                
                                <div class="resource-meta">
                                    <div class="resource-id">${resource.id.toString().padStart(3, '0')}</div>
                                </div>
                                
                                ${resource.tags.length > 0 ? `
                                    <div class="tags">
                                        ${resource.tags.map(tag => `<span class="tag">#${tag}</span>`).join('')}
                                    </div>
                                ` : '<div class="tags"><span class="tag" style="opacity: 0.5;">No tags</span></div>'}
                                
                                <div class="resource-actions">
                                    <button class="btn-reserve" 
                                            ${!resource.available ? 'disabled' : ''} 
                                            onclick="showCreateReservationModal(${resource.id})">
                                        ${resource.available ? '📅 Reserve Now' : '🚫 Unavailable'}
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>

                    <div class="resources-list ${viewMode === 'list' ? 'active' : ''}" style="${viewMode === 'list' ? 'display: flex' : 'display: none'}">
                        ${filteredResources.map(resource => `
                            <div class="resource-list-item">
                                <div class="resource-list-avatar">
                                    ${resource.name.charAt(0).toUpperCase()}
                                </div>
                                
                                <div class="resource-list-content">
                                    <div class="resource-list-header">
                                        <h3 class="resource-list-title">${resource.name}</h3>
                                        <div class="resource-list-id">${resource.id.toString().padStart(3, '0')}</div>
                                    </div>
                                    
                                    <div class="resource-list-meta">
                                        <span class="resource-list-status ${resource.available ? 'available' : 'unavailable'}">
                                            ${resource.available ? '🟢 Available' : '🔴 Unavailable'}
                                        </span>
                                        
                                        ${resource.tags.length > 0 ? `
                                            <div class="resource-list-tags">
                                                ${resource.tags.slice(0, 4).map(tag => `<span class="tag">#${tag}</span>`).join('')}
                                                ${resource.tags.length > 4 ? `<span class="tag" style="background: #f59e0b; color: white; border-color: #f59e0b;">+${resource.tags.length - 4}</span>` : ''}
                                            </div>
                                        ` : `
                                            <div class="resource-list-tags">
                                                <span class="tag" style="opacity: 0.5;">No tags</span>
                                            </div>
                                        `}
                                    </div>
                                </div>
                                
                                <div class="resource-list-actions">
                                    <button class="btn-list-reserve" 
                                            ${!resource.available ? 'disabled' : ''} 
                                            onclick="showCreateReservationModal(${resource.id})">
                                        ${resource.available ? '📅 Reserve' : '🚫 Unavailable'}
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `}
            `;
}

function renderReservationsTab() {
    return `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #2c3e50;">My Reservations</h2>
                    <button class="btn btn-secondary" onclick="loadReservations(); renderDashboard();">
                        Refresh
                    </button>
                </div>

                <!-- Demo Section for History Feature -->
                <div class="demo-section">
                    <div class="demo-title">
                        📚 How to Check Reservation History
                    </div>
                    <div class="demo-steps">
                        <div class="demo-step">
                            <div class="demo-step-number">1</div>
                            <div class="demo-step-text">Look for any reservation below with a <span class="demo-highlight">History</span> button</div>
                        </div>
                        <div class="demo-step">
                            <div class="demo-step-number">2</div>
                            <div class="demo-step-text">Click the <span class="demo-highlight">History</span> button to view the complete audit trail</div>
                        </div>
                        <div class="demo-step">
                            <div class="demo-step-number">3</div>
                            <div class="demo-step-text">See when reservations were created, modified, or cancelled with timestamps</div>
                        </div>
                    </div>
                </div>

                ${reservations.map(reservation => {
        const startTime = new Date(reservation.start_time);
        const endTime = new Date(reservation.end_time);
        const isUpcoming = startTime > new Date();

        return `
                        <div class="reservation-item">
                            <div class="reservation-info">
                                <h3>${reservation.resource.name}</h3>
                                <div class="reservation-time">
                                    ${startTime.toLocaleDateString()} • ${startTime.toLocaleTimeString()} - ${endTime.toLocaleTimeString()}
                                </div>
                                <div class="reservation-badges">
                                    <span class="status-badge ${reservation.status === 'active' ? 'status-active' : 'status-cancelled'}">
                                        ${reservation.status.charAt(0).toUpperCase() + reservation.status.slice(1)}
                                    </span>
                                    ${isUpcoming ? '<span class="status-badge" style="background-color: #dbeafe; color: #1e40af;">Upcoming</span>' : ''}
                                </div>
                            </div>
                            
                            <div style="display: flex; gap: 8px; align-items: center;">
                                <button class="btn btn-secondary" onclick="showReservationHistory(${reservation.id})" style="padding: 8px 12px; font-size: 12px;">
                                    📋 History
                                </button>
                                ${reservation.status === 'active' && isUpcoming ? `
                                    <button class="btn btn-danger" onclick="cancelReservation(${reservation.id})">
                                        Cancel
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `;
    }).join('')}

                ${reservations.length === 0 ? `
                    <div class="empty-state">
                        <div class="empty-state-icon">📅</div>
                        <h3>No reservations found</h3>
                        <p>Once you make a reservation, you'll be able to view its complete history here</p>
                        <button class="btn btn-primary" onclick="switchTab('resources')">
                            📦 Browse Resources
                        </button>
                    </div>
                ` : ''}
            `;
}

function renderUpcomingTab() {
    const upcomingReservations = getUpcomingReservations();

    return `
                <h2 style="margin: 0 0 20px 0; color: #2c3e50;">Upcoming Reservations</h2>

                ${upcomingReservations.map(reservation => {
        const startTime = new Date(reservation.start_time);
        const endTime = new Date(reservation.end_time);
        const timeUntil = startTime - new Date();
        const hoursUntil = Math.floor(timeUntil / (1000 * 60 * 60));
        const daysUntil = Math.floor(hoursUntil / 24);

        let timeText;
        if (daysUntil > 0) {
            timeText = `in ${daysUntil} day${daysUntil > 1 ? 's' : ''}`;
        } else if (hoursUntil > 0) {
            timeText = `in ${hoursUntil} hour${hoursUntil > 1 ? 's' : ''}`;
        } else {
            timeText = 'starting soon';
        }

        return `
                        <div class="reservation-item">
                            <div class="reservation-info">
                                <h3>${reservation.resource.name}</h3>
                                <div class="reservation-time">
                                    ${startTime.toLocaleDateString()} • ${startTime.toLocaleTimeString()} - ${endTime.toLocaleTimeString()}
                                </div>
                                <div style="color: #3498db; font-size: 14px; margin-top: 4px;">
                                    ⏰ ${timeText}
                                </div>
                            </div>
                            <div style="text-align: center;">
                                <div style="width: 50px; height: 50px; background-color: #dbeafe; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px;">
                                    ✓
                                </div>
                            </div>
                        </div>
                    `;
    }).join('')}

                ${upcomingReservations.length === 0 ? `
                    <div class="empty-state">
                        <div class="empty-state-icon">⏰</div>
                        <p>No upcoming reservations</p>
                    </div>
                ` : ''}
            `;
}

// Helper Functions
function calculateStats() {
    return {
        totalResources: resources.length,
        availableResources: resources.filter(r => r.available).length,
        activeReservations: reservations.filter(r => r.status === 'active').length,
        upcomingReservations: getUpcomingReservations().length
    };
}

function getUpcomingReservations() {
    return reservations
        .filter(r => r.status === 'active' && new Date(r.start_time) > new Date())
        .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
}

// Event Handlers
function switchAuthTab(event, tab) {
    const tabs = document.querySelectorAll('.auth-tab');
    tabs.forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');

    const confirmGroup = document.getElementById('confirmPasswordGroup');
    const submitBtn = document.getElementById('authSubmit');

    if (tab === 'register') {
        confirmGroup.style.display = 'block';
        submitBtn.textContent = 'Register';
    } else {
        confirmGroup.style.display = 'none';
        submitBtn.textContent = 'Sign In';
    }
}

async function handleAuth(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const username = formData.get('username');
    const password = formData.get('password');
    const confirmPassword = formData.get('confirmPassword');
    const isLogin = document.querySelector('.auth-tab.active').textContent === 'Sign In';

    const errorDiv = document.getElementById('authError');
    const submitBtn = document.getElementById('authSubmit');

    // Clear previous errors
    errorDiv.classList.add('hidden');
    errorDiv.textContent = '';

    // Validation
    if (!isLogin && password !== confirmPassword) {
        errorDiv.textContent = 'Passwords do not match';
        errorDiv.classList.remove('hidden');
        return;
    }

    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Processing...';

    try {
        if (isLogin) {
            await login(username, password);
            currentView = 'dashboard';
            await loadDashboard();
        } else {
            await register(username, password);
            // Switch to login tab after successful registration
            const loginTab = document.querySelector('.auth-tab');
            const registerTab = document.querySelectorAll('.auth-tab')[1];
            loginTab.classList.add('active');
            registerTab.classList.remove('active');
            document.getElementById('confirmPasswordGroup').style.display = 'none';
            document.getElementById('authSubmit').textContent = 'Sign In';
            form.reset();
            showMessage('Registration successful! Please sign in.', 'success');
        }
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = isLogin ? 'Sign In' : 'Register';
    }
}

function switchTab(tab) {
    activeTab = tab;

    // Update tab visual state
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(t => t.classList.remove('active'));

    // Find and activate the correct tab
    tabs.forEach(t => {
        if (t.textContent.toLowerCase().includes(tab) ||
            (tab === 'resources' && t.textContent.includes('Resources')) ||
            (tab === 'reservations' && t.textContent.includes('My Reservations')) ||
            (tab === 'upcoming' && t.textContent.includes('Upcoming'))) {
            t.classList.add('active');
        }
    });

    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = renderTabContent();
}

function handleSearch(value) {
    // Store the current input element and cursor position before re-rendering
    const activeElement = document.activeElement;
    if (activeElement && activeElement.classList.contains('search-input')) {
        searchInputElement = activeElement;
        lastCursorPosition = activeElement.selectionStart;
    }

    // Update search query and filter results
    searchQuery = value;
    filterResources();

    // Re-render the tab content
    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = renderTabContent();

    // Restore focus and cursor position after re-rendering
    restoreSearchFocus();
}

// Function to restore focus and cursor position to the search input
function restoreSearchFocus() {
    // Use requestAnimationFrame to ensure DOM has been updated
    requestAnimationFrame(() => {
        const newSearchInput = document.querySelector('.search-input');
        if (newSearchInput && searchInputElement) {
            // Restore focus
            newSearchInput.focus();

            // Restore cursor position
            if (typeof lastCursorPosition === 'number') {
                newSearchInput.setSelectionRange(lastCursorPosition, lastCursorPosition);
            }

            // Update the stored reference
            searchInputElement = newSearchInput;
        }
    });
}
function handleFilterChange(filter) {
    currentFilter = filter;
    filterResources();
    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = renderTabContent();
}

function handleViewModeChange(mode) {
    viewMode = mode;
    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = renderTabContent();
}

async function cancelReservation(reservationId) {
    if (!confirm('Are you sure you want to cancel this reservation?')) {
        return;
    }

    try {
        await apiCall(`/reservations/${reservationId}/cancel`, {
            method: 'POST',
            body: JSON.stringify({})
        });
        await loadReservations();
        renderDashboard();
        showMessage('Reservation cancelled successfully', 'success');
    } catch (error) {
        showMessage('Failed to cancel reservation: ' + error.message, 'error');
    }
}

function showCreateResourceModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2 class="modal-title">Create New Resource</h2>
                        <button class="close-btn" onclick="closeModal(this)">&times;</button>
                    </div>
                    
                    <form onsubmit="handleCreateResource(event)">
                        <div class="form-group">
                            <label class="form-label">Resource Name</label>
                            <input type="text" class="form-input" name="name" placeholder="e.g., Conference Room A" required>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">Tags (comma-separated)</label>
                            <input type="text" class="form-input" name="tags" placeholder="e.g., meeting, conference, large">
                        </div>
                        
                        <div class="form-group">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" name="available" checked>
                                <span>Available for booking</span>
                            </label>
                        </div>
                        
                        <div id="createResourceError" class="alert alert-error hidden"></div>
                        
                        <div class="modal-actions">
                            <button type="button" class="btn btn-secondary" onclick="closeModal(this)">Cancel</button>
                            <button type="submit" class="btn btn-success">Create Resource</button>
                        </div>
                    </form>
                </div>
            `;
    document.body.appendChild(modal);
}

function showUploadCSVModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2 class="modal-title">Upload Resources from CSV</h2>
                        <button class="close-btn" onclick="closeModal(this)">&times;</button>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 16px; border-radius: 6px; margin-bottom: 20px; font-size: 14px;">
                        <h4 style="margin: 0 0 8px 0; color: #2c3e50;">CSV Format Requirements:</h4>
                        <ul style="margin: 0; padding-left: 20px; color: #666;">
                            <li>Required columns: <code>name</code></li>
                            <li>Optional columns: <code>tags</code> (comma-separated), <code>available</code> (true/false)</li>
                            <li>Example: <code>Conference Room A,"meeting,large",true</code></li>
                        </ul>
                    </div>
                    
                    <form onsubmit="handleUploadCSV(event)">
                        <div class="form-group">
                            <label class="form-label">Select CSV File</label>
                            <input type="file" class="form-input" name="csvFile" accept=".csv" required onchange="handleFileSelect(event)">
                        </div>
                        
                        <div id="filePreview" class="hidden" style="margin-bottom: 20px;">
                            <h4 style="margin: 0 0 10px 0; color: #2c3e50;">File Preview:</h4>
                            <div id="previewContent" style="background-color: #f8f9fa; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto;"></div>
                            <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">
                                <span id="previewInfo"></span>
                            </p>
                        </div>
                        
                        <div id="uploadCSVError" class="alert alert-error hidden"></div>
                        
                        <div class="modal-actions">
                            <button type="button" class="btn btn-secondary" onclick="closeModal(this)">Cancel</button>
                            <button type="submit" class="btn btn-primary" id="uploadCSVBtn" disabled>Upload Resources</button>
                        </div>
                    </form>
                </div>
            `;
    document.body.appendChild(modal);
}

function showCreateReservationModal(resourceId) {
    const resource = resources.find(r => r.id === resourceId);
    if (!resource) return;

    // Set default dates/times
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const startDate = tomorrow.toISOString().split('T')[0];
    const startTime = '09:00';
    const endTime = '10:00';

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2 class="modal-title">Reserve Resource</h2>
                        <button class="close-btn" onclick="closeModal(this)">&times;</button>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 16px; border-radius: 6px; margin-bottom: 20px;">
                        <h3 style="margin: 0 0 8px 0; color: #2c3e50;">${resource.name}</h3>
                        ${resource.tags.length > 0 ? `
                            <div class="tags">
                                ${resource.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                            </div>
                        ` : ''}
                    </div>
                    
                    <form onsubmit="handleCreateReservation(event, ${resourceId})">
                        <div class="form-grid">
                            <div class="form-group">
                                <label class="form-label">Start Date</label>
                                <input type="date" class="form-input" name="startDate" value="${startDate}" required>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Start Time</label>
                                <input type="time" class="form-input" name="startTime" value="${startTime}" required>
                            </div>
                        </div>
                        
                        <div class="form-grid">
                            <div class="form-group">
                                <label class="form-label">End Date</label>
                                <input type="date" class="form-input" name="endDate" value="${startDate}" required>
                            </div>
                            <div class="form-group">
                                <label class="form-label">End Time</label>
                                <input type="time" class="form-input" name="endTime" value="${endTime}" required>
                            </div>
                        </div>
                        
                        <div id="createReservationError" class="alert alert-error hidden"></div>
                        
                        <div class="modal-actions">
                            <button type="button" class="btn btn-secondary" onclick="closeModal(this)">Cancel</button>
                            <button type="submit" class="btn btn-primary">Reserve Resource</button>
                        </div>
                    </form>
                </div>
            `;
    document.body.appendChild(modal);
}

async function handleCreateResource(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const errorDiv = document.getElementById('createResourceError');
    const submitBtn = form.querySelector('button[type="submit"]');

    // Clear previous errors
    errorDiv.classList.add('hidden');
    errorDiv.textContent = '';

    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Creating...';

    try {
        const tags = formData.get('tags').split(',').map(tag => tag.trim()).filter(tag => tag);
        await apiCall('/resources', {
            method: 'POST',
            body: JSON.stringify({
                name: formData.get('name'),
                tags,
                available: formData.get('available') === 'on'
            })
        });

        closeModal(submitBtn);
        await loadResources();
        renderDashboard();
        showMessage('Resource created successfully', 'success');
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Resource';
    }
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    const previewDiv = document.getElementById('filePreview');
    const previewContent = document.getElementById('previewContent');
    const previewInfo = document.getElementById('previewInfo');
    const uploadBtn = document.getElementById('uploadCSVBtn');

    if (!file) {
        previewDiv.classList.add('hidden');
        uploadBtn.disabled = true;
        return;
    }

    if (!file.name.toLowerCase().endsWith('.csv')) {
        showMessage('Please select a CSV file', 'error');
        uploadBtn.disabled = true;
        return;
    }

    const reader = new FileReader();
    reader.onload = function (e) {
        const csvContent = e.target.result;
        const lines = csvContent.split('\n').filter(line => line.trim());

        if (lines.length === 0) {
            showMessage('CSV file is empty', 'error');
            uploadBtn.disabled = true;
            return;
        }

        // Show preview of first 5 lines
        const previewLines = lines.slice(0, 6); // Header + 5 data rows
        previewContent.innerHTML = previewLines.map((line, index) => {
            const isHeader = index === 0;
            return `<div style="${isHeader ? 'font-weight: bold; color: #2c3e50;' : 'color: #666;'}">${line}</div>`;
        }).join('');

        previewInfo.textContent = `File: ${file.name} • ${lines.length - 1} resources (excluding header) • ${(file.size / 1024).toFixed(1)} KB`;

        previewDiv.classList.remove('hidden');
        uploadBtn.disabled = false;
    };

    reader.readAsText(file);
}

async function handleUploadCSV(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const file = formData.get('csvFile');
    const errorDiv = document.getElementById('uploadCSVError');
    const submitBtn = document.getElementById('uploadCSVBtn');

    if (!file) {
        errorDiv.textContent = 'Please select a CSV file';
        errorDiv.classList.remove('hidden');
        return;
    }

    // Clear previous errors
    errorDiv.classList.add('hidden');
    errorDiv.textContent = '';

    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Uploading...';

    try {
        // Create FormData for file upload
        const uploadFormData = new FormData();
        uploadFormData.append('file', file);

        const response = await fetch(`${API_BASE_URL}/resources/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: uploadFormData
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(error || 'Upload failed');
        }

        const result = await response.json();

        closeModal(submitBtn);
        await loadResources();
        renderDashboard();

        // Show detailed success message
        let message = `Successfully created ${result.created_count} resources`;
        if (result.errors && result.errors.length > 0) {
            message += ` (${result.errors.length} errors encountered)`;
            console.warn('Upload errors:', result.errors);
        }
        showMessage(message, 'success');

        // Show errors in console for debugging
        if (result.errors && result.errors.length > 0) {
            setTimeout(() => {
                showMessage(`Upload completed with ${result.errors.length} errors. Check console for details.`, 'error');
            }, 3000);
        }

    } catch (error) {
        errorDiv.textContent = error.message || 'Upload failed';
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Upload Resources';
    }
}

function showAdvancedSearchModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2 class="modal-title">Advanced Resource Search</h2>
                        <button class="close-btn" onclick="closeModal(this)">&times;</button>
                    </div>
                    
                    <form onsubmit="handleAdvancedSearch(event)">
                        <div class="form-group">
                            <label class="form-label">Search Query (resource name or tags)</label>
                            <input type="text" class="form-input" name="query" placeholder="e.g., meeting, projector, large">
                        </div>
                        
                        <div class="form-group">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                                <input type="checkbox" name="availableOnly" checked>
                                <span>Show only available resources</span>
                            </label>
                        </div>
                        
                        <div style="background-color: #f8f9fa; padding: 16px; border-radius: 6px; margin-bottom: 20px;">
                            <h4 style="margin: 0 0 12px 0; color: #2c3e50;">Time-based Availability Filter</h4>
                            <p style="margin: 0 0 12px 0; font-size: 14px; color: #666;">Check if resources are available during a specific time period</p>
                            
                            <div class="form-grid">
                                <div class="form-group">
                                    <label class="form-label">Available From</label>
                                    <input type="datetime-local" class="form-input" name="availableFrom">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">Available Until</label>
                                    <input type="datetime-local" class="form-input" name="availableUntil">
                                </div>
                            </div>
                        </div>
                        
                        <div id="advancedSearchError" class="alert alert-error hidden"></div>
                        
                        <div class="modal-actions">
                            <button type="button" class="btn btn-secondary" onclick="closeModal(this)">Cancel</button>
                            <button type="submit" class="btn btn-primary">Search Resources</button>
                        </div>
                    </form>
                </div>
            `;
    document.body.appendChild(modal);
}

async function handleAdvancedSearch(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const errorDiv = document.getElementById('advancedSearchError');
    const submitBtn = form.querySelector('button[type="submit"]');

    // Clear previous errors
    errorDiv.classList.add('hidden');
    errorDiv.textContent = '';

    try {
        const query = formData.get('query').trim();
        const availableOnly = formData.get('availableOnly') === 'on';
        const availableFrom = formData.get('availableFrom');
        const availableUntil = formData.get('availableUntil');

        // Validate time range if provided
        if ((availableFrom && !availableUntil) || (!availableFrom && availableUntil)) {
            throw new Error('Both start and end times must be specified for time filtering');
        }

        if (availableFrom && availableUntil) {
            const startTime = new Date(availableFrom);
            const endTime = new Date(availableUntil);

            if (endTime <= startTime) {
                throw new Error('End time must be after start time');
            }

            if (startTime <= new Date()) {
                throw new Error('Start time must be in the future');
            }
        }

        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Searching...';

        // Prepare search parameters
        const params = new URLSearchParams();
        if (query) params.append('q', query);
        if (availableOnly) params.append('available_only', 'true');
        if (availableFrom) params.append('available_from', new Date(availableFrom).toISOString());
        if (availableUntil) params.append('available_until', new Date(availableUntil).toISOString());

        // Make API call to search endpoint
        const searchResults = await apiCall(`/resources/search?${params.toString()}`);

        // Update filtered resources and re-render
        filteredResources = searchResults;
        searchQuery = query; // Update search query for consistency

        closeModal(submitBtn);
        renderDashboard();

        // Show results message
        if (availableFrom && availableUntil) {
            const startTime = new Date(availableFrom);
            const endTime = new Date(availableUntil);
            showMessage(`Found ${searchResults.length} resources available from ${startTime.toLocaleString()} to ${endTime.toLocaleString()}`, 'success');
        } else {
            showMessage(`Found ${searchResults.length} resources matching your criteria`, 'success');
        }

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Search Resources';
    }
}

function showReservationHistory(reservationId) {
    // Show loading state
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2 class="modal-title">Reservation History</h2>
                        <button class="close-btn" onclick="closeModal(this)">&times;</button>
                    </div>
                    
                    <div style="text-align: center; padding: 40px;">
                        <div class="spinner" style="margin: 0 auto 16px auto; width: 32px; height: 32px;"></div>
                        <p>Loading history...</p>
                    </div>
                </div>
            `;
    document.body.appendChild(modal);

    // Load and display history
    loadReservationHistory(reservationId, modal);
}

async function loadReservationHistory(reservationId, modal) {
    try {
        const history = await apiCall(`/reservations/${reservationId}/history`);

        // Find the reservation details
        const reservation = reservations.find(r => r.id === reservationId);

        const modalContent = modal.querySelector('.modal-content');
        modalContent.innerHTML = `
                    <div class="modal-header">
                        <h2 class="modal-title">📋 Reservation History</h2>
                        <button class="close-btn" onclick="closeModal(this)">&times;</button>
                    </div>
                    
                    ${reservation ? `
                        <div style="background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); padding: 16px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #cbd5e1;">
                            <h3 style="margin: 0 0 8px 0; color: #1e293b; display: flex; align-items: center; gap: 8px;">
                                🏢 ${reservation.resource.name}
                                <span class="resource-id">${reservation.id.toString().padStart(3, '0')}</span>
                            </h3>
                            <p style="margin: 0; color: #64748b; font-size: 14px;">
                                📅 ${new Date(reservation.start_time).toLocaleString()} - ${new Date(reservation.end_time).toLocaleString()}
                            </p>
                        </div>
                    ` : ''}
                    
                    <div style="max-height: 400px; overflow-y: auto;">
                        ${history.length > 0 ? `
                            <div class="history-timeline">
                                ${history.map(entry => {
            const timestamp = new Date(entry.timestamp);
            const actionIcons = {
                'created': '✅',
                'cancelled': '❌',
                'updated': '📝'
            };

            return `
                                        <div class="history-entry ${entry.action}">
                                            <div class="history-header">
                                                <div class="history-action">
                                                    ${actionIcons[entry.action] || '📋'} 
                                                    ${entry.action.charAt(0).toUpperCase() + entry.action.slice(1)}
                                                </div>
                                                <div class="history-timestamp">
                                                    ${timestamp.toLocaleDateString()} at ${timestamp.toLocaleTimeString()}
                                                </div>
                                            </div>
                                            ${entry.details ? `
                                                <p class="history-details">
                                                    ${entry.details}
                                                </p>
                                            ` : ''}
                                        </div>
                                    `;
        }).join('')}
                            </div>
                        ` : `
                            <div class="empty-state">
                                <div class="empty-state-icon">📋</div>
                                <h3>No history available</h3>
                                <p>History tracking wasn't available when this reservation was created</p>
                            </div>
                        `}
                    </div>
                    
                    <div style="margin-top: 20px; text-align: center; padding-top: 16px; border-top: 1px solid #e2e8f0;">
                        <button type="button" class="btn btn-secondary" onclick="closeModal(this)">Close History</button>
                    </div>
                `;

    } catch (error) {
        const modalContent = modal.querySelector('.modal-content');
        modalContent.innerHTML = `
                    <div class="modal-header">
                        <h2 class="modal-title">📋 Reservation History</h2>
                        <button class="close-btn" onclick="closeModal(this)">&times;</button>
                    </div>
                    
                    <div class="alert alert-error">
                        <strong>Unable to load history:</strong> ${error.message}
                    </div>
                    
                    <div style="text-align: center; margin-top: 20px;">
                        <button type="button" class="btn btn-secondary" onclick="closeModal(this)">Close</button>
                    </div>
                `;
    }
}

async function handleCreateReservation(event, resourceId) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const errorDiv = document.getElementById('createReservationError');
    const submitBtn = form.querySelector('button[type="submit"]');

    // Clear previous errors
    errorDiv.classList.add('hidden');
    errorDiv.textContent = '';

    try {
        const startDateTime = new Date(`${formData.get('startDate')}T${formData.get('startTime')}`);
        const endDateTime = new Date(`${formData.get('endDate')}T${formData.get('endTime')}`);

        if (endDateTime <= startDateTime) {
            throw new Error('End time must be after start time');
        }

        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Reserving...';

        await apiCall('/reservations', {
            method: 'POST',
            body: JSON.stringify({
                resource_id: resourceId,
                start_time: startDateTime.toISOString(),
                end_time: endDateTime.toISOString()
            })
        });

        closeModal(submitBtn);
        await loadReservations();
        renderDashboard();
        showMessage('Reservation created successfully', 'success');
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Reserve Resource';
    }
}

function closeModal(element) {
    const modal = element.closest('.modal');
    if (modal) {
        modal.remove();
    }
}

function showMessage(message, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `alert ${type === 'success' ? 'alert-success' : 'alert-error'}`;
    messageDiv.textContent = message;
    messageDiv.style.position = 'fixed';
    messageDiv.style.top = '20px';
    messageDiv.style.right = '20px';
    messageDiv.style.zIndex = '1001';
    messageDiv.style.minWidth = '300px';

    document.body.appendChild(messageDiv);

    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    }, 5000);
}

// Close modal when clicking outside
document.addEventListener('click', function (event) {
    if (event.target.classList.contains('modal')) {
        event.target.remove();
    }
});

// Initialize the application
init();