import { apiClient } from '../api/client';
import { appStore } from '../stores/AppStore';
import { showNotification } from '../utils/notifications';

export class AuthService {
  async login(username: string, password: string): Promise<void> {
    try {
      const data = await apiClient.login(username, password);
      const user = { username };
      
      apiClient.setAuthToken(data.access_token);
      appStore.setAuth(user, data.access_token);
    } catch (error) {
      throw error;
    }
  }

  async register(username: string, password: string): Promise<void> {
    try {
      await apiClient.register(username, password);
      showNotification('Registration successful! Please sign in.', 'success');
    } catch (error) {
      throw error;
    }
  }

  logout(): void {
    apiClient.setAuthToken(null);
    appStore.logout();
  }

  isAuthenticated(): boolean {
    const state = appStore.getState();
    return !!(state.authToken && state.currentUser);
  }

  getCurrentUser() {
    return appStore.getState().currentUser;
  }

  getAuthToken(): string | null {
    return appStore.getState().authToken;
  }
}

export const authService = new AuthService();