import { apiClient } from '../api/client';
import { appStore } from '../stores/AppStore';
import type { Reservation } from '../types';
import { showNotification } from '../utils/notifications';

export class ReservationService {
  async loadReservations(includeCancelled = false): Promise<void> {
    try {
      const reservations = await apiClient.getMyReservations(includeCancelled);
      appStore.setReservations(reservations);
    } catch (error) {
      console.error('Failed to load reservations:', error);
      showNotification('Failed to load reservations: ' + (error as Error).message, 'error');
      throw error;
    }
  }

  async createReservation(resourceId: number, startTime: string, endTime: string): Promise<void> {
    try {
      // Validate times
      const startDateTime = new Date(startTime);
      const endDateTime = new Date(endTime);

      if (endDateTime <= startDateTime) {
        throw new Error('End time must be after start time');
      }

      if (startDateTime <= new Date()) {
        throw new Error('Start time must be in the future');
      }

      await apiClient.createReservation(resourceId, startTime, endTime);
      await this.loadReservations(); // Refresh the list
      showNotification('Reservation created successfully!', 'success');
    } catch (error) {
      console.error('Failed to create reservation:', error);
      throw error;
    }
  }

  async cancelReservation(reservationId: number): Promise<void> {
    try {
      await apiClient.cancelReservation(reservationId);
      await this.loadReservations(); // Refresh the list
      showNotification('Reservation cancelled successfully', 'success');
    } catch (error) {
      console.error('Failed to cancel reservation:', error);
      showNotification('Failed to cancel reservation: ' + (error as Error).message, 'error');
      throw error;
    }
  }

  async getReservationHistory(reservationId: number) {
    try {
      return await apiClient.getReservationHistory(reservationId);
    } catch (error) {
      console.error('Failed to get reservation history:', error);
      throw error;
    }
  }

  getUpcomingReservations(): Reservation[] {
    return appStore.getUpcomingReservations();
  }

  getReservationById(id: number): Reservation | undefined {
    const state = appStore.getState();
    return state.reservations.find(r => r.id === id);
  }

  isReservationUpcoming(reservation: Reservation): boolean {
    return new Date(reservation.start_time) > new Date();
  }

  canCancelReservation(reservation: Reservation): boolean {
    return reservation.status === 'active' && this.isReservationUpcoming(reservation);
  }
}

export const reservationService = new ReservationService();