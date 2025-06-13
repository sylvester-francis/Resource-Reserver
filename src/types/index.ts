export interface User {
  username: string;
}

export interface Resource {
  id: number;
  name: string;
  tags: string[];
  available: boolean;
}

export interface Reservation {
  id: number;
  resource: Resource;
  start_time: string;
  end_time: string;
  status: 'active' | 'cancelled';
  user_id: string;
}

export interface SystemStatus {
  status: 'healthy' | 'error';
  timestamp?: string;
  background_tasks?: Record<string, string>;
  error?: string;
}

export interface AvailabilityInfo {
  is_currently_available: boolean;
  base_available: boolean;
  current_time: string;
  reservations: Reservation[];
}

export interface SearchParams {
  query?: string;
  availableOnly?: boolean;
  availableFrom?: string;
  availableUntil?: string;
}

export interface LoginData {
  access_token: string;
}

export interface NotificationType {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
}

export interface AppState {
  currentUser: User | null;
  authToken: string | null;
  currentView: 'login' | 'dashboard';
  activeTab: 'resources' | 'reservations' | 'upcoming';
  resources: Resource[];
  reservations: Reservation[];
  filteredResources: Resource[];
  searchQuery: string;
  currentFilter: 'all' | 'available' | 'unavailable';
  systemStatus: SystemStatus | null;
  currentPage: number;
  itemsPerPage: number;
  totalPages: number;
}

export interface ReservationHistory {
  id: number;
  action: 'created' | 'cancelled' | 'updated' | 'expired';
  timestamp: string;
  details?: string;
}