import { apiClient } from '../api/client';
import { appStore } from '../stores/AppStore';
import type { SystemStatus } from '../types';

export class SystemService {
  async loadSystemStatus(): Promise<void> {
    try {
      const status = await apiClient.getSystemStatus();
      appStore.setSystemStatus(status);
    } catch (error) {
      console.error('Failed to load system status:', error);
      const errorStatus: SystemStatus = { 
        status: 'error', 
        error: (error as Error).message 
      };
      appStore.setSystemStatus(errorStatus);
    }
  }

  async getResourcesSummary() {
    try {
      return await apiClient.getResourcesSummary();
    } catch (error) {
      console.error('Failed to get resources summary:', error);
      throw error;
    }
  }

  getSystemStatus(): SystemStatus | null {
    return appStore.getState().systemStatus;
  }

  isSystemHealthy(): boolean {
    const status = this.getSystemStatus();
    return status?.status === 'healthy';
  }
}

export const systemService = new SystemService();