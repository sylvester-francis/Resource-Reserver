// Type definitions for the application

export interface User {
  id: number;
  username: string;
  email?: string;
  email_verified?: boolean;
  mfa_enabled: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  next_cursor?: string | null;
  prev_cursor?: string | null;
  has_more: boolean;
  total_count?: number | null;
}

export interface Resource {
  id: number;
  name: string;
  available: boolean;
  tags: string[];
  status: 'available' | 'in_use' | 'unavailable';
  current_availability?: boolean;
  unavailable_since?: string;
  auto_reset_hours?: number;
}

export interface Reservation {
  id: number;
  user_id: number;
  resource_id: number;
  resource?: Resource;
  start_time: string;
  end_time: string;
  status: 'active' | 'cancelled' | 'expired';
  created_at: string;
  cancelled_at?: string;
  cancellation_reason?: string;
}

export interface MFASetupResponse {
  secret: string;
  qr_code: string;
  backup_codes: string[];
}

export interface HealthStatus {
  status: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

export interface OAuth2Client {
  id: number;
  client_id: string;
  client_name: string;
  redirect_uris: string[];
  owner_id: number;
  created_at: string;
}

export interface Role {
  id: number;
  name: string;
  description?: string;
}

export interface HistoryEntry {
  id: number;
  action: string;
  timestamp: string;
  details?: string;
}
