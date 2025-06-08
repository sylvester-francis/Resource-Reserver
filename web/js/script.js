// Configuration
const API_BASE_URL = 'http://localhost:8000';
        
// Global state
let currentUser = JSON.parse(localStorage.getItem('user')) || null;
let authToken = localStorage.getItem('auth_token') || null;
let currentView = 'login';
let activeTab = 'resources';
let resources = [];
let reservations = [];
let filteredResources = [];
let searchQuery = '';
let currentFilter = 'all';
let systemStatus = null;

// Pagination state
let currentPage = 1;
let itemsPerPage = 10;
let totalPages = 1;

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
                errorMessage = errorText || `HTTP ${response.status}`;
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
        showNotification('Failed to load resources: ' + error.message, 'error');
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

async function loadReservations(includeCancelled = false) {
    try {
        const params = new URLSearchParams();
        if (includeCancelled) params.append('include_cancelled', 'true');
        const endpoint = params.toString() ? `/reservations/my?${params}` : '/reservations/my';
        reservations = await apiCall(endpoint);
    } catch (error) {
        console.error('Failed to load reservations:', error);
        showNotification('Failed to load reservations: ' + error.message, 'error');
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

async function loadSystemStatus() {
    try {
        systemStatus = await apiCall('/health');
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
    
    // Update pagination
    totalPages = Math.ceil(filteredResources.length / itemsPerPage);
    if (currentPage > totalPages && totalPages > 0) {
        currentPage = totalPages;
    }
    if (currentPage < 1) {
        currentPage = 1;
    }
}

function getPaginatedResources() {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredResources.slice(startIndex, endIndex);
}

function changePage(page) {
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        const tabContent = document.getElementById('tabContent');
        tabContent.innerHTML = renderTabContent();
    }
}

function changeItemsPerPage(items) {
    itemsPerPage = parseInt(items);
    currentPage = 1;
    filterResources();
    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = renderTabContent();
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
        showNotification('Failed to load dashboard data', 'error');
    }
}

// Render Functions
function renderLogin() {
    const app = document.getElementById('app');
    app.innerHTML = `
        <div class="login-container">
            <div class="login-card">
                <div class="login-header">
                    <h1><i class="fas fa-calendar-alt"></i> Resource Reservation</h1>
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
                    
                    <div class="form-group hidden" id="confirmPasswordGroup">
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
        <header class="header">
            <div class="container">
                <div class="header-content">
                    <div class="logo">
                        <i class="fas fa-calendar-alt"></i>
                        Resource Reservation System
                    </div>
                    <div class="user-menu">
                        <div class="user-info">
                            <i class="fas fa-user"></i>
                            Welcome, ${currentUser.username}
                        </div>
                        <button class="btn btn-outline btn-sm" onclick="showSystemStatus()">
                            <i class="fas fa-chart-line"></i> Status
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="logout()">
                            <i class="fas fa-sign-out-alt"></i> Sign Out
                        </button>
                    </div>
                </div>
            </div>
        </header>

        <nav class="nav-tabs">
            <div class="container">
                <div class="nav-content">
                    <a href="#" class="nav-tab ${activeTab === 'resources' ? 'active' : ''}" onclick="switchTab(event, 'resources')">
                        <i class="fas fa-cube"></i> Resources
                    </a>
                    <a href="#" class="nav-tab ${activeTab === 'reservations' ? 'active' : ''}" onclick="switchTab(event, 'reservations')">
                        <i class="fas fa-calendar-check"></i> My Reservations
                    </a>
                    <a href="#" class="nav-tab ${activeTab === 'upcoming' ? 'active' : ''}" onclick="switchTab(event, 'upcoming')">
                        <i class="fas fa-clock"></i> Upcoming
                    </a>
                </div>
            </div>
        </nav>

        <main class="container">
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

            <div id="tabContent">
                ${renderTabContent()}
            </div>
        </main>
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
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">
                    <i class="fas fa-cube"></i> Resources
                </h2>
            </div>
            
            <div class="flex gap-2 mb-4">
                <button class="btn btn-outline btn-sm" onclick="showTimeSearchModal()">
                    <i class="fas fa-search"></i> Time Search
                </button>
                <button class="btn btn-success btn-sm" onclick="showCreateResourceModal()">
                    <i class="fas fa-plus"></i> Add Resource
                </button>
                <button class="btn btn-primary btn-sm" onclick="showUploadCsvModal()">
                    <i class="fas fa-upload"></i> Upload CSV
                </button>
                <button class="btn btn-outline btn-sm" onclick="refreshResources()">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
            </div>

            <div class="search-container">
                <input type="text" class="form-input search-input" placeholder="Search resources..." 
                       value="${searchQuery}" onkeyup="handleSearch(this.value)">
                <i class="fas fa-search search-icon"></i>
            </div>

            <div class="filters mb-4">
                <div class="filter-chip ${currentFilter === 'all' ? 'active' : ''}" onclick="handleFilterChange('all')">
                    <i class="fas fa-list"></i> All
                </div>
                <div class="filter-chip ${currentFilter === 'available' ? 'active' : ''}" onclick="handleFilterChange('available')">
                    <i class="fas fa-check-circle"></i> Available
                </div>
                <div class="filter-chip ${currentFilter === 'unavailable' ? 'active' : ''}" onclick="handleFilterChange('unavailable')">
                    <i class="fas fa-times-circle"></i> Unavailable
                </div>
            </div>

            <div class="mb-4 flex justify-between items-center">
                <span>Showing ${getPaginatedResources().length} of ${filteredResources.length} resources</span>
                <div class="flex items-center gap-2">
                    <label style="font-size: 0.875rem; color: var(--text-secondary);">Show:</label>
                    <select class="pagination-select" onchange="changeItemsPerPage(this.value)" value="${itemsPerPage}">
                        <option value="5" ${itemsPerPage === 5 ? 'selected' : ''}>5</option>
                        <option value="10" ${itemsPerPage === 10 ? 'selected' : ''}>10</option>
                        <option value="25" ${itemsPerPage === 25 ? 'selected' : ''}>25</option>
                        <option value="50" ${itemsPerPage === 50 ? 'selected' : ''}>50</option>
                    </select>
                    <span style="font-size: 0.875rem; color: var(--text-secondary);">per page</span>
                </div>
            </div>

            ${filteredResources.length === 0 ? `
                <div class="empty-state">
                    <i class="fas fa-cube"></i>
                    <h3>No resources found</h3>
                    <p>${searchQuery || currentFilter !== 'all' ? 'Try adjusting your search or filters' : 'Get started by adding your first resource'}</p>
                    <button class="btn btn-primary" onclick="showCreateResourceModal()">
                        Add Your First Resource
                    </button>
                </div>
            ` : `
                <div class="resources-list">
                    ${getPaginatedResources().map(resource => renderResourceListItem(resource)).join('')}
                </div>

                ${totalPages > 1 ? renderPagination() : ''}
            `}
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
                    <div class="resource-list-id">#${resource.id.toString().padStart(3, '0')}</div>
                </div>
                
                <div class="resource-list-meta">
                    <span class="resource-list-status ${resource.available ? 'available' : 'unavailable'}">
                        <i class="fas fa-${resource.available ? 'check' : 'times'}-circle"></i>
                        ${resource.available ? 'Available' : 'Unavailable'}
                    </span>
                    
                    ${resource.tags.length > 0 ? `
                        <div class="resource-list-tags">
                            ${resource.tags.slice(0, 4).map(tag => `<span class="resource-tag">${tag}</span>`).join('')}
                            ${resource.tags.length > 4 ? `<span class="resource-tag" style="background: var(--warning-color); color: white;">+${resource.tags.length - 4}</span>` : ''}
                        </div>
                    ` : `
                        <div class="resource-list-tags">
                            <span class="resource-tag" style="opacity: 0.5;">No tags</span>
                        </div>
                    `}
                </div>
            </div>
            
            <div class="resource-list-actions">
                <button class="btn-list-reserve" 
                        ${!resource.available ? 'disabled' : ''} 
                        onclick="showReservationModal(${resource.id})">
                    <i class="fas fa-calendar-plus"></i>
                    ${resource.available ? 'Reserve' : 'Unavailable'}
                </button>
                <button class="btn btn-outline btn-sm" onclick="showResourceAvailability(${resource.id})">
                    <i class="fas fa-calendar-alt"></i>
                </button>
            </div>
        </div>
    `;
}

function renderPagination() {
    const pageNumbers = [];
    const maxVisiblePages = 5;
    
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage < maxVisiblePages - 1) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        pageNumbers.push(i);
    }

    return `
        <div class="pagination-container">
            <div class="pagination-info">
                <span>
                    Showing ${(currentPage - 1) * itemsPerPage + 1} to ${Math.min(currentPage * itemsPerPage, filteredResources.length)} 
                    of ${filteredResources.length} resources
                </span>
            </div>

            <div class="pagination-controls">
                <div class="pagination-nav">
                    <button class="pagination-btn" 
                            onclick="changePage(1)" 
                            ${currentPage === 1 ? 'disabled' : ''}>
                        <i class="fas fa-angle-double-left"></i>
                    </button>
                    <button class="pagination-btn" 
                            onclick="changePage(${currentPage - 1})" 
                            ${currentPage === 1 ? 'disabled' : ''}>
                        <i class="fas fa-angle-left"></i>
                    </button>

                    ${startPage > 1 ? `
                        <button class="pagination-btn" onclick="changePage(1)">1</button>
                        ${startPage > 2 ? '<span style="padding: 0 var(--space-2);">...</span>' : ''}
                    ` : ''}

                    ${pageNumbers.map(page => `
                        <button class="pagination-btn ${page === currentPage ? 'active' : ''}" 
                                onclick="changePage(${page})">
                            ${page}
                        </button>
                    `).join('')}

                    ${endPage < totalPages ? `
                        ${endPage < totalPages - 1 ? '<span style="padding: 0 var(--space-2);">...</span>' : ''}
                        <button class="pagination-btn" onclick="changePage(${totalPages})">${totalPages}</button>
                    ` : ''}

                    <button class="pagination-btn" 
                            onclick="changePage(${currentPage + 1})" 
                            ${currentPage === totalPages ? 'disabled' : ''}>
                        <i class="fas fa-angle-right"></i>
                    </button>
                    <button class="pagination-btn" 
                            onclick="changePage(${totalPages})" 
                            ${currentPage === totalPages ? 'disabled' : ''}>
                        <i class="fas fa-angle-double-right"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

function renderReservationsTab() {
    return `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">
                    <i class="fas fa-calendar-check"></i> My Reservations
                </h2>
            </div>
            
            <div class="flex gap-2 mb-4">
                <button class="btn btn-outline btn-sm" onclick="loadReservations(true); renderDashboard();">
                    <i class="fas fa-list"></i> Include Cancelled
                </button>
                <button class="btn btn-outline btn-sm" onclick="loadReservations(); renderDashboard();">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
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
                                <i class="fas fa-clock"></i>
                                ${startTime.toLocaleDateString()} • ${startTime.toLocaleTimeString()} - ${endTime.toLocaleTimeString()}
                            </div>
                            <div class="reservation-badges">
                                <span class="resource-status ${reservation.status === 'active' ? 'available' : 'unavailable'}">
                                    ${reservation.status.charAt(0).toUpperCase() + reservation.status.slice(1)}
                                </span>
                                ${isUpcoming ? '<span class="resource-status available">Upcoming</span>' : ''}
                            </div>
                        </div>
                        
                        <div class="reservation-actions">
                            <button class="btn btn-outline btn-sm" onclick="showReservationHistory(${reservation.id})">
                                <i class="fas fa-history"></i> History
                            </button>
                            ${reservation.status === 'active' && isUpcoming ? `
                                <button class="btn btn-danger btn-sm" onclick="cancelReservation(${reservation.id})">
                                    <i class="fas fa-times"></i> Cancel
                                </button>
                            ` : ''}
                        </div>
                    </div>
                `;
            }).join('')}

            ${reservations.length === 0 ? `
                <div class="empty-state">
                    <i class="fas fa-calendar-check"></i>
                    <h3>No reservations found</h3>
                    <p>Once you make a reservation, you'll see it here</p>
                    <button class="btn btn-primary" onclick="switchTab(event, 'resources')">
                        Make a Reservation
                    </button>
                </div>
            ` : ''}
        </div>
    `;
}

