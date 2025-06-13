import { BaseComponent } from '../BaseComponent';
import { appStore } from '../../stores/AppStore';
import { reservationService } from '../../services/ReservationService';
import { delegate } from '../../utils/dom';
import { formatDate, formatTime, getTimeUntil } from '../../utils/formatting';
import type { Reservation } from '../../types';

export class UpcomingTabComponent extends BaseComponent {
  protected render(): string {
    const upcomingReservations = reservationService.getUpcomingReservations();

    return `
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">
            <i class="fas fa-clock"></i> Upcoming Reservations
          </h2>
        </div>
        
        <div class="flex gap-2 mb-4">
          <button class="btn btn-outline btn-sm" data-action="refresh">
            <i class="fas fa-sync-alt"></i> Refresh
          </button>
        </div>

        ${upcomingReservations.length === 0 ? this.renderEmptyState() : this.renderUpcomingList(upcomingReservations)}
      </div>
    `;
  }

  private renderEmptyState(): string {
    return `
      <div class="empty-state">
        <i class="fas fa-clock"></i>
        <h3>No upcoming reservations</h3>
        <p>Your upcoming reservations will appear here</p>
        <button class="btn btn-primary" data-action="switch-to-resources">
          Make a Reservation
        </button>
      </div>
    `;
  }

  private renderUpcomingList(reservations: Reservation[]): string {
    return reservations.map(reservation => this.renderUpcomingItem(reservation)).join('');
  }

  private renderUpcomingItem(reservation: Reservation): string {
    const startTime = new Date(reservation.start_time);
    const endTime = new Date(reservation.end_time);
    const timeText = getTimeUntil(startTime);

    return `
      <div class="reservation-item">
        <div class="reservation-info">
          <h3>${reservation.resource.name}</h3>
          <div class="reservation-time">
            <i class="fas fa-clock"></i>
            ${formatDate(startTime)} • ${formatTime(startTime)} - ${formatTime(endTime)}
          </div>
          <div style="color: var(--primary-color); font-size: 0.875rem; margin-top: var(--space-1);">
            <i class="fas fa-hourglass-half"></i> ${timeText}
          </div>
        </div>
        <div class="reservation-actions">
          <button class="btn btn-outline btn-sm" 
                  data-action="show-history" 
                  data-reservation-id="${reservation.id}">
            <i class="fas fa-history"></i> History
          </button>
          <button class="btn btn-danger btn-sm" 
                  data-action="cancel-reservation" 
                  data-reservation-id="${reservation.id}">
            <i class="fas fa-times"></i> Cancel
          </button>
        </div>
      </div>
    `;
  }

  protected bindEvents(): void {
    delegate(this.container, '[data-action="refresh"]', 'click', async () => {
      await reservationService.loadReservations();
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