import { apiClient } from '../api/client';
import { appStore } from '../stores/AppStore';
import type { Resource, SearchParams } from '../types';
import { showNotification } from '../utils/notifications';

export class ResourceService {
  async loadResources(): Promise<void> {
    try {
      const resources = await apiClient.getResources();
      appStore.setResources(resources);
    } catch (error) {
      console.error('Failed to load resources:', error);
      showNotification('Failed to load resources: ' + (error as Error).message, 'error');
      throw error;
    }
  }

  async searchResources(params: SearchParams): Promise<Resource[]> {
    try {
      const results = await apiClient.searchResources(params);
      appStore.setFilteredResources(results);
      return results;
    } catch (error) {
      console.error('Failed to search resources:', error);
      throw error;
    }
  }

  async createResource(name: string, tags: string[], available: boolean): Promise<void> {
    try {
      await apiClient.createResource(name, tags, available);
      await this.loadResources(); // Refresh the list
      showNotification('Resource created successfully', 'success');
    } catch (error) {
      console.error('Failed to create resource:', error);
      throw error;
    }
  }

  async uploadCsv(file: File): Promise<void> {
    try {
      const result = await apiClient.uploadResourcesCsv(file);
      await this.loadResources(); // Refresh the list
      
      let message = `Successfully created ${result.created_count} resources`;
      if (result.errors && result.errors.length > 0) {
        message += ` (${result.errors.length} errors)`;
      }
      showNotification(message, 'success');
    } catch (error) {
      console.error('Failed to upload CSV:', error);
      throw error;
    }
  }

  async getResourceAvailability(resourceId: number, daysAhead = 7) {
    try {
      return await apiClient.getResourceAvailability(resourceId, daysAhead);
    } catch (error) {
      console.error('Failed to get resource availability:', error);
      throw error;
    }
  }

  getResourceById(id: number): Resource | undefined {
    const state = appStore.getState();
    return state.resources.find(r => r.id === id);
  }

  filterResources(query: string, filter: 'all' | 'available' | 'unavailable'): void {
    appStore.setSearchQuery(query);
    appStore.setFilter(filter);
  }

  setPage(page: number): void {
    appStore.setPage(page);
  }

  setItemsPerPage(items: number): void {
    appStore.setItemsPerPage(items);
  }

  getPaginatedResources(): Resource[] {
    return appStore.getPaginatedResources();
  }
}

export const resourceService = new ResourceService();