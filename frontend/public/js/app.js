// API wrapper with session handling
const { DateTime } = luxon;

async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, options);
        
        // Check if response indicates session expiration (401 or redirect to login)
        if (response.status === 401 || response.url.includes('/login')) {
            // Session expired, redirect to login
            window.location.href = '/login?error=' + encodeURIComponent('Your session has expired. Please log in again.');
            return;
        }
        
        // Handle other HTTP errors gracefully
        if (!response.ok) {
            const errorText = await response.text();
            let errorMessage;
            
            try {
                const errorData = JSON.parse(errorText);
                errorMessage = errorData.error || errorData.detail || errorData.message || `Request failed (${response.status})`;
            } catch {
                errorMessage = `Request failed with status ${response.status}`;
            }
            
            throw new Error(errorMessage);
        }
        
        return response;
    } catch (error) {
        console.error('API call failed:', error);
        
        // Provide user-friendly error messages
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('Unable to connect to the server. Please check your connection.');
        }
        
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
        
        // Time-based search
        showAdvancedSearch: false,
        searchTimeFrom: '',
        searchTimeUntil: '',
        
        // Pagination
        currentPage: 1,
        itemsPerPage: 10,
        
        // Stats
        stats: {
            totalResources: 0,
            availableResources: 0,
            activeReservations: 0,
            upcomingReservations: 0
        },
        
        // Modals
        showCreateResource: false,
        showReservation: false,
        showUpload: false,
        showAvailability: false,
        showHistory: false,
        showHealthStatus: false,
        showResourceStatus: false,
        
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
        availabilityDaysAhead: 7,
        selectedReservation: null,
        reservationHistory: null,
        healthData: null,
        
        // Errors
        resourceError: '',
        reservationError: '',
        uploadError: '',

        // Initialize with robust data validation
        init() {
            try {
                // Validate and set initial data
                this.resources = this.validateResourceArray(window.initialResources);
                this.reservations = this.validateReservationArray(window.initialReservations);
                
                // Initialize filtered resources safely
                this.filterResources();
                this.updateStats();
                
                // Set default dates for reservation form
                this.initializeReservationForm();
                
                // Set up periodic refresh for real-time updates
                this.setupPeriodicRefresh();
                
            } catch (error) {
                console.error('Initialization error:', error);
                // Ensure arrays are always initialized
                this.resources = [];
                this.reservations = [];
                this.filteredResources = [];
                showNotification('Application initialized with limited functionality. Please refresh the page.', 'warning');
            }
        },

        // Validate resource data array
        validateResourceArray(data) {
            if (!Array.isArray(data)) {
                console.warn('Invalid resources data, using empty array');
                return [];
            }
            const validResources = data.filter(resource => 
                resource && 
                typeof resource.id === 'number' && 
                typeof resource.name === 'string' &&
                typeof resource.available === 'boolean' &&
                Array.isArray(resource.tags)
            );
            console.log('Resource validation:', data.length, 'input,', validResources.length, 'valid');
            return validResources;
        },

        // Validate reservation data array
        validateReservationArray(data) {
            if (!Array.isArray(data)) {
                console.warn('Invalid reservations data, using empty array');
                return [];
            }
            return data.filter(reservation => 
                reservation && 
                typeof reservation.id === 'number' &&
                typeof reservation.start_time === 'string' &&
                typeof reservation.end_time === 'string' &&
                typeof reservation.status === 'string'
            );
        },

        // Initialize reservation form with safe date handling
        initializeReservationForm() {
            try {
                const now = DateTime.now();
                const tomorrow = now.plus({days: 1});
                this.newReservation.startDate = tomorrow.toISODate();
                this.newReservation.endDate = tomorrow.toISODate();
                this.newReservation.startTime = '09:00';
                this.newReservation.endTime = '10:00';
            } catch (error) {
                console.error('Error setting default dates:', error);
                // Fallback to manual date setting
                this.newReservation.startTime = '09:00';
                this.newReservation.endTime = '10:00';
            }
        },

        // Setup periodic refresh for real-time updates
        setupPeriodicRefresh() {
            // Refresh stats every 30 seconds to keep data current
            setInterval(() => {
                if (document.visibilityState === 'visible') {
                    this.refreshResourcesIfNeeded();
                }
            }, 30000);
        },

        // Refresh resources only if page is visible and user isn't actively working
        async refreshResourcesIfNeeded() {
            try {
                // Don't refresh if user is in the middle of an operation
                if (this.loading || this.showCreateResource || this.showReservation) {
                    return;
                }

                await this.refreshResources();
            } catch (error) {
                // Silent fail for background refresh
                console.warn('Background refresh failed:', error);
            }
        },

        // Computed properties
        get upcomingReservations() {
            return this.reservations.filter(r => 
                r.status === 'active' && DateTime.fromISO(r.start_time) > DateTime.now()
            ).sort((a, b) => DateTime.fromISO(a.start_time) - DateTime.fromISO(b.start_time));
        },

        // Pagination computed properties
        get totalPages() {
            return Math.ceil(this.filteredResources.length / this.itemsPerPage);
        },

        get paginatedResources() {
            const start = (this.currentPage - 1) * this.itemsPerPage;
            const end = start + this.itemsPerPage;
            return this.filteredResources.slice(start, end);
        },

        get showPagination() {
            return this.totalPages > 1;
        },

        get paginationPages() {
            const pages = [];
            const maxVisible = 5;
            const start = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
            const end = Math.min(this.totalPages, start + maxVisible - 1);
            
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
            return pages;
        },

        // Update stats based on current data
        updateStats() {
            this.stats.totalResources = this.resources.length;
            // Use current_availability if available, otherwise fall back to base availability
            this.stats.availableResources = this.resources.filter(r => 
                r.current_availability !== undefined ? r.current_availability : r.available
            ).length;
            this.stats.activeReservations = this.reservations.filter(r => r.status === 'active').length;
            this.stats.upcomingReservations = this.reservations.filter(r => 
                r.status === 'active' && new Date(r.start_time) > new Date()
            ).length;
            console.log('Stats updated:', this.stats, 'Resources array length:', this.resources.length);
        },

        // Filter and search using backend with robust error handling
        async filterResources() {
            try {
                // Reset to first page when filtering/searching
                this.currentPage = 1;
                
                // For 'unavailable' filter, we need to use local filtering since backend doesn't support it
                if (this.currentFilter === 'unavailable') {
                    this.localFilterResources();
                    return;
                }
                
                const params = {};
                
                // Add search query if present (validate and sanitize)
                if (this.searchQuery && typeof this.searchQuery === 'string') {
                    params.q = this.searchQuery.trim().slice(0, 100); // Limit query length
                }
                
                // Apply status filter (new API parameter)
                if (this.currentFilter !== 'all') {
                    params.status = this.currentFilter;
                } else {
                    params.status = 'all';
                }
                
                // Add time-based search parameters
                if (this.searchTimeFrom) {
                    // Convert to ISO format for API
                    // Convert local datetime to UTC ISO string
                    params.available_from = DateTime.fromJSDate(this.searchTimeFrom).toUTC().toISO();
                }
                if (this.searchTimeUntil) {
                    // Convert to ISO format for API
                    params.available_until = DateTime.fromJSDate(this.searchTimeUntil).toUTC().toISO();
                }
                
                // Only call backend if we have search query, specific filter, or time parameters
                if (params.q || this.currentFilter !== 'all' || params.available_from || params.available_until) {
                    const response = await apiCall('/api/resources/search?' + new URLSearchParams(params));
                    
                    // Handle response safety
                    if (!response) {
                        this.localFilterResources();
                        return;
                    }
                    
                    const result = await response.json();
                    
                    if (result && result.success && Array.isArray(result.data)) {
                        this.filteredResources = result.data;
                    } else {
                        console.error('Search failed:', result?.error || 'Invalid response format');
                        // Fallback to local filtering
                        this.localFilterResources();
                    }
                } else {
                    // No search and 'all' filter - show local resources
                    this.filteredResources = Array.isArray(this.resources) ? [...this.resources] : [];
                }
            } catch (error) {
                console.error('Search error:', error);
                // Always fallback to local filtering on any error
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
            this.currentPage = 1; // Reset to first page when filtering
            this.filterResources();
        },

        // Time-based search functions
        setTimePreset(preset) {
            const now = DateTime.now();

            switch (preset) {
                case 'now':
                    // Available from now for the next 2 hours
                    this.searchTimeFrom = this.formatDateTimeLocal(now);
                    const twoHoursLater = now.plus({ hours: 2 });
                    this.searchTimeUntil = this.formatDateTimeLocal(twoHoursLater);
                    break;
                case 'today':
                    // Rest of today (current time to end of day)
                    this.searchTimeFrom = this.formatDateTimeLocal(now);
                    const endOfDay = DateTime.now().endOf('day');
                    this.searchTimeUntil = this.formatDateTimeLocal(endOfDay);
                    break;
                case 'tomorrow':
                    // All day tomorrow
                    const tomorrow = now.plus({ days: 1 });
                    let temp = tomorrow.set({ hour: 9, minute: 0, second: 0, millisecond: 0 }); // Start at 9 AM
                    this.searchTimeFrom = this.formatDateTimeLocal(temp);
                    temp = tomorrow.set({ hour: 17, minute: 0, second: 0, millisecond: 0 }); // End at 5 PM
                    this.searchTimeUntil = this.formatDateTimeLocal(temp);
                    break;
            }
            
            this.filterResources();
        },

        clearTimeSearch() {
            this.searchTimeFrom = '';
            this.searchTimeUntil = '';
            this.showAdvancedSearch = false;
            this.filterResources();
        },

        // Helper function to format datetime for datetime-local input
        formatDateTimeLocal(dateString) {
            return DateTime.fromISO(dateString).toLocaleString();
        },

        // Toggle advanced search visibility
        // Pagination methods
        goToPage(page) {
            if (page >= 1 && page <= this.totalPages) {
                this.currentPage = page;
            }
        },

        nextPage() {
            if (this.currentPage < this.totalPages) {
                this.currentPage++;
            }
        },

        prevPage() {
            if (this.currentPage > 1) {
                this.currentPage--;
            }
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

                // Convert UTC reservations to local time and group by day
        groupReservationsByDay(reservations) {
            const groupedByDay = new Map();
            
            if (!Array.isArray(reservations)) {
                return [];
            }
            
            reservations.forEach(reservation => {
                try {
                    // Parse UTC times and convert to local
                    const startTime = DateTime.fromISO(reservation.start_time).toLocal();
                    const endTime = DateTime.fromISO(reservation.end_time).toLocal();
                    
                    // Check if reservation spans multiple days
                    const startDate = startTime.toISODate();
                    const endDate = endTime.toISODate();
                    
                    if (startDate === endDate) {
                        // Reservation is within a single day
                        this.addReservationToDay(groupedByDay, {
                            date: startDate,
                            dayName: startTime.toFormat('EEEE, MMMM d, yyyy'),
                            start_time: startTime.toFormat('h:mm a'),
                            end_time: endTime.toFormat('h:mm a'),
                            status: reservation.status,
                            id: reservation.id,
                            resource_id: reservation.resource_id,
                            user_id: reservation.user_id,
                            user_name: reservation.user_name,
                            isPartial: false
                        });
                    } else {
                        // Reservation spans multiple days - split it
                        let currentDate = startTime;
                        
                        while (currentDate.toISODate() <= endDate) {
                            const dateStr = currentDate.toISODate();
                            
                            // Determine start and end times for this day
                            let dayStartTime, dayEndTime;
                            
                            if (dateStr === startDate) {
                                // First day: use reservation start time to end of day
                                dayStartTime = startTime;
                                dayEndTime = currentDate.endOf('day');
                            } else if (dateStr === endDate) {
                                // Last day: use start of day to reservation end time
                                dayStartTime = currentDate.startOf('day');
                                dayEndTime = endTime;
                            } else {
                                // Middle days: use full day
                                dayStartTime = currentDate.startOf('day');
                                dayEndTime = currentDate.endOf('day');
                            }
                            
                            this.addReservationToDay(groupedByDay, {
                                date: dateStr,
                                dayName: currentDate.toFormat('EEEE, MMMM d, yyyy'),
                                start_time: dayStartTime.toFormat('h:mm a'),
                                end_time: dayEndTime.toFormat('h:mm a'),
                                status: reservation.status,
                                id: reservation.id,
                                resource_id: reservation.resource_id,
                                user_id: reservation.user_id,
                                user_name: reservation.user_name,
                                isPartial: true // Mark as part of a multi-day reservation
                            });
                            
                            // Move to next day
                            currentDate = currentDate.plus({ days: 1 }).startOf('day');
                        }
                    }
                    
                } catch (error) {
                    console.error('Error processing reservation:', reservation, error);
                }
            });
            
            // Convert Map to array and sort by date
            const sortedReservations = Array.from(groupedByDay.values()).sort((a, b) => {
                return DateTime.fromISO(a.date) - DateTime.fromISO(b.date);
            });
            
            // Sort time slots within each day by start time
            sortedReservations.forEach(day => {
                day.time_slots.sort((a, b) => {
                    const timeA = DateTime.fromFormat(a.start_time, 'h:mm a');
                    const timeB = DateTime.fromFormat(b.start_time, 'h:mm a');
                    return timeA - timeB;
                });
            });
            
            return sortedReservations;
        },

        // Helper method to add a reservation to a specific day
        addReservationToDay(groupedByDay, timeSlotData) {
            const { date, dayName, ...slotData } = timeSlotData;
            
            // Create the day entry if it doesn't exist
            if (!groupedByDay.has(date)) {
                groupedByDay.set(date, {
                    date: date,
                    dayName: dayName,
                    time_slots: []
                });
            }
            
            // Add the time slot to the day's array
            groupedByDay.get(date).time_slots.push(slotData);
        },
        
        async showAvailabilityModal(resource, days = 7) {
            this.selectedResource = resource;
            this.showAvailability = true;
            
            try {
                const response = await apiCall(`/api/resources/${resource.id}/availability?days_ahead=${days}`);
                const result = await response.json();

                if (result.success) {
                    this.availabilityData = result.data;
                    
                    // Convert and group reservations by day (UTC to local time)
                    if (this.availabilityData.reservations && Array.isArray(this.availabilityData.reservations)) {
                        this.availabilityData.reservations = this.groupReservationsByDay(
                            this.availabilityData.reservations
                        );
                    }
                    this.availabilityData.reservations.forEach(reservation => {
                        if (!reservation.user_name) {
                            reservation.user_name = 'Unknown User (' + reservation.user_id + ')';
                        }
                    });
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
                    this.updateStats();
                    
                    // Reset form and close modal
                    this.newResource = { name: '', tags: '', available: true };
                    this.showCreateResource = false;
                    
                    showNotification('Resource created successfully!', 'success');
                } else {
                    // Handle specific error messages gracefully
                    const errorMessage = result.error || 'Failed to create resource';
                    if (errorMessage.toLowerCase().includes('already exists')) {
                        this.resourceError = `A resource named "${this.newResource.name}" already exists. Please choose a different name.`;
                    } else {
                        this.resourceError = errorMessage;
                    }
                }
            } catch (error) {
                // Handle network or other errors gracefully
                console.error('Resource creation error:', error);
                if (error.message && error.message.includes('already exists')) {
                    this.resourceError = `A resource named "${this.newResource.name}" already exists. Please choose a different name.`;
                } else {
                    this.resourceError = 'Unable to create resource. Please check your connection and try again.';
                }
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
                    // convert to ISO strings in UTC
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
                    // Update stats immediately after cancellation
                    this.updateStats();
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
                
                if (response.ok) {
                    this.showUpload = false;
                    this.csvFile = null;
                    
                    // Show success message with details
                    let message = `Successfully uploaded! Created ${result.created_count} resources.`;
                    if (result.errors && result.errors.length > 0) {
                        message += ` ${result.errors.length} errors occurred.`;
                    }
                    showNotification(message, 'success');
                    
                    // Refresh resources list and stats without page reload
                    await this.refreshResources();
                } else {
                    this.uploadError = result.detail || result.error || 'Upload failed';
                    console.error('Upload error:', result);
                }
            } catch (error) {
                console.error('Upload exception:', error);
                this.uploadError = 'Failed to upload CSV. Please check your file format.';
            } finally {
                this.loading = false;
            }
        },

        // Refresh resources from server
        async refreshResources() {
            try {
                const response = await apiCall('/api/resources/search?status=all');
                
                if (response.ok) {
                    const result = await response.json();
                    // Handle wrapped response format from frontend proxy
                    if (result.success && result.data) {
                        this.resources = result.data;
                    } else {
                        // Fallback for direct API response
                        this.resources = result;
                    }
                    this.filterResources();
                    this.updateStats();
                    console.log('Resources refreshed:', this.resources.length, 'resources loaded');
                } else {
                    console.error('Failed to refresh resources:', response.status);
                }
            } catch (error) {
                console.error('Error refreshing resources:', error);
            }
        },

        // Utility functions
        formatDateTime(dateString) {
            return DateTime.fromISO(dateString);
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

        async showSystemStatus() {
            this.showHealthStatus = true;
            await this.refreshHealthData();
        },

        async refreshHealthData() {
            try {
                const response = await apiCall('/api/health');
                const result = await response.json();
                
                if (result.success) {
                    this.healthData = result.data;
                } else {
                    console.error('Failed to load health data:', result.error);
                    this.healthData = null;
                }
            } catch (error) {
                console.error('Error loading health data:', error);
                this.healthData = null;
            }
        },

        // Get display text for resource status
        getResourceStatusText(resource) {
            // Use new status field if available
            if (resource.status) {
                const statusMap = {
                    'available': 'Available',
                    'in_use': 'In Use',
                    'unavailable': 'Maintenance'
                };
                return statusMap[resource.status] || resource.status;
            }
            
            // Fallback to old logic
            if (!resource.available) {
                return 'Disabled';
            }
            if (resource.current_availability === false) {
                return 'In Use';
            }
            return 'Available';
        },

        // Get status icon for resource
        getResourceStatusIcon(resource) {
            if (resource.status) {
                const iconMap = {
                    'available': '🟢',
                    'in_use': '🟡',
                    'unavailable': '🔴'
                };
                return iconMap[resource.status] || '❓';
            }
            
            // Fallback to old logic
            if (!resource.available) {
                return '🔴';
            }
            if (resource.current_availability === false) {
                return '🟡';
            }
            return '🟢';
        },

        // Set resource to maintenance mode
        async setResourceMaintenance(resource, hours = 8) {
            try {
                const response = await apiCall(`/api/resources/${resource.id}/status/unavailable?auto_reset_hours=${hours}`, {
                    method: 'PUT'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Update resource in local state
                    const resourceIndex = this.resources.findIndex(r => r.id === resource.id);
                    if (resourceIndex !== -1) {
                        this.resources[resourceIndex].status = 'unavailable';
                    }
                    
                    const filteredIndex = this.filteredResources.findIndex(r => r.id === resource.id);
                    if (filteredIndex !== -1) {
                        this.filteredResources[filteredIndex].status = 'unavailable';
                    }
                    
                    this.updateStats();
                    showNotification(`Resource set to maintenance mode (auto-reset in ${hours} hours)`, 'success');
                } else {
                    showNotification(result.error || 'Failed to set maintenance mode', 'error');
                }
            } catch (error) {
                console.error('Error setting maintenance mode:', error);
                showNotification('Failed to set maintenance mode', 'error');
            }
        },

        // Reset resource to available
        async resetResourceToAvailable(resource) {
            try {
                const response = await apiCall(`/api/resources/${resource.id}/status/available`, {
                    method: 'PUT'
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Update resource in local state
                    const resourceIndex = this.resources.findIndex(r => r.id === resource.id);
                    if (resourceIndex !== -1) {
                        this.resources[resourceIndex].status = 'available';
                    }
                    
                    const filteredIndex = this.filteredResources.findIndex(r => r.id === resource.id);
                    if (filteredIndex !== -1) {
                        this.filteredResources[filteredIndex].status = 'available';
                    }
                    
                    this.updateStats();
                    showNotification('Resource reset to available', 'success');
                } else {
                    showNotification(result.error || 'Failed to reset resource', 'error');
                }
            } catch (error) {
                console.error('Error resetting resource:', error);
                showNotification('Failed to reset resource', 'error');
            }
        },

        // Show resource status details modal
        async showResourceStatusModal(resource) {
            this.selectedResource = resource;
            
            try {
                const response = await apiCall(`/api/resources/${resource.id}/status`);
                const result = await response.json();
                
                if (result.success) {
                    this.selectedResource.statusDetails = result.data;
                } else {
                    console.error('Failed to load status details:', result.error);
                    this.selectedResource.statusDetails = null;
                }
            } catch (error) {
                console.error('Error loading status details:', error);
                this.selectedResource.statusDetails = null;
            }
            
            this.showResourceStatus = true;
        },

        // Toggle resource status (available/disabled)
        async toggleResourceStatus(resource) {
            // Don't allow toggling if resource is currently in use
            if (resource.available && resource.current_availability === false) {
                showNotification('Cannot disable resource while it is in use', 'warning');
                return;
            }

            try {
                const newAvailability = !resource.available;
                const response = await apiCall(`/api/resources/${resource.id}/availability`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ available: newAvailability })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Update the resource in local state
                    const resourceIndex = this.resources.findIndex(r => r.id === resource.id);
                    if (resourceIndex !== -1) {
                        this.resources[resourceIndex].available = newAvailability;
                        this.resources[resourceIndex].current_availability = newAvailability ? this.resources[resourceIndex].current_availability : false;
                    }
                    
                    // Update filtered resources as well
                    const filteredIndex = this.filteredResources.findIndex(r => r.id === resource.id);
                    if (filteredIndex !== -1) {
                        this.filteredResources[filteredIndex].available = newAvailability;
                        this.filteredResources[filteredIndex].current_availability = newAvailability ? this.filteredResources[filteredIndex].current_availability : false;
                    }
                    
                    // Update stats
                    this.updateStats();
                    
                    const action = newAvailability ? 'enabled' : 'disabled';
                    showNotification(`Resource ${action} successfully`, 'success');
                } else {
                    showNotification(result.error || 'Failed to update resource status', 'error');
                }
            } catch (error) {
                console.error('Error toggling resource status:', error);
                showNotification('Failed to update resource status', 'error');
            }
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