function renderUpcomingTab() {
    const upcomingReservations = getUpcomingReservations();

    return `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">
                    <i class="fas fa-clock"></i> Upcoming Reservations
                </h2>
            </div>
            
            <div class="flex gap-2 mb-4">
                <button class="btn btn-outline btn-sm" onclick="loadReservations(); renderDashboard();">
                    <i class="fas fa-sync-alt"></i> Refresh
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
                                <i class="fas fa-clock"></i>
                                ${startTime.toLocaleDateString()} • ${startTime.toLocaleTimeString()} - ${endTime.toLocaleTimeString()}
                            </div>
                            <div style="color: var(--primary-color); font-size: 0.875rem; margin-top: var(--space-1);">
                                <i class="fas fa-hourglass-half"></i> ${timeText}
                            </div>
                        </div>
                        <div class="reservation-actions">
                            <button class="btn btn-outline btn-sm" onclick="showReservationHistory(${reservation.id})">
                                <i class="fas fa-history"></i> History
                            </button>
                            <button class="btn btn-danger btn-sm" onclick="cancelReservation(${reservation.id})">
                                <i class="fas fa-times"></i> Cancel
                            </button>
                        </div>
                    </div>
                `;
            }).join('')}

            ${upcomingReservations.length === 0 ? `
                <div class="empty-state">
                    <i class="fas fa-clock"></i>
                    <h3>No upcoming reservations</h3>
                    <p>Your upcoming reservations will appear here</p>
                    <button class="btn btn-primary" onclick="switchTab(event, 'resources')">
                        Make a Reservation
                    </button>
                </div>
            ` : ''}
        </div>
    `;
}

function renderAnalyticsTab() {
    const stats = calculateDetailedStats();

    return `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">
                    <i class="fas fa-chart-bar"></i> System Analytics
                </h2>
                <button class="btn btn-outline btn-sm" onclick="loadDashboard();">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
            </div>

            <div class="form-grid">
                <div class="card">
                    <h3><i class="fas fa-cube"></i> Resource Statistics</h3>
                    <div class="flex justify-between items-center mb-2">
                        <span>Total Resources</span>
                        <strong>${stats.totalResources}</strong>
                    </div>
                    <div class="flex justify-between items-center mb-2">
                        <span>Available Now</span>
                        <strong style="color: var(--success-color);">${stats.availableResources}</strong>
                    </div>
                    <div class="flex justify-between items-center mb-2">
                        <span>Unavailable</span>
                        <strong style="color: var(--warning-color);">${stats.unavailableResources}</strong>
                    </div>
                    <div class="flex justify-between items-center">
                        <span>Utilization Rate</span>
                        <strong>${stats.utilizationRate}%</strong>
                    </div>
                </div>

                <div class="card">
                    <h3><i class="fas fa-calendar-check"></i> Reservation Statistics</h3>
                    <div class="flex justify-between items-center mb-2">
                        <span>Active Reservations</span>
                        <strong>${stats.activeReservations}</strong>
                    </div>
                    <div class="flex justify-between items-center mb-2">
                        <span>Upcoming Reservations</span>
                        <strong>${stats.upcomingReservations}</strong>
                    </div>
                    <div class="flex justify-between items-center mb-2">
                        <span>Cancelled Reservations</span>
                        <strong style="color: var(--warning-color);">${stats.cancelledReservations}</strong>
                    </div>
                    <div class="flex justify-between items-center">
                        <span>Total Reservations</span>
                        <strong>${stats.totalReservations}</strong>
                    </div>
                </div>

                <div class="card">
                    <h3><i class="fas fa-heart"></i> System Health</h3>
                    <div class="flex justify-between items-center mb-2">
                        <span>API Status</span>
                        <strong style="color: ${systemStatus?.status === 'healthy' ? 'var(--success-color)' : 'var(--danger-color)'};">
                            ${systemStatus?.status === 'healthy' ? '✓ Healthy' : '✗ Error'}
                        </strong>
                    </div>
                    <div class="flex justify-between items-center mb-2">
                        <span>Background Tasks</span>
                        <strong style="color: var(--success-color);">
                            ${systemStatus?.background_tasks?.cleanup_task === 'running' ? '✓ Running' : '⚠ Stopped'}
                        </strong>
                    </div>
                    <div class="flex justify-between items-center">
                        <span>Last Updated</span>
                        <strong>
                            ${systemStatus?.timestamp ? new Date(systemStatus.timestamp).toLocaleTimeString() : 'Unknown'}
                        </strong>
                    </div>
                </div>
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
        confirmGroup.classList.remove('hidden');
        submitBtn.textContent = 'Register';
    } else {
        confirmGroup.classList.add('hidden');
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

    if (!isLogin && password !== confirmPassword) {
        errorDiv.textContent = 'Passwords do not match';
        errorDiv.classList.remove('hidden');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

    try {
        if (isLogin) {
            await login(username, password);
            currentView = 'dashboard';
            await loadDashboard();
        } else {
            await register(username, password);
            switchAuthTab({ target: document.querySelector('.auth-tab') }, 'login');
            form.reset();
            showNotification('Registration successful! Please sign in.', 'success');
        }
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    } finally {
        if (isLogin || document.querySelector('.auth-tab.active').textContent === 'Sign In') {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Sign In';
        } else {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Register';
        }
    }
}

function switchTab(event, tab) {
    event.preventDefault();
    activeTab = tab;
    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = renderTabContent();
    
    // Update active tab styling
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
}

function handleSearch(value) {
    searchQuery = value;
    currentPage = 1; // Reset to first page when searching
    filterResources();
    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = renderTabContent();
}

function handleFilterChange(filter) {
    currentFilter = filter;
    currentPage = 1; // Reset to first page when filtering
    filterResources();
    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = renderTabContent();
}

async function refreshResources() {
    await loadResources();
    const tabContent = document.getElementById('tabContent');
    tabContent.innerHTML = renderTabContent();
    showNotification('Resources refreshed', 'success');
}

// Modal Functions
function showModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

function showReservationModal(resourceId) {
    const resource = resources.find(r => r.id === resourceId);
    if (!resource) return;

    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    const form = document.getElementById('reservationForm');
    form.startDate.value = tomorrow.toISOString().split('T')[0];
    form.endDate.value = tomorrow.toISOString().split('T')[0];
    form.startTime.value = '09:00';
    form.endTime.value = '10:00';
    form.dataset.resourceId = resourceId;

    document.getElementById('selectedResourceInfo').innerHTML = `
        <strong>${resource.name}</strong> (ID: ${resource.id})
        ${resource.tags.length > 0 ? `<br>Tags: ${resource.tags.join(', ')}` : ''}
    `;
    document.getElementById('selectedResourceInfo').classList.remove('hidden');

    showModal('reservationModal');
}

async function handleCreateReservation(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const errorDiv = document.getElementById('reservationError');
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
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';

        await apiCall('/reservations', {
            method: 'POST',
            body: JSON.stringify({
                resource_id: resourceId,
                start_time: startDateTime.toISOString(),
                end_time: endDateTime.toISOString()
            })
        });

        closeModal('reservationModal');
        await loadReservations();
        renderDashboard();
        showNotification('Reservation created successfully!', 'success');

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Reservation';
    }
}

