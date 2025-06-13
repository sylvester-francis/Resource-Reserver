import { appStore } from './stores/AppStore';
import { authService } from './services/AuthService';
import { resourceService } from './services/ResourceService';
import { reservationService } from './services/ReservationService';
import { systemService } from './services/SystemService';
import { apiClient } from './api/client';
import { LoginComponent } from './components/LoginComponent';
import { DashboardComponent } from './components/DashboardComponent';
import type { AppState } from './types';

export class AppController {
  private loginComponent!: LoginComponent;
  private dashboardComponent!: DashboardComponent;
  private currentComponent: LoginComponent | DashboardComponent | null = null;
  private unsubscribe?: () => void;

  public initialize(): void {
    this.initializeComponents();
    this.setupStateSubscription();
    this.initializeApp();
  }

  private initializeComponents(): void {
    this.loginComponent = new LoginComponent('#app');
    this.dashboardComponent = new DashboardComponent('#app');
  }

  private setupStateSubscription(): void {
    this.unsubscribe = appStore.subscribe((state: AppState) => {
      this.handleStateChange(state);
    });
  }

  private async initializeApp(): Promise<void> {
    const state = appStore.getState();
    
    if (state.authToken && state.currentUser) {
      // Set auth token for API client
      apiClient.setAuthToken(state.authToken);
      
      try {
        // Load initial data
        await this.loadDashboardData();
        // The component will be mounted via state change
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
        // If loading fails, logout and show login
        authService.logout();
      }
    } else {
      this.showLogin();
    }
  }

  private async loadDashboardData(): Promise<void> {
    try {
      await Promise.all([
        resourceService.loadResources(),
        reservationService.loadReservations(),
        systemService.loadSystemStatus()
      ]);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      throw error;
    }
  }

  private handleStateChange(state: AppState): void {
    if (state.currentView === 'login') {
      this.showLogin();
    } else if (state.currentView === 'dashboard') {
      if (state.authToken) {
        apiClient.setAuthToken(state.authToken);
      }
      this.showDashboard();
    }
  }

  private showLogin(): void {
    if (this.currentComponent !== this.loginComponent) {
      this.currentComponent?.unmount();
      this.currentComponent = this.loginComponent;
      this.loginComponent.mount();
    }
  }

  private showDashboard(): void {
    if (this.currentComponent !== this.dashboardComponent) {
      this.currentComponent?.unmount();
      this.currentComponent = this.dashboardComponent;
      this.dashboardComponent.mount();
    }
  }

  public destroy(): void {
    if (this.unsubscribe) {
      this.unsubscribe();
    }
    this.currentComponent?.unmount();
  }
}