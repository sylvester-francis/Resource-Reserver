// API wrapper with session handling
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, options);
        
        // Check if response indicates session expiration (401 or redirect to login)
        if (response.status === 401 || response.url.includes('/login')) {
            // Session expired, redirect to login
            window.location.href = '/login?error=' + encodeURIComponent('Your session has expired. Please log in again.');
            return;
        }
        
        return response;
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Alpine.js Dashboard App
function dashboardApp() {
    return {
        // State
        activeTab: 'resources',
        resources: [],
        reservations: [],
        filteredResources: [],
        searchQuery: '',
        currentFilter: 'all',
        loading: false,
        
        // Modals
        showCreateResource: false,
        showReservation: false,
        showUpload: false,
        showAvailability: false,
        showHistory: false,
        
        // Forms
        newResource: {
            name: '',
            tags: '',
            available: true
        },
        newReservation: {
            startDate: '',
            startTime: '',
            endDate: '',
            endTime: ''
        },
        selectedResource: null,
        csvFile: null,
        availabilityData: null,
        selectedReservation: null,
        reservationHistory: null,
        
        // Errors
        resourceError: '',
        reservationError: '',
        uploadError: '',

        // Initialize
        init() {
            this.resources = window.initialResources || [];
            this.reservations = window.initialReservations || [];
            this.filterResources();
            
            // Set default dates for reservation form
            const now = new Date();
            const tomorrow = new Date(now);
            tomorrow.setDate(tomorrow.getDate() + 1);
            
            this.newReservation.startDate = tomorrow.toISOString().split('T')[0];
            this.newReservation.endDate = tomorrow.toISOString().split('T')[0];
            this.newReservation.startTime = '09:00';
            this.newReservation.endTime = '10:00';
        },

        // Computed properties
        get upcomingReservations() {
            return this.reservations.filter(r => 
                r.status === 'active' && new Date(r.start_time) > new Date()
            ).sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
        },

        // Filter and search using backend
        async filterResources() {
            try {
                const params = {};
                
                // Add search query if present
                if (this.searchQuery) {
                    params.q = this.searchQuery;
                }
                
                // Apply availability filter
                if (this.currentFilter === 'available') {
                    params.available_only = true;
                } else if (this.currentFilter === 'unavailable') {
                    params.available_only = false;
                } else {
                    // For 'all', we still want to use search if there's a query
                    if (this.searchQuery) {
                        params.available_only = false; // Show all when searching
                    } else {
                        // No search, just show local resources
                        this.filteredResources = [...this.resources];
                        return;
                    }
                }
                
                // Only call backend if we have search query or specific filter
                if (this.searchQuery || this.currentFilter !== 'all') {
                    const response = await apiCall('/api/resources/search?' + new URLSearchParams(params));
                    const result = await response.json();
                    
                    if (result.success) {
                        this.filteredResources = result.data;
                    } else {
                        console.error('Search failed:', result.error);
                        // Fallback to local filtering
                        this.localFilterResources();
                    }
                } else {
                    this.filteredResources = [...this.resources];
                }
            } catch (error) {
                console.error('Search error:', error);
                // Fallback to local filtering
                this.localFilterResources();
            }
        },

        // Fallback local filtering method
        localFilterResources() {
            let filtered = [...this.resources];
            
            // Apply filter
            if (this.currentFilter === 'available') {
                filtered = filtered.filter(r => r.available);
            } else if (this.currentFilter === 'unavailable') {
                filtered = filtered.filter(r => !r.available);
            }
            
            // Apply search
            if (this.searchQuery) {
                const query = this.searchQuery.toLowerCase();
                filtered = filtered.filter(r => 
                    r.name.toLowerCase().includes(query) ||
                    r.tags.some(tag => tag.toLowerCase().includes(query))
                );
            }
            
            this.filteredResources = filtered;
        },

        setFilter(filter) {
            this.currentFilter = filter;
            this.filterResources();
        },

        // Modal functions
        showCreateResourceModal() {
            this.newResource = { name: '', tags: '', available: true };
            this.resourceError = '';
            this.showCreateResource = true;
        },

        showReservationModal(resource) {
            this.selectedResource = resource;
            this.reservationError = '';
            this.showReservation = true;
        },

        showUploadModal() {
            this.csvFile = null;
            this.uploadError = '';
            this.showUpload = true;
        },

        async showAvailabilityModal(resource) {
            console.log('showAvailabilityModal called with resource:', resource);
            this.selectedResource = resource;
            this.showAvailability = true;
            console.log('Modal should be visible now, showAvailability:', this.showAvailability);
            
            try {
                console.log('Making API call to:', `/api/resources/${resource.id}/availability`);
                const response = await apiCall(`/api/resources/${resource.id}/availability`);
                const result = await response.json();
                console.log('API response:', result);
                
                if (result.success) {
                    this.availabilityData = result.data;
                    console.log('Availability data set:', this.availabilityData);
                } else {
                    console.error('Failed to load availability:', result.error);
                    this.availabilityData = null;
                }
            } catch (error) {
                console.error('Error loading availability:', error);
                this.availabilityData = null;
            }
        },

        async showHistoryModal(reservation) {
            this.selectedReservation = reservation;
            this.showHistory = true;
            this.reservationHistory = null;
            
            try {
                const response = await apiCall(`/api/reservations/${reservation.id}/history`);
                const result = await response.json();
                
                if (result.success) {
                    this.reservationHistory = result.data;
                } else {
                    console.error('Failed to load history:', result.error);
                    this.reservationHistory = [];
                }
            } catch (error) {
                console.error('Error loading history:', error);
                this.reservationHistory = [];
            }
        },

        // API calls
        async createResource() {
            this.loading = true;
            this.resourceError = '';
            
            try {
                const tags = this.newResource.tags
                    .split(',')
                    .map(tag => tag.trim())
                    .filter(tag => tag);
                
                const response = await apiCall('/api/resources', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: this.newResource.name,
                        tags: tags,
                        available: this.newResource.available
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Add the new resource to local state immediately
                    this.resources.push(result.data);
                    this.filterResources();
                    
                    // Reset form and close modal
                    this.newResource = { name: '', tags: '', available: true };
                    this.showCreateResource = false;
                    
                    showNotification('Resource created successfully!', 'success');
                } else {
                    this.resourceError = result.error;
                }
            } catch (error) {
                this.resourceError = 'Failed to create resource';
                console.error('Resource creation error:', error);
            } finally {
                this.loading = false;
            }
        },

        async createReservation() {
            this.loading = true;
            this.reservationError = '';
            
            try {
                const startDateTime = new Date(`${this.newReservation.startDate}T${this.newReservation.startTime}`);
                const endDateTime = new Date(`${this.newReservation.endDate}T${this.newReservation.endTime}`);
                
                if (endDateTime <= startDateTime) {
                    this.reservationError = 'End time must be after start time';
                    this.loading = false;
                    return;
                }
                
                const response = await apiCall('/api/reservations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        resource_id: this.selectedResource.id,
                        start_time: startDateTime.toISOString(),
                        end_time: endDateTime.toISOString()
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Add the new reservation to the local state immediately
                    const newReservation = {
                        ...result.data,
                        resource: this.selectedResource
                    };
                    this.reservations.push(newReservation);
                    
                    // Reset form
                    this.showReservation = false;
                    this.selectedResource = null;
                    
                    // Switch to reservations tab to show the new reservation
                    this.activeTab = 'reservations';
                    
                    showNotification('Reservation created successfully!', 'success');
                } else {
                    this.reservationError = result.error;
                }
            } catch (error) {
                this.reservationError = 'Failed to create reservation';
                console.error('Reservation creation error:', error);
            } finally {
                this.loading = false;
            }
        },

        async cancelReservation(reservationId) {
            if (!confirm('Are you sure you want to cancel this reservation?')) {
                return;
            }
            
            try {
                const response = await apiCall(`/api/reservations/${reservationId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    const index = this.reservations.findIndex(r => r.id === reservationId);
                    if (index !== -1) {
                        this.reservations[index].status = 'cancelled';
                    }
                    showNotification('Reservation cancelled successfully', 'success');
                } else {
                    showNotification(result.error, 'error');
                }
            } catch (error) {
                showNotification('Failed to cancel reservation', 'error');
            }
        },

        async uploadCsv() {
            this.loading = true;
            this.uploadError = '';
            
            try {
                if (!this.csvFile) {
                    this.uploadError = 'Please select a CSV file';
                    this.loading = false;
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', this.csvFile);
                
                const response = await apiCall('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    this.showUpload = false;
                    this.csvFile = null;
                    showNotification(`Successfully uploaded! Created ${result.data.created_count} resources.`, 'success');
                    
                    // Refresh resources list
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    this.uploadError = result.error || 'Upload failed';
                    console.error('Upload error:', result);
                }
            } catch (error) {
                console.error('Upload exception:', error);
                this.uploadError = 'Failed to upload CSV. Please check your file format.';
            } finally {
                this.loading = false;
            }
        },

        // Utility functions
        formatDateTime(dateString) {
            return new Date(dateString).toLocaleString();
        },

        getHistoryIcon(action) {
            const icons = {
                'created': 'fa-plus-circle',
                'cancelled': 'fa-times-circle',
                'expired': 'fa-clock',
                'modified': 'fa-edit',
                'confirmed': 'fa-check-circle'
            };
            return icons[action] || 'fa-info-circle';
        },

        getHistoryIconClass(action) {
            const classes = {
                'created': 'history-icon-success',
                'cancelled': 'history-icon-danger',
                'expired': 'history-icon-warning',
                'modified': 'history-icon-info',
                'confirmed': 'history-icon-success'
            };
            return classes[action] || 'history-icon-info';
        },

        getHistoryActionText(action) {
            const texts = {
                'created': 'Reservation Created',
                'cancelled': 'Reservation Cancelled',
                'expired': 'Reservation Expired',
                'modified': 'Reservation Modified',
                'confirmed': 'Reservation Confirmed'
            };
            return texts[action] || 'Unknown Action';
        },

        showSystemStatus() {
            // Show system status (could be expanded)
            showNotification('System is running normally', 'info');
        }
    };
}

// Notification system
function showNotification(message, type = 'info') {
    const container = document.getElementById('notifications');
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification-item`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" style="background: none; border: none; color: inherit; font-size: 1.2em; cursor: pointer; margin-left: 10px;">&times;</button>
    `;
    
    container.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Initialize notification system
document.addEventListener('DOMContentLoaded', function() {
    // Notification system is now handled by CSS
    console.log('Frontend application loaded');
});