function showTimeSearchModal() {
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const form = document.getElementById('timeSearchForm');
    form.availableFrom.value = tomorrow.toISOString().slice(0, 16);
    form.availableUntil.value = new Date(tomorrow.getTime() + 2 * 60 * 60 * 1000).toISOString().slice(0, 16);

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
        activeTab = 'resources';
        renderDashboard();

        showNotification(`Found ${results.length} resources available from ${startTime.toLocaleString()} to ${endTime.toLocaleString()}`, 'success');

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    }
}

function showCreateResourceModal() {
    showModal('createResourceModal');
}

async function handleCreateResource(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const errorDiv = document.getElementById('createResourceError');
    const submitBtn = form.querySelector('button[type="submit"]');

    errorDiv.classList.add('hidden');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating...';

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

        closeModal('createResourceModal');
        await loadResources();
        renderDashboard();
        showNotification('Resource created successfully', 'success');
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Resource';
    }
}

function showUploadCsvModal() {
    showModal('uploadCsvModal');
}

async function handleUploadCsv(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const file = formData.get('csvFile');
    const errorDiv = document.getElementById('uploadCsvError');
    const submitBtn = form.querySelector('button[type="submit"]');

    if (!file) {
        errorDiv.textContent = 'Please select a CSV file';
        errorDiv.classList.remove('hidden');
        return;
    }

    errorDiv.classList.add('hidden');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';

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

        closeModal('uploadCsvModal');
        await loadResources();
        renderDashboard();

        let message = `Successfully created ${result.created_count} resources`;
        if (result.errors && result.errors.length > 0) {
            message += ` (${result.errors.length} errors)`;
        }
        showNotification(message, 'success');

    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Upload';
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
            <div class="mb-4">
                <h3><i class="fas fa-calendar-alt"></i> ${resource?.name || 'Resource'} Availability</h3>
                <div class="flex justify-between items-center mb-4">
                    <div class="resource-status ${availability.is_currently_available ? 'available' : 'unavailable'}">
                        <i class="fas fa-${availability.is_currently_available ? 'check' : 'times'}-circle"></i>
                        ${availability.is_currently_available ? 'Available Now' : 'Currently Busy'}
                    </div>
                    <div>
                        <i class="fas fa-cog"></i> Base Status: ${availability.base_available ? 'Enabled' : 'Disabled'}
                    </div>
                </div>
                
                <div class="flex justify-between items-center mb-4">
                    <span>Current Time</span>
                    <strong>${new Date(availability.current_time).toLocaleString()}</strong>
                </div>
                
                ${availability.reservations && availability.reservations.length > 0 ? `
                    <h4><i class="fas fa-calendar-check"></i> Upcoming Reservations</h4>
                    ${availability.reservations.map(res => `
                        <div class="alert alert-warning mb-2">
                            <strong>${new Date(res.start_time).toLocaleString()} - ${new Date(res.end_time).toLocaleString()}</strong><br>
                            <small>ID: ${res.id} | User: ${res.user_id} | Status: ${res.status || 'active'}</small>
                        </div>
                    `).join('')}
                ` : `
                    <div class="empty-state">
                        <i class="fas fa-calendar-check"></i>
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
        showNotification('Reservation cancelled successfully', 'success');
    } catch (error) {
        showNotification('Failed to cancel reservation: ' + error.message, 'error');
    }
}

function showReservationHistory(reservationId) {
    showModal('availabilityModal');
    loadReservationHistoryDetails(reservationId);
}

async function loadReservationHistoryDetails(reservationId) {
    const content = document.getElementById('availabilityContent');

    content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const history = await getReservationHistory(reservationId);
        const reservation = reservations.find(r => r.id === reservationId);

        content.innerHTML = `
            <div class="mb-4">
                <h3><i class="fas fa-history"></i> Reservation History</h3>
                ${reservation ? `
                    <div class="alert alert-info mb-4">
                        <strong>${reservation.resource.name}</strong><br>
                        ID: ${reservation.id} | ${new Date(reservation.start_time).toLocaleString()} - ${new Date(reservation.end_time).toLocaleString()}
                    </div>
                ` : ''}
            </div>
            
            ${history.length > 0 ? `
                <div class="space-y-3">
                    ${history.map(entry => {
                        const timestamp = new Date(entry.timestamp);
                        const actionIcons = {
                            'created': 'plus-circle',
                            'cancelled': 'times-circle',
                            'updated': 'edit',
                            'expired': 'clock'
                        };
                        const actionColors = {
                            'created': 'var(--success-color)',
                            'cancelled': 'var(--danger-color)',
                            'updated': 'var(--warning-color)',
                            'expired': 'var(--secondary-color)'
                        };

                        return `
                            <div class="card" style="padding: var(--space-3); border-left: 3px solid ${actionColors[entry.action] || 'var(--border-color)'};">
                                <div class="flex justify-between items-center mb-2">
                                    <div style="color: ${actionColors[entry.action] || 'var(--text-primary)'}; font-weight: 600;">
                                        <i class="fas fa-${actionIcons[entry.action] || 'info-circle'}"></i>
                                        ${entry.action.charAt(0).toUpperCase() + entry.action.slice(1)}
                                    </div>
                                    <small style="color: var(--text-secondary);">
                                        ${timestamp.toLocaleDateString()} at ${timestamp.toLocaleTimeString()}
                                    </small>
                                </div>
                                ${entry.details ? `<p style="margin: 0; color: var(--text-secondary); font-size: 0.875rem;">${entry.details}</p>` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            ` : `
                <div class="empty-state">
                    <i class="fas fa-history"></i>
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

function showSystemStatus() {
    showModal('availabilityModal');
    loadSystemStatusDetails();
}

async function loadSystemStatusDetails() {
    const content = document.getElementById('availabilityContent');

    try {
        await loadSystemStatus();
        const summary = await apiCall('/resources/availability/summary');

        content.innerHTML = `
            <div class="mb-4">
                <h3><i class="fas fa-heartbeat"></i> System Status</h3>
            </div>

            <div class="form-grid">
                <div class="card">
                    <h4><i class="fas fa-server"></i> API Health</h4>
                    <div class="flex justify-between items-center mb-2">
                        <span>Status</span>
                        <strong style="color: ${systemStatus?.status === 'healthy' ? 'var(--success-color)' : 'var(--danger-color)'};">
                            ${systemStatus?.status || 'Unknown'}
                        </strong>
                    </div>
                    <div class="flex justify-between items-center">
                        <span>Timestamp</span>
                        <strong>
                            ${systemStatus?.timestamp ? new Date(systemStatus.timestamp).toLocaleString() : 'Unknown'}
                        </strong>
                    </div>
                </div>

                <div class="card">
                    <h4><i class="fas fa-tasks"></i> Background Tasks</h4>
                    ${systemStatus?.background_tasks ? Object.entries(systemStatus.background_tasks).map(([name, status]) => `
                        <div class="flex justify-between items-center mb-2">
                            <span>${name.replace('_', ' ').toUpperCase()}</span>
                            <strong style="color: ${status === 'running' ? 'var(--success-color)' : status === 'failed' ? 'var(--danger-color)' : 'var(--warning-color)'};">
                                ${status}
                            </strong>
                        </div>
                    `).join('') : '<p>No background task information available</p>'}
                </div>

                ${summary ? `
                    <div class="card">
                        <h4><i class="fas fa-chart-pie"></i> Resource Summary</h4>
                        <div class="flex justify-between items-center mb-2">
                            <span>Total Resources</span>
                            <strong>${summary.total_resources}</strong>
                        </div>
                        <div class="flex justify-between items-center mb-2">
                            <span>Available Now</span>
                            <strong style="color: var(--success-color);">${summary.available_now}</strong>
                        </div>
                        <div class="flex justify-between items-center mb-2">
                            <span>Unavailable</span>
                            <strong style="color: var(--warning-color);">${summary.unavailable_now}</strong>
                        </div>
                        <div class="flex justify-between items-center mb-2">
                            <span>Currently In Use</span>
                            <strong style="color: var(--primary-color);">${summary.currently_in_use}</strong>
                        </div>
                        <div class="flex justify-between items-center">
                            <span>Last Updated</span>
                            <strong>
                                ${new Date(summary.timestamp).toLocaleString()}
                            </strong>
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

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1001;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
    notification.innerHTML = `
        <div class="flex items-center gap-2">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'times-circle' : 'info-circle'}"></i>
            ${message}
        </div>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.add('hidden');
    }
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    .space-y-3 > * + * {
        margin-top: var(--space-3);
    }
`;
document.head.appendChild(style);

// Initialize the application
init();
