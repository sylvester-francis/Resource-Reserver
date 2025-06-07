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
let currentFilter = 'all';
let viewMode = 'grid';
let systemStatus = null;
let availabilitySummary = null;

// Initialize app
function init() {
    if (authToken && currentUser) {
        currentView = 'dashboard';
        loadDashboard();
    } else {
        currentView = 'login';
        renderLogin();
    }

    if (authToken) {
        loadSystemStatus();
        setInterval(loadSystemStatus, 30000);
    }
}

// Enhanced API Helper Functions
async function apiCall(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(authToken && { 'Authorization': `Bearer ${authToken}` }),
        ...options.headers
    };

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers
        });

        if (!response.ok) {
            const errorText = await response.text();
            let errorMessage;
            try {
                const errorJson = JSON.parse(errorText);
                errorMessage = errorJson.detail || errorText;
            } catch {
                errorMessage = errorText || `HTTP ${response.status}: ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        }
        return await response.text();
    } catch (error) {
        console.error(`API call failed for ${endpoint}:`, error);
        throw error;
    }
}

async function checkHealth() {
    try {
        return await apiCall('/health');
    } catch (error) {
        console.error('Health check failed:', error);
        throw error;
    }
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
        const error = await response.text();
        throw new Error(error || 'Invalid credentials');
    }

    const data = await response.json();
    authToken = data.access_token;
    currentUser = { username };

    localStorage.setItem('auth_token', authToken);
    localStorage.setItem('user', JSON.stringify(currentUser));

    return data;
}

async function register(username, password) {
    return await apiCall('/register', {
        method: 'POST',
        body: JSON.stringify({ username, password })
    });
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    currentView = 'login';
    renderLogin();
}

async function loadResources() {
    try {
        resources = await apiCall('/resources');
        filterResources();
    } catch (error) {
        console.error('Failed to load resources:', error);
        showMessage('Failed to load resources: ' + error.message, 'error');
    }
}

async function searchResources(params = {}) {
    try {
        const queryParams = new URLSearchParams();

        if (params.query) queryParams.append('q', params.query);
        if (params.availableOnly !== undefined) queryParams.append('available_only', params.availableOnly);
        if (params.availableFrom) queryParams.append('available_from', params.availableFrom);
        if (params.availableUntil) queryParams.append('available_until', params.availableUntil);

        const queryString = queryParams.toString();
        const endpoint = queryString ? `/resources/search?${queryString}` : '/resources/search';

        return await apiCall(endpoint);
    } catch (error) {
        console.error('Failed to search resources:', error);
        throw error;
    }
}

async function getResourceAvailability(resourceId, daysAhead = 7) {
    try {
        const params = new URLSearchParams({ days_ahead: daysAhead });
        return await apiCall(`/resources/${resourceId}/availability?${params}`);
    } catch (error) {
        console.error('Failed to get resource availability:', error);
        throw error;
    }
}

async function updateResourceAvailability(resourceId, available) {
    try {
        return await apiCall(`/resources/${resourceId}/availability`, {
            method: 'PUT',
            body: JSON.stringify({ available })
        });
    } catch (error) {
        console.error('Failed to update resource availability:', error);
        throw error;
    }
}

async function getAvailabilitySummary() {
    try {
        availabilitySummary = await apiCall('/resources/availability/summary');
        return availabilitySummary;
    } catch (error) {
        console.error('Failed to get availability summary:', error);
        throw error;
    }
}

async function loadReservations(includeCancelled = false) {
    try {
        const params = new URLSearchParams();
        if (includeCancelled) params.append('include_cancelled', 'true');

        const endpoint = params.toString() ? `/reservations/my?${params}` : '/reservations/my';
        reservations = await apiCall(endpoint);
    } catch (error) {
        console.error('Failed to load reservations:', error);
        showMessage('Failed to load reservations: ' + error.message, 'error');
    }
}

async function getReservationHistory(reservationId) {
    try {
        return await apiCall(`/reservations/${reservationId}/history`);
    } catch (error) {
        console.error('Failed to get reservation history:', error);
        throw error;
    }
}

async function manualCleanupExpired() {
    try {
        return await apiCall('/admin/cleanup-expired', { method: 'POST' });
    } catch (error) {
        console.error('Failed to cleanup expired reservations:', error);
        throw error;
    }
}

async function loadSystemStatus() {
    try {
        systemStatus = await checkHealth();

        if (authToken) {
            await getAvailabilitySummary();
        }
    } catch (error) {
        console.error('Failed to load system status:', error);
        systemStatus = { status: 'error', error: error.message };
    }
}

function filterResources() {
    let filtered = resources;

    if (currentFilter === 'available') {
        filtered = filtered.filter(r => r.available);
    } else if (currentFilter === 'unavailable') {
        filtered = filtered.filter(r => !r.available);
    }

    if (searchQuery) {
        filtered = filtered.filter(resource =>
            resource.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            resource.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
        );
    }

    filteredResources = filtered;
}

async function loadDashboard() {
    try {
        await Promise.all([
            loadResources(),
            loadReservations(),
            loadSystemStatus()
        ]);
        renderDashboard();
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        showMessage('Failed to load dashboard data', 'error');
    }
}
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

    const app = document.getElementById('app');
    app.innerHTML = `
        <div class="container">
            <div class="header">
                <div>
                    <h1>Resource Reservation System</h1>
                    <div class="user-info">Welcome back, ${currentUser.username}</div>
                </div>
                <div class="header-actions">
                    <button class="btn btn-sm btn-secondary" onclick="showSystemStatusModal()">
                        📊 System Status
                    </button>
                    <button class="btn btn-sm btn-warning" onclick="showAdminModal()">
                        ⚙️ Admin
                    </button>
                    <button class="btn btn-secondary" onclick="logout()">Sign Out</button>
                </div>
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
                    📦 Resources
                </button>
                <button class="nav-tab ${activeTab === 'reservations' ? 'active' : ''}" onclick="switchTab('reservations')">
                    📅 My Reservations
                </button>
                <button class="nav-tab ${activeTab === 'upcoming' ? 'active' : ''}" onclick="switchTab('upcoming')">
                    ⏰ Upcoming
                </button>
                <button class="nav-tab ${activeTab === 'analytics' ? 'active' : ''}" onclick="switchTab('analytics')">
                    📊 Analytics
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
        case 'analytics':
            return renderAnalyticsTab();
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
                        <button class="btn btn-secondary" onclick="showTimeSearchModal()">
                            🕒 Time Search
                        </button>
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
                ${filteredResources.map(resource => renderResourceCard(resource)).join('')}
            </div>

            <div class="resources-list ${viewMode === 'list' ? 'active' : ''}" style="${viewMode === 'list' ? 'display: flex' : 'display: none'}">
                ${filteredResources.map(resource => renderResourceListItem(resource)).join('')}
            </div>
        `}
    `;
}

function renderResourceCard(resource) {
    return `
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
                        onclick="showExtendedReservationModal(${resource.id})">
                    ${resource.available ? '📅 Reserve Now' : '🚫 Unavailable'}
                </button>
                <button class="btn-resource-action" onclick="showResourceAvailability(${resource.id})">
                    📊 Schedule
                </button>
                <button class="btn-resource-action" onclick="showMaintenanceModal(${resource.id})">
                    ⚙️ Maintain
                </button>
            </div>
        </div>
    `;
}

function renderResourceListItem(resource) {
    return `
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
                        onclick="showExtendedReservationModal(${resource.id})">
                    ${resource.available ? '📅 Reserve' : '🚫 Unavailable'}
                </button>
                <button class="btn btn-sm btn-secondary" onclick="showResourceAvailability(${resource.id})">
                    📊
                </button>
                <button class="btn btn-sm btn-secondary" onclick="showMaintenanceModal(${resource.id})">
                    ⚙️
                </button>
            </div>
        </div>
    `;
}

function renderReservationsTab() {
    return `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 16px;">
            <h2 style="margin: 0; color: #2c3e50;">My Reservations</h2>
            <div style="display: flex; gap: 12px;">
                <button class="btn btn-secondary" onclick="loadReservations(true); renderDashboard();">
                    📋 Include Cancelled
                </button>
                <button class="btn btn-secondary" onclick="loadReservations(); renderDashboard();">
                    🔄 Refresh
                </button>
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
                    
                    <div class="reservation-actions">
                        <button class="btn btn-sm btn-secondary" onclick="showReservationHistory(${reservation.id})">
                            📋 History
                        </button>
                        ${reservation.status === 'active' && isUpcoming ? `
                            <button class="btn btn-sm btn-danger" onclick="cancelReservation(${reservation.id})">
                                ❌ Cancel
                            </button>
                        ` : ''}
                        <button class="btn btn-sm btn-secondary" onclick="showResourceAvailability(${reservation.resource_id})">
                            📊 Schedule
                        </button>
                    </div>
                </div>
            `;
    }).join('')}

        ${reservations.length === 0 ? `
            <div class="empty-state">
                <div class="empty-state-icon">📅</div>
                <h3>No reservations found</h3>
                <p>Once you make a reservation, you'll see it here with full history tracking</p>
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
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #2c3e50;">Upcoming Reservations</h2>
            <button class="btn btn-secondary" onclick="loadReservations(); renderDashboard();">
                🔄 Refresh
            </button>
        </div>

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
                    <div class="reservation-actions">
                        <button class="btn btn-sm btn-secondary" onclick="showReservationHistory(${reservation.id})">
                            📋 History
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="cancelReservation(${reservation.id})">
                            ❌ Cancel
                        </button>
                    </div>
                </div>
            `;
    }).join('')}

        ${upcomingReservations.length === 0 ? `
            <div class="empty-state">
                <div class="empty-state-icon">⏰</div>
                <h3>No upcoming reservations</h3>
                <p>Your upcoming reservations will appear here</p>
                <button class="btn btn-primary" onclick="switchTab('resources')">
                    📦 Browse Resources
                </button>
            </div>
        ` : ''}
    `;
}

function renderAnalyticsTab() {
    const stats = calculateDetailedStats();

    return `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #2c3e50;">System Analytics</h2>
            <button class="btn btn-secondary" onclick="loadDashboard();">
                🔄 Refresh Data
            </button>
        </div>

        <div class="system-status">
            <div class="status-section">
                <h3>📊 Resource Statistics</h3>
                <div class="status-item">
                    <span class="status-label">Total Resources</span>
                    <span class="status-value">${stats.totalResources}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Available Now</span>
                    <span class="status-value success">${stats.availableResources}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">In Maintenance</span>
                    <span class="status-value warning">${stats.unavailableResources}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Utilization Rate</span>
                    <span class="status-value">${stats.utilizationRate}%</span>
                </div>
            </div>

            <div class="status-section">
                <h3>📅 Reservation Statistics</h3>
                <div class="status-item">
                    <span class="status-label">Active Reservations</span>
                    <span class="status-value">${stats.activeReservations}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Upcoming Reservations</span>
                    <span class="status-value">${stats.upcomingReservations}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Cancelled Reservations</span>
                    <span class="status-value warning">${stats.cancelledReservations}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Total Reservations</span>
                    <span class="status-value">${stats.totalReservations}</span>
                </div>
            </div>

            <div class="status-section">
                <h3>⚙️ System Health</h3>
                <div class="status-item">
                    <span class="status-label">API Status</span>
                    <span class="status-value ${systemStatus?.status === 'healthy' ? 'success' : 'error'}">
                        ${systemStatus?.status === 'healthy' ? '✅ Healthy' : '❌ Error'}
                    </span>
                </div>
                <div class="status-item">
                    <span class="status-label">Background Tasks</span>
                    <span class="status-value success">
                        ${systemStatus?.background_tasks?.cleanup_task === 'running' ? '✅ Running' : '⚠️ Stopped'}
                    </span>
                </div>
                <div class="status-item">
                    <span class="status-label">Last Updated</span>
                    <span class="status-value">
                        ${systemStatus?.timestamp ? new Date(systemStatus.timestamp).toLocaleTimeString() : 'Unknown'}
                    </span>
                </div>
            </div>
        </div>

        <div style="margin-top: 24px;">
            <h3>🔧 System Actions</h3>
            <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                <button class="btn btn-warning" onclick="triggerCleanup()">
                    🧹 Cleanup Expired Reservations
                </button>
                <button class="btn btn-secondary" onclick="showSystemStatusModal()">
                    📊 Detailed System Status
                </button>
                <button class="btn btn-secondary" onclick="loadSystemStatus(); renderDashboard();">
                    🔄 Refresh System Status
                </button>
            </div>
        </div>
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

