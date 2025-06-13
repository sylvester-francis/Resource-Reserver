import { BaseComponent } from './BaseComponent';
import { appStore } from '../stores/AppStore';
import { authService } from '../services/AuthService';
import { systemService } from '../services/SystemService';
import { $, $$, addEventListener, delegate } from '../utils/dom';
import { ResourcesTabComponent } from './tabs/ResourcesTabComponent';
import { ReservationsTabComponent } from './tabs/ReservationsTabComponent';
import { UpcomingTabComponent } from './tabs/UpcomingTabComponent';
import type { AppState } from '../types';

export class DashboardComponent extends BaseComponent {
  private resourcesTab!: ResourcesTabComponent;
  private reservationsTab!: ReservationsTabComponent;
  private upcomingTab!: UpcomingTabComponent;
  private unsubscribe?: () => void;

  constructor(containerId: string) {
    super(containerId);
    this.initializeTabs();
  }

  private initializeTabs(): void {
    this.resourcesTab = new ResourcesTabComponent('#tabContent');
    this.reservationsTab = new ReservationsTabComponent('#tabContent');
    this.upcomingTab = new UpcomingTabComponent('#tabContent');
  }

  protected render(): string {
    const state = appStore.getState();
    const stats = appStore.getStats();
    const user = authService.getCurrentUser();

    return `
      <header class="header">
        <div class="container">
          <div class="header-content">
            <div class="logo">
              <i class="fas fa-calendar-alt"></i>
              Resource Reservation System
            </div>
            <div class="user-menu">
              <div class="user-info">
                <i class="fas fa-user"></i>
                Welcome, ${user?.username || 'User'}
              </div>
              <button class="btn btn-outline btn-sm" data-action="show-status">
                <i class="fas fa-chart-line"></i> Status
              </button>
              <button class="btn btn-secondary btn-sm" data-action="logout">
                <i class="fas fa-sign-out-alt"></i> Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      <nav class="nav-tabs">
        <div class="container">
          <div class="nav-content">
            <a href="#" class="nav-tab ${state.activeTab === 'resources' ? 'active' : ''}" data-tab="resources">
              <i class="fas fa-cube"></i> Resources
            </a>
            <a href="#" class="nav-tab ${state.activeTab === 'reservations' ? 'active' : ''}" data-tab="reservations">
              <i class="fas fa-calendar-check"></i> My Reservations
            </a>
            <a href="#" class="nav-tab ${state.activeTab === 'upcoming' ? 'active' : ''}" data-tab="upcoming">
              <i class="fas fa-clock"></i> Upcoming
            </a>
          </div>
        </div>
      </nav>

      <main class="container">
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-number">${stats.totalResources}</span>
            <div class="stat-label">Total Resources</div>
          </div>
          <div class="stat-card">
            <span class="stat-number">${stats.availableResources}</span>
            <div class="stat-label">Available Now</div>
          </div>
          <div class="stat-card">
            <span class="stat-number">${stats.activeReservations}</span>
            <div class="stat-label">Active Bookings</div>
          </div>
          <div class="stat-card">
            <span class="stat-number">${stats.upcomingReservations}</span>
            <div class="stat-label">Upcoming</div>
          </div>
        </div>

        <div id="tabContent">
          <!-- Tab content will be rendered here -->
        </div>
      </main>
    `;
  }

  protected bindEvents(): void {
    // Navigation tabs
    delegate(this.container, '.nav-tab', 'click', (e, target) => {
      e.preventDefault();
      const tab = target.dataset.tab as AppState['activeTab'];
      if (tab) {
        this.switchTab(tab);
      }
    });

    // User menu actions
    delegate(this.container, '[data-action="logout"]', 'click', () => {
      authService.logout();
    });

    delegate(this.container, '[data-action="show-status"]', 'click', () => {
      this.showSystemStatus();
    });

    // Subscribe to state changes
    this.unsubscribe = appStore.subscribe((state) => {
      this.updateActiveTab(state.activeTab);
      this.renderCurrentTab();
    });
  }

  private switchTab(tab: AppState['activeTab']): void {
    appStore.setActiveTab(tab);
  }

  private updateActiveTab(activeTab: string): void {
    const tabs = $$('.nav-tab');
    tabs.forEach((tab: Element) => {
      tab.classList.remove('active');
      if ((tab as HTMLElement).dataset.tab === activeTab) {
        tab.classList.add('active');
      }
    });
  }

  private renderCurrentTab(): void {
    const state = appStore.getState();
    
    switch (state.activeTab) {
      case 'resources':
        this.resourcesTab.mount();
        break;
      case 'reservations':
        this.reservationsTab.mount();
        break;
      case 'upcoming':
        this.upcomingTab.mount();
        break;
    }
  }

  private async showSystemStatus(): Promise<void> {
    // This would show a modal with system status
    // For now, just load the status
    await systemService.loadSystemStatus();
  }

  public mount(): void {
    super.mount();
    // Render the initial tab
    this.renderCurrentTab();
  }

  public unmount(): void {
    if (this.unsubscribe) {
      this.unsubscribe();
    }
    super.unmount();
  }
}