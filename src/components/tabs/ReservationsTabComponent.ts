import { BaseComponent } from '../BaseComponent';
import { appStore } from '../../stores/AppStore';
import { reservationService } from '../../services/ReservationService';
import { delegate } from '../../utils/dom';
import { formatDate, formatTime } from '../../utils/formatting';
import type { Reservation } from '../../types';

export class ReservationsTabComponent extends BaseComponent {
  protected render(): string {
    const state = appStore.getState();

    return `
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">
            <i class="fas fa-calendar-check"></i> My Reservations
          </h2>
        </div>
        
        <div class="flex gap-2 mb-4">
          <button class="btn btn-outline btn-sm" data-action="include-cancelled">
            <i class="fas fa-list"></i> Include Cancelled
          </button>
          <button class="btn btn-outline btn-sm" data-action="refresh">
            <i class="fas fa-sync-alt"></i> Refresh
          </button>
        </div>

        ${state.reservations.length === 0 ? this.renderEmptyState() : this.renderReservationsList()}
      </div>
    `;
  }

  private renderEmptyState(): string {
    return `
      <div class="empty-state">
        <i class="fas fa-calendar-check"></i>
        <h3>No reservations found</h3>
        <p>Once you make a reservation, you'll see it here</p>
        <button class="btn btn-primary" data-action="switch-to-resources">
          Make a Reservation
        </button>
      </div>
    `;
  }

  private renderReservationsList(): string {
    const state = appStore.getState();
    
    return state.reservations.map(reservation => this.renderReservationItem(reservation)).join('');
  }

  private renderReservationItem(reservation: Reservation): string {
    const startTime = new Date(reservation.start_time);
    const endTime = new Date(reservation.end_time);
    const isUpcoming = reservationService.isReservationUpcoming(reservation);
    const canCancel = reservationService.canCancelReservation(reservation);

    return `
      <div class="reservation-item">
        <div class="reservation-info">
          <h3>${reservation.resource.name}</h3>
          <div class="reservation-time">
            <i class="fas fa-clock"></i>
            ${formatDate(startTime)} • ${formatTime(startTime)} - ${formatTime(endTime)}
          </div>
          <div class="reservation-badges">
            <span class="resource-status ${reservation.status === 'active' ? 'available' : 'unavailable'}">
              ${reservation.status.charAt(0).toUpperCase() + reservation.status.slice(1)}
            </span>
            ${isUpcoming ? '<span class="resource-status available">Upcoming</span>' : ''}
          </div>
        </div>
        
        <div class="reservation-actions">
          <button class="btn btn-outline btn-sm" 
                  data-action="show-history" 
                  data-reservation-id="${reservation.id}">
            <i class="fas fa-history"></i> History
          </button>
          ${canCancel ? `
            <button class="btn btn-danger btn-sm" 
                    data-action="cancel-reservation" 
                    data-reservation-id="${reservation.id}">
              <i class="fas fa-times"></i> Cancel
            </button>
          ` : ''}
        </div>
      </div>
    `;
  }

  protected bindEvents(): void {
    delegate(this.container, '[data-action="refresh"]', 'click', async () => {
      await reservationService.loadReservations();
    });

    delegate(this.container, '[data-action="include-cancelled"]', 'click', async () => {
      await reservationService.loadReservations(true);
    });

    delegate(this.container, '[data-action="switch-to-resources"]', 'click', () => {
      appStore.setActiveTab('resources');
    });

    delegate(this.container, '[data-action="cancel-reservation"]', 'click', async (e, target) => {
      const reservationId = parseInt(target.dataset.reservationId || '0');
      if (reservationId && confirm('Are you sure you want to cancel this reservation?')) {
        await reservationService.cancelReservation(reservationId);
      }
    });

    delegate(this.container, '[data-action="show-history"]', 'click', (e, target) => {
      const reservationId = parseInt(target.dataset.reservationId || '0');
      if (reservationId) {
        // TODO: Show history modal
        console.log('Show history for reservation', reservationId);
      }
    });
  }
}