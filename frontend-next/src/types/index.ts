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
  recurrence_rule_id?: number | null;
  parent_reservation_id?: number | null;
  is_recurring_instance?: boolean;
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

export type NotificationType =
  | 'reservation_confirmed'
  | 'reservation_cancelled'
  | 'reservation_reminder'
  | 'resource_available'
  | 'system_announcement';

export interface Notification {
  id: number;
  type: NotificationType;
  title: string;
  message: string;
  link?: string | null;
  read: boolean;
  created_at: string;
}

export type RecurrenceFrequency = 'daily' | 'weekly' | 'monthly';
export type RecurrenceEndType = 'never' | 'on_date' | 'after_count';

export interface RecurrenceRule {
  id?: number;
  frequency: RecurrenceFrequency;
  interval?: number;
  days_of_week?: number[] | null;
  end_type?: RecurrenceEndType;
  end_date?: string | null;
  occurrence_count?: number | null;
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
