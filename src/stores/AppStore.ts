import type { AppState, User, Resource, Reservation, SystemStatus } from '../types';

class AppStore {
  private state: AppState = {
    currentUser: this.loadFromStorage('user'),
    authToken: this.loadFromStorage('auth_token'),
    currentView: 'login',
    activeTab: 'resources',
    resources: [],
    reservations: [],
    filteredResources: [],
    searchQuery: '',
    currentFilter: 'all',
    systemStatus: null,
    currentPage: 1,
    itemsPerPage: 10,
    totalPages: 1
  };

  private listeners: Array<(state: AppState) => void> = [];

  constructor() {
    if (this.state.authToken && this.state.currentUser) {
      this.state.currentView = 'dashboard';
    }
  }

  private loadFromStorage(key: string): any {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch {
      return null;
    }
  }

  private saveToStorage(key: string, value: any): void {
    try {
      if (value === null) {
        localStorage.removeItem(key);
      } else {
        localStorage.setItem(key, JSON.stringify(value));
      }
    } catch (error) {
      console.error(`Failed to save ${key} to localStorage:`, error);
    }
  }

  private notifyListeners(): void {
    this.listeners.forEach(listener => listener(this.state));
  }

  subscribe(listener: (state: AppState) => void): () => void {
    this.listeners.push(listener);
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  getState(): AppState {
    return { ...this.state };
  }

  setAuth(user: User, token: string): void {
    this.state.currentUser = user;
    this.state.authToken = token;
    this.state.currentView = 'dashboard';
    this.saveToStorage('user', user);
    this.saveToStorage('auth_token', token);
    this.notifyListeners();
  }

  logout(): void {
    this.state.currentUser = null;
    this.state.authToken = null;
    this.state.currentView = 'login';
    this.saveToStorage('user', null);
    this.saveToStorage('auth_token', null);
    this.notifyListeners();
  }

  setResources(resources: Resource[]): void {
    this.state.resources = resources;
    this.filterResources();
    this.notifyListeners();
  }

  setReservations(reservations: Reservation[]): void {
    this.state.reservations = reservations;
    this.notifyListeners();
  }

  setSystemStatus(status: SystemStatus): void {
    this.state.systemStatus = status;
    this.notifyListeners();
  }

  setActiveTab(tab: AppState['activeTab']): void {
    this.state.activeTab = tab;
    this.notifyListeners();
  }

  setSearchQuery(query: string): void {
    this.state.searchQuery = query;
    this.state.currentPage = 1;
    this.filterResources();
    this.notifyListeners();
  }

  setFilter(filter: AppState['currentFilter']): void {
    this.state.currentFilter = filter;
    this.state.currentPage = 1;
    this.filterResources();
    this.notifyListeners();
  }

  setPage(page: number): void {
    if (page >= 1 && page <= this.state.totalPages) {
      this.state.currentPage = page;
      this.notifyListeners();
    }
  }

  setItemsPerPage(items: number): void {
    this.state.itemsPerPage = items;
    this.state.currentPage = 1;
    this.filterResources();
    this.notifyListeners();
  }

  setFilteredResources(resources: Resource[]): void {
    this.state.filteredResources = resources;
    this.state.searchQuery = '';
    this.state.currentPage = 1;
    this.updatePagination();
    this.notifyListeners();
  }

  private filterResources(): void {
    let filtered = [...this.state.resources];

    if (this.state.currentFilter === 'available') {
      filtered = filtered.filter(r => r.available);
    } else if (this.state.currentFilter === 'unavailable') {
      filtered = filtered.filter(r => !r.available);
    }

    if (this.state.searchQuery) {
      const query = this.state.searchQuery.toLowerCase();
      filtered = filtered.filter(resource =>
        resource.name.toLowerCase().includes(query) ||
        resource.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    this.state.filteredResources = filtered;
    this.updatePagination();
  }

  private updatePagination(): void {
    this.state.totalPages = Math.ceil(this.state.filteredResources.length / this.state.itemsPerPage);
    if (this.state.currentPage > this.state.totalPages && this.state.totalPages > 0) {
      this.state.currentPage = this.state.totalPages;
    }
    if (this.state.currentPage < 1) {
      this.state.currentPage = 1;
    }
  }

  getPaginatedResources(): Resource[] {
    const startIndex = (this.state.currentPage - 1) * this.state.itemsPerPage;
    const endIndex = startIndex + this.state.itemsPerPage;
    return this.state.filteredResources.slice(startIndex, endIndex);
  }

  getUpcomingReservations(): Reservation[] {
    return this.state.reservations
      .filter(r => r.status === 'active' && new Date(r.start_time) > new Date())
      .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
  }

  getStats() {
    return {
      totalResources: this.state.resources.length,
      availableResources: this.state.resources.filter(r => r.available).length,
      activeReservations: this.state.reservations.filter(r => r.status === 'active').length,
      upcomingReservations: this.getUpcomingReservations().length
    };
  }
}

export const appStore = new AppStore();