function calculateDetailedStats() {
    const totalResources = resources.length;
    const availableResources = resources.filter(r => r.available).length;
    const unavailableResources = totalResources - availableResources;
    const activeReservations = reservations.filter(r => r.status === 'active').length;
    const cancelledReservations = reservations.filter(r => r.status === 'cancelled').length;
    const upcomingReservations = getUpcomingReservations().length;

    const utilizationRate = totalResources > 0 ?
        Math.round((activeReservations / totalResources) * 100) : 0;

    return {
        totalResources,
        availableResources,
        unavailableResources,
        activeReservations,
        cancelledReservations,
        upcomingReservations,
        totalReservations: reservations.length,
        utilizationRate
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

    errorDiv.classList.add('hidden');
    errorDiv.textContent = '';

    if (!isLogin && password !== confirmPassword) {
        errorDiv.textContent = 'Passwords do not match';
        errorDiv.classList.remove('hidden');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Processing...';

    try {
        if (isLogin) {
            await login(username, password);
            currentView = 'dashboard';
            await loadDashboard();
        } else {
            await register(username, password);
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
    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = renderTabContent();
}

function handleSearch(value) {
    searchQuery = value;
    filterResources();
    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = renderTabContent();
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

// Modal Functions
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
    }
}

function showSystemStatusModal() {
    showModal('systemStatusModal');
    loadSystemStatusDetails();
}

async function loadSystemStatusDetails() {
    const content = document.getElementById('systemStatusContent');

    try {
        await loadSystemStatus();

        content.innerHTML = `
            <div class="system-status">
                <div class="status-section">
                    <h3>🌐 API Health</h3>
                    <div class="status-item">
                        <span class="status-label">Status</span>
                        <span class="status-value ${systemStatus?.status === 'healthy' ? 'success' : 'error'}">
                            ${systemStatus?.status || 'Unknown'}
                        </span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Timestamp</span>
                        <span class="status-value">
                            ${systemStatus?.timestamp ? new Date(systemStatus.timestamp).toLocaleString() : 'Unknown'}
                        </span>
                    </div>
                </div>

                <div class="status-section">
                    <h3>🔧 Background Tasks</h3>
                    ${systemStatus?.background_tasks ? Object.entries(systemStatus.background_tasks).map(([name, status]) => `
                        <div class="status-item">
                            <span class="status-label">${name.replace('_', ' ').toUpperCase()}</span>
                            <span class="status-value ${status === 'running' ? 'success' : status === 'failed' ? 'error' : 'warning'}">
                                ${status}
                            </span>
                        </div>
                    `).join('') : '<p>No background task information available</p>'}
                </div>

                ${availabilitySummary ? `
                    <div class="status-section">
                        <h3>📊 Resource Summary</h3>
                        <div class="status-item">
                            <span class="status-label">Total Resources</span>
                            <span class="status-value">${availabilitySummary.total_resources}</span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Available Now</span>
                            <span class="status-value success">${availabilitySummary.available_now}</span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Unavailable</span>
                            <span class="status-value warning">${availabilitySummary.unavailable_now}</span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Currently In Use</span>
                            <span class="status-value">${availabilitySummary.currently_in_use}</span>
                        </div>
                        <div class="status-item">
                            <span class="status-label">Last Updated</span>
                            <span class="status-value">
                                ${new Date(availabilitySummary.timestamp).toLocaleString()}
                            </span>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    } catch (error) {
        content.innerHTML = `
            <div class="alert alert-error">
                Failed to load system status: ${error.message}
            </div>
        `;
    }
}

function showAdminModal() {
    showModal('adminModal');
}

async function triggerCleanup() {
    const resultsDiv = document.getElementById('adminResults');
    resultsDiv.classList.remove('hidden');
    resultsDiv.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Triggering cleanup...</p>
        </div>
    `;

    try {
        const result = await manualCleanupExpired();
        resultsDiv.innerHTML = `
            <div class="alert alert-success">
                <strong>Cleanup completed!</strong><br>
                Cleaned up ${result.expired_count} expired reservations<br>
                <small>Completed at: ${new Date(result.timestamp).toLocaleString()}</small>
            </div>
        `;

        await loadReservations();
        await loadSystemStatus();

        showMessage(`Cleanup completed: ${result.expired_count} expired reservations removed`, 'success');
    } catch (error) {
        resultsDiv.innerHTML = `
            <div class="alert alert-error">
                <strong>Cleanup failed:</strong> ${error.message}
            </div>
        `;
        showMessage('Cleanup failed: ' + error.message, 'error');
    }
}

function showTimeSearchModal() {
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const startDate = tomorrow.toISOString().slice(0, 16);
    const endDate = new Date(tomorrow.getTime() + 2 * 60 * 60 * 1000).toISOString().slice(0, 16);

    const form = document.getElementById('timeSearchForm');
    form.availableFrom.value = startDate;
    form.availableUntil.value = endDate;

    showModal('timeSearchModal');
}

async function handleTimeSearch(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const errorDiv = document.getElementById('timeSearchError');

    errorDiv.classList.add('hidden');

    try {
        const query = formData.get('query').trim();
        const availableFrom = formData.get('availableFrom');
        const availableUntil = formData.get('availableUntil');
        const availableOnly = formData.get('availableOnly') === 'on';

        if (!availableFrom || !availableUntil) {
            throw new Error('Both start and end times are required');
        }

        const startTime = new Date(availableFrom);
        const endTime = new Date(availableUntil);

        if (endTime <= startTime) {
            throw new Error('End time must be after start time');
        }

        if (startTime <= new Date()) {
            throw new Error('Start time must be in the future');
        }

        const searchParams = {
            query: query || undefined,
            availableOnly,
            availableFrom: startTime.toISOString(),
            availableUntil: endTime.toISOString()
        };

        const results = await searchResources(searchParams);

        filteredResources = results;
        searchQuery = query;

        closeModal('timeSearchModal');
        switchTab('resources');

        showMessage(`Found ${results.length} resources available from ${startTime.toLocaleString()} to ${endTime.toLocaleString()}`, 'success');

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    }
}

function showResourceAvailability(resourceId) {
    showModal('availabilityModal');
    loadResourceAvailabilityDetails(resourceId);
}

async function loadResourceAvailabilityDetails(resourceId) {
    const content = document.getElementById('availabilityContent');

    try {
        const availability = await getResourceAvailability(resourceId);
        const resource = resources.find(r => r.id === resourceId);

        content.innerHTML = `
            <div class="availability-timeline">
                <div class="availability-header">
                    <h3>📊 ${resource?.name || 'Resource'} Availability</h3>
                    <div class="availability-status">
                        <div class="availability-indicator ${availability.is_currently_available ? 'available' : 'unavailable'}">
                            ${availability.is_currently_available ? '🟢 Available Now' : '🔴 Currently Busy'}
                        </div>
                        <div class="availability-indicator">
                            ⚙️ Base Status: ${availability.base_available ? 'Enabled' : 'Disabled'}
                        </div>
                    </div>
                </div>
                
                <div class="status-item">
                    <span class="status-label">Current Time</span>
                    <span class="status-value">${new Date(availability.current_time).toLocaleString()}</span>
                </div>
                
                ${availability.reservations && availability.reservations.length > 0 ? `
                    <div class="reservation-timeline">
                        <h4>📅 Upcoming Reservations</h4>
                        ${availability.reservations.map(res => `
                            <div class="reservation-block">
                                <div class="reservation-block-time">
                                    ${new Date(res.start_time).toLocaleString()} - ${new Date(res.end_time).toLocaleString()}
                                </div>
                                <div class="reservation-block-info">
                                    ID: ${res.id} | User: ${res.user_id} | Status: ${res.status || 'active'}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : `
                    <div class="empty-state" style="padding: 20px;">
                        <div class="empty-state-icon">📅</div>
                        <h3>No upcoming reservations</h3>
                        <p>This resource is free for the next 7 days</p>
                    </div>
                `}
            </div>
        `;
    } catch (error) {
        content.innerHTML = `
            <div class="alert alert-error">
                Failed to load availability: ${error.message}
            </div>
        `;
    }
}

function showMaintenanceModal(resourceId) {
    const resource = resources.find(r => r.id === resourceId);
    if (!resource) return;

    document.getElementById('maintenanceResourceName').textContent = resource.name;
    document.getElementById('maintenanceResourceStatus').textContent =
        `Current status: ${resource.available ? 'Available' : 'Unavailable'}`;
    document.getElementById('maintenanceAction').value = resource.available ? 'disable' : 'enable';
    document.getElementById('maintenanceReason').value = '';

    document.getElementById('maintenanceModal').dataset.resourceId = resourceId;

    showModal('maintenanceModal');
}

async function applyMaintenance() {
    const modal = document.getElementById('maintenanceModal');
    const resourceId = parseInt(modal.dataset.resourceId);
    const action = document.getElementById('maintenanceAction').value;
    const reason = document.getElementById('maintenanceReason').value;
    const errorDiv = document.getElementById('maintenanceError');

    errorDiv.classList.add('hidden');

    try {
        const available = action === 'enable';
        await updateResourceAvailability(resourceId, available);

        closeModal('maintenanceModal');
        await loadResources();
        renderDashboard();

        const actionText = available ? 'enabled' : 'disabled';
        showMessage(`Resource ${actionText} successfully${reason ? ` (${reason})` : ''}`, 'success');

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    }
}

function showExtendedReservationModal(resourceId) {
    const resource = resources.find(r => r.id === resourceId);
    if (!resource) return;

    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const startDate = tomorrow.toISOString().split('T')[0];
    const startTime = '09:00';
    const endTime = '10:00';

    document.getElementById('selectedResourceInfo').innerHTML = `
        <h3>${resource.name}</h3>
        <p>Resource ID: ${resource.id}</p>
        ${resource.tags.length > 0 ? `
            <div class="tags">
                ${resource.tags.map(tag => `<span class="tag">#${tag}</span>`).join('')}
            </div>
        ` : ''}
    `;

    const form = document.getElementById('extendedReservationForm');
    form.startDate.value = startDate;
    form.endDate.value = startDate;
    form.startTime.value = startTime;
    form.endTime.value = endTime;
    form.purpose.value = '';

    form.dataset.resourceId = resourceId;

    document.getElementById('availabilityResult').classList.add('hidden');

    showModal('extendedReservationModal');
}

async function checkAvailability() {
    const form = document.getElementById('extendedReservationForm');
    const formData = new FormData(form);
    const resultDiv = document.getElementById('availabilityResult');

    try {
        const startDateTime = new Date(`${formData.get('startDate')}T${formData.get('startTime')}`);
        const endDateTime = new Date(`${formData.get('endDate')}T${formData.get('endTime')}`);

        if (endDateTime <= startDateTime) {
            throw new Error('End time must be after start time');
        }

        if (startDateTime <= new Date()) {
            throw new Error('Start time must be in the future');
        }

        const results = await searchResources({
            availableFrom: startDateTime.toISOString(),
            availableUntil: endDateTime.toISOString(),
            availableOnly: true
        });

        const resourceId = parseInt(form.dataset.resourceId);
        const isAvailable = results.some(r => r.id === resourceId);

        resultDiv.className = `availability-result ${isAvailable ? 'available' : 'unavailable'}`;
        resultDiv.innerHTML = isAvailable
            ? `✅ Resource is available for the selected time period`
            : `❌ Resource is not available for the selected time period`;
        resultDiv.classList.remove('hidden');

    } catch (error) {
        resultDiv.className = 'availability-result unavailable';
        resultDiv.innerHTML = `❌ ${error.message}`;
        resultDiv.classList.remove('hidden');
    }
}

async function handleExtendedReservation(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const errorDiv = document.getElementById('extendedReservationError');
    const submitBtn = form.querySelector('button[type="submit"]');

    errorDiv.classList.add('hidden');

    try {
        const resourceId = parseInt(form.dataset.resourceId);
        const startDateTime = new Date(`${formData.get('startDate')}T${formData.get('startTime')}`);
        const endDateTime = new Date(`${formData.get('endDate')}T${formData.get('endTime')}`);

        if (endDateTime <= startDateTime) {
            throw new Error('End time must be after start time');
        }

        if (startDateTime <= new Date()) {
            throw new Error('Start time must be in the future');
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Creating...';

        await apiCall('/reservations', {
            method: 'POST',
            body: JSON.stringify({
                resource_id: resourceId,
                start_time: startDateTime.toISOString(),
                end_time: endDateTime.toISOString()
            })
        });

        closeModal('extendedReservationModal');
        await loadReservations();
        renderDashboard();
        showMessage('Reservation created successfully!', 'success');

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Reservation';
    }
}

async function cancelReservation(reservationId) {
    if (!confirm('Are you sure you want to cancel this reservation?')) {
        return;
    }

    try {
        await apiCall(`/reservations/${reservationId}/cancel`, {
            method: 'POST',
            body: JSON.stringify({ reason: 'Cancelled by user' })
        });

        await loadReservations();
        renderDashboard();
        showMessage('Reservation cancelled successfully', 'success');
    } catch (error) {
        showMessage('Failed to cancel reservation: ' + error.message, 'error');
    }
}

function showReservationHistory(reservationId) {
    showModal('availabilityModal');
    loadReservationHistoryDetails(reservationId);
}

async function loadReservationHistoryDetails(reservationId) {
    const content = document.getElementById('availabilityContent');

    content.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Loading reservation history...</p>
        </div>
    `;

    try {
        const history = await getReservationHistory(reservationId);
        const reservation = reservations.find(r => r.id === reservationId);

        content.innerHTML = `
            <div style="margin-bottom: 20px;">
                <h3>📋 Reservation History</h3>
                ${reservation ? `
                    <div style="background: #f8fafc; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                        <h4>${reservation.resource.name}</h4>
                        <p>ID: ${reservation.id} | ${new Date(reservation.start_time).toLocaleString()} - ${new Date(reservation.end_time).toLocaleString()}</p>
                    </div>
                ` : ''}
            </div>
            
            ${history.length > 0 ? `
                <div class="history-timeline">
                    ${history.map(entry => {
            const timestamp = new Date(entry.timestamp);
            const actionIcons = {
                'created': '✅',
                'cancelled': '❌',
                'updated': '📝',
                'expired': '⏰'
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
                                    <p class="history-details">${entry.details}</p>
                                ` : ''}
                            </div>
                        `;
        }).join('')}
                </div>
            ` : `
                <div class="empty-state">
                    <div class="empty-state-icon">📋</div>
                    <h3>No history available</h3>
                    <p>No audit trail found for this reservation</p>
                </div>
            `}
        `;
    } catch (error) {
        content.innerHTML = `
            <div class="alert alert-error">
                Failed to load reservation history: ${error.message}
            </div>
        `;
    }
}
function showCreateResourceModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Create New Resource</h2>
                <button class="close-btn" onclick="this.closest('.modal').remove()">&times;</button>
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
                    <label class="checkbox-label">
                        <input type="checkbox" name="available" checked>
                        <span>Available for booking</span>
                    </label>
                </div>
                
                <div id="createResourceError" class="alert alert-error hidden"></div>
                
                <div class="modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button type="submit" class="btn btn-success">Create Resource</button>
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
    const errorDiv = form.querySelector('#createResourceError');
    const submitBtn = form.querySelector('button[type="submit"]');

    errorDiv.classList.add('hidden');
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

        form.closest('.modal').remove();
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

function showUploadCSVModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Upload Resources from CSV</h2>
                <button class="close-btn" onclick="this.closest('.modal').remove()">&times;</button>
            </div>
            
            <div class="alert alert-info">
                <strong>CSV Format:</strong> name,tags,available<br>
                <small>Example: "Conference Room A","meeting,large",true</small>
            </div>
            
            <form onsubmit="handleUploadCSV(event)">
                <div class="form-group">
                    <label class="form-label">Select CSV File</label>
                    <input type="file" class="form-input" name="csvFile" accept=".csv" required>
                </div>
                
                <div id="uploadCSVError" class="alert alert-error hidden"></div>
                
                <div class="modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Upload Resources</button>
                </div>
            </form>
        </div>
    `;
    document.body.appendChild(modal);
}

async function handleUploadCSV(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const file = formData.get('csvFile');
    const errorDiv = form.querySelector('#uploadCSVError');
    const submitBtn = form.querySelector('button[type="submit"]');

    if (!file) {
        errorDiv.textContent = 'Please select a CSV file';
        errorDiv.classList.remove('hidden');
        return;
    }

    errorDiv.classList.add('hidden');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Uploading...';

    try {
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

        form.closest('.modal').remove();
        await loadResources();
        renderDashboard();

        let message = `Successfully created ${result.created_count} resources`;
        if (result.errors && result.errors.length > 0) {
            message += ` (${result.errors.length} errors)`;
        }
        showMessage(message, 'success');

    } catch (error) {
        errorDiv.textContent = error.message;
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
                <button class="close-btn" onclick="this.closest('.modal').remove()">&times;</button>
            </div>
            
            <form onsubmit="handleAdvancedSearch(event)">
                <div class="form-group">
                    <label class="form-label">Search Query</label>
                    <input type="text" class="form-input" name="query" placeholder="e.g., meeting, projector, large">
                </div>
                
                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" name="availableOnly" checked>
                        <span>Show only available resources</span>
                    </label>
                </div>
                
                <div id="advancedSearchError" class="alert alert-error hidden"></div>
                
                <div class="modal-actions">
                    <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
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
    const errorDiv = form.querySelector('#advancedSearchError');
    const submitBtn = form.querySelector('button[type="submit"]');

    errorDiv.classList.add('hidden');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Searching...';

    try {
        const query = formData.get('query').trim();
        const availableOnly = formData.get('availableOnly') === 'on';

        const searchParams = {
            query: query || undefined,
            availableOnly
        };

        const results = await searchResources(searchParams);

        filteredResources = results;
        searchQuery = query;

        form.closest('.modal').remove();
        switchTab('resources');

        showMessage(`Found ${results.length} resources matching your criteria`, 'success');

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Search Resources';
    }
}

function showMessage(message, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `alert alert-${type}`;
    messageDiv.textContent = message;
    messageDiv.style.position = 'fixed';
    messageDiv.style.top = '20px';
    messageDiv.style.right = '20px';
    messageDiv.style.zIndex = '1001';
    messageDiv.style.minWidth = '300px';
    messageDiv.style.maxWidth = '500px';
    messageDiv.style.wordWrap = 'break-word';

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