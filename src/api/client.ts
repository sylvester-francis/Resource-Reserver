import type { 
  LoginData, 
  Resource, 
  Reservation, 
  SystemStatus, 
  AvailabilityInfo, 
  SearchParams,
  ReservationHistory 
} from '../types';

const API_BASE_URL = 'http://localhost:8000';

class ApiClient {
  private authToken: string | null = null;

  setAuthToken(token: string | null): void {
    this.authToken = token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(this.authToken && { 'Authorization': `Bearer ${this.authToken}` }),
      ...options.headers
    };

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage: string;
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
      return await response.text() as T;
    } catch (error) {
      console.error(`API call failed for ${endpoint}:`, error);
      throw error;
    }
  }

  async login(username: string, password: string): Promise<LoginData> {
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

    return await response.json();
  }

  async register(username: string, password: string): Promise<void> {
    await this.request('/register', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
  }

  async getResources(): Promise<Resource[]> {
    return this.request<Resource[]>('/resources');
  }

  async searchResources(params: SearchParams): Promise<Resource[]> {
    const queryParams = new URLSearchParams();
    if (params.query) queryParams.append('q', params.query);
    if (params.availableOnly !== undefined) queryParams.append('available_only', String(params.availableOnly));
    if (params.availableFrom) queryParams.append('available_from', params.availableFrom);
    if (params.availableUntil) queryParams.append('available_until', params.availableUntil);

    const queryString = queryParams.toString();
    const endpoint = queryString ? `/resources/search?${queryString}` : '/resources/search';
    return this.request<Resource[]>(endpoint);
  }

  async getResourceAvailability(resourceId: number, daysAhead = 7): Promise<AvailabilityInfo> {
    const params = new URLSearchParams({ days_ahead: String(daysAhead) });
    return this.request<AvailabilityInfo>(`/resources/${resourceId}/availability?${params}`);
  }

  async createResource(name: string, tags: string[], available: boolean): Promise<Resource> {
    return this.request<Resource>('/resources', {
      method: 'POST',
      body: JSON.stringify({ name, tags, available })
    });
  }

  async uploadResourcesCsv(file: File): Promise<{ created_count: number; errors?: string[] }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/resources/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.authToken}`
      },
      body: formData
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || 'Upload failed');
    }

    return await response.json();
  }

  async getMyReservations(includeCancelled = false): Promise<Reservation[]> {
    const params = new URLSearchParams();
    if (includeCancelled) params.append('include_cancelled', 'true');
    const endpoint = params.toString() ? `/reservations/my?${params}` : '/reservations/my';
    return this.request<Reservation[]>(endpoint);
  }

  async createReservation(resourceId: number, startTime: string, endTime: string): Promise<Reservation> {
    return this.request<Reservation>('/reservations', {
      method: 'POST',
      body: JSON.stringify({
        resource_id: resourceId,
        start_time: startTime,
        end_time: endTime
      })
    });
  }

  async cancelReservation(reservationId: number, reason = 'Cancelled by user'): Promise<void> {
    await this.request(`/reservations/${reservationId}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    });
  }

  async getReservationHistory(reservationId: number): Promise<ReservationHistory[]> {
    return this.request<ReservationHistory[]>(`/reservations/${reservationId}/history`);
  }

  async getSystemStatus(): Promise<SystemStatus> {
    return this.request<SystemStatus>('/health');
  }

  async getResourcesSummary(): Promise<{
    total_resources: number;
    available_now: number;
    unavailable_now: number;
    currently_in_use: number;
    timestamp: string;
  }> {
    return this.request('/resources/availability/summary');
  }
}

export const apiClient = new ApiClient();