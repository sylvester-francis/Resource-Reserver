import { BaseComponent } from '../BaseComponent';
import { appStore } from '../../stores/AppStore';
import { resourceService } from '../../services/ResourceService';
import { delegate, $ } from '../../utils/dom';
import { padResourceId } from '../../utils/formatting';
import type { Resource } from '../../types';

export class ResourcesTabComponent extends BaseComponent {
  protected render(): string {
    const state = appStore.getState();
    const paginatedResources = resourceService.getPaginatedResources();

    return `
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">
            <i class="fas fa-cube"></i> Resources
          </h2>
        </div>
        
        <div class="flex gap-2 mb-4">
          <button class="btn btn-outline btn-sm" data-action="time-search">
            <i class="fas fa-search"></i> Time Search
          </button>
          <button class="btn btn-success btn-sm" data-action="create-resource">
            <i class="fas fa-plus"></i> Add Resource
          </button>
          <button class="btn btn-primary btn-sm" data-action="upload-csv">
            <i class="fas fa-upload"></i> Upload CSV
          </button>
          <button class="btn btn-outline btn-sm" data-action="refresh">
            <i class="fas fa-sync-alt"></i> Refresh
          </button>
        </div>

        <div class="search-container">
          <input type="text" class="form-input search-input" placeholder="Search resources..." 
                 value="${state.searchQuery}" id="searchInput">
          <i class="fas fa-search search-icon"></i>
        </div>

        <div class="filters mb-4">
          <div class="filter-chip ${state.currentFilter === 'all' ? 'active' : ''}" data-filter="all">
            <i class="fas fa-list"></i> All
          </div>
          <div class="filter-chip ${state.currentFilter === 'available' ? 'active' : ''}" data-filter="available">
            <i class="fas fa-check-circle"></i> Available
          </div>
          <div class="filter-chip ${state.currentFilter === 'unavailable' ? 'active' : ''}" data-filter="unavailable">
            <i class="fas fa-times-circle"></i> Unavailable
          </div>
        </div>

        <div class="mb-4 flex justify-between items-center">
          <span>Showing ${paginatedResources.length} of ${state.filteredResources.length} resources</span>
          <div class="flex items-center gap-2">
            <label style="font-size: 0.875rem; color: var(--text-secondary);">Show:</label>
            <select class="pagination-select" id="itemsPerPageSelect">
              <option value="5" ${state.itemsPerPage === 5 ? 'selected' : ''}>5</option>
              <option value="10" ${state.itemsPerPage === 10 ? 'selected' : ''}>10</option>
              <option value="25" ${state.itemsPerPage === 25 ? 'selected' : ''}>25</option>
              <option value="50" ${state.itemsPerPage === 50 ? 'selected' : ''}>50</option>
            </select>
            <span style="font-size: 0.875rem; color: var(--text-secondary);">per page</span>
          </div>
        </div>

        ${state.filteredResources.length === 0 ? this.renderEmptyState() : this.renderResourcesList()}
      </div>
    `;
  }

  private renderEmptyState(): string {
    const state = appStore.getState();
    return `
      <div class="empty-state">
        <i class="fas fa-cube"></i>
        <h3>No resources found</h3>
        <p>${state.searchQuery || state.currentFilter !== 'all' ? 'Try adjusting your search or filters' : 'Get started by adding your first resource'}</p>
        <button class="btn btn-primary" data-action="create-resource">
          Add Your First Resource
        </button>
      </div>
    `;
  }

  private renderResourcesList(): string {
    const state = appStore.getState();
    const paginatedResources = resourceService.getPaginatedResources();

    return `
      <div class="resources-list">
        ${paginatedResources.map(resource => this.renderResourceItem(resource)).join('')}
      </div>
      ${state.totalPages > 1 ? this.renderPagination() : ''}
    `;
  }

  private renderResourceItem(resource: Resource): string {
    return `
      <div class="resource-list-item">
        <div class="resource-list-avatar">
          ${resource.name.charAt(0).toUpperCase()}
        </div>
        
        <div class="resource-list-content">
          <div class="resource-list-header">
            <h3 class="resource-list-title">${resource.name}</h3>
            <div class="resource-list-id">${padResourceId(resource.id)}</div>
          </div>
          
          <div class="resource-list-meta">
            <span class="resource-list-status ${resource.available ? 'available' : 'unavailable'}">
              <i class="fas fa-${resource.available ? 'check' : 'times'}-circle"></i>
              ${resource.available ? 'Available' : 'Unavailable'}
            </span>
            
            ${resource.tags.length > 0 ? `
              <div class="resource-list-tags">
                ${resource.tags.slice(0, 4).map(tag => `<span class="resource-tag">${tag}</span>`).join('')}
                ${resource.tags.length > 4 ? `<span class="resource-tag" style="background: var(--warning-color); color: white;">+${resource.tags.length - 4}</span>` : ''}
              </div>
            ` : `
              <div class="resource-list-tags">
                <span class="resource-tag" style="opacity: 0.5;">No tags</span>
              </div>
            `}
          </div>
        </div>
        
        <div class="resource-list-actions">
          <button class="btn-list-reserve" 
                  ${!resource.available ? 'disabled' : ''} 
                  data-action="reserve" 
                  data-resource-id="${resource.id}">
            <i class="fas fa-calendar-plus"></i>
            ${resource.available ? 'Reserve' : 'Unavailable'}
          </button>
          <button class="btn btn-outline btn-sm" 
                  data-action="show-availability" 
                  data-resource-id="${resource.id}">
            <i class="fas fa-calendar-alt"></i>
          </button>
        </div>
      </div>
    `;
  }

  private renderPagination(): string {
    const state = appStore.getState();
    const { currentPage, totalPages, itemsPerPage, filteredResources } = state;
    const pageNumbers: number[] = [];
    const maxVisiblePages = 5;
    
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage < maxVisiblePages - 1) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pageNumbers.push(i);
    }

    return `
      <div class="pagination-container">
        <div class="pagination-info">
          <span>
            Showing ${(currentPage - 1) * itemsPerPage + 1} to ${Math.min(currentPage * itemsPerPage, filteredResources.length)} 
            of ${filteredResources.length} resources
          </span>
        </div>

        <div class="pagination-controls">
          <div class="pagination-nav">
            <button class="pagination-btn" 
                    data-action="first-page"
                    ${currentPage === 1 ? 'disabled' : ''}>
              <i class="fas fa-angle-double-left"></i>
            </button>
            <button class="pagination-btn" 
                    data-action="prev-page"
                    ${currentPage === 1 ? 'disabled' : ''}>
              <i class="fas fa-angle-left"></i>
            </button>

            ${startPage > 1 ? `
              <button class="pagination-btn" data-action="goto-page" data-page="1">1</button>
              ${startPage > 2 ? '<span style="padding: 0 var(--space-2);">...</span>' : ''}
            ` : ''}

            ${pageNumbers.map(page => `
              <button class="pagination-btn ${page === currentPage ? 'active' : ''}" 
                      data-action="goto-page" 
                      data-page="${page}">
                ${page}
              </button>
            `).join('')}

            ${endPage < totalPages ? `
              ${endPage < totalPages - 1 ? '<span style="padding: 0 var(--space-2);">...</span>' : ''}
              <button class="pagination-btn" data-action="goto-page" data-page="${totalPages}">${totalPages}</button>
            ` : ''}

            <button class="pagination-btn" 
                    data-action="next-page"
                    ${currentPage === totalPages ? 'disabled' : ''}>
              <i class="fas fa-angle-right"></i>
            </button>
            <button class="pagination-btn" 
                    data-action="last-page"
                    ${currentPage === totalPages ? 'disabled' : ''}>
              <i class="fas fa-angle-double-right"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  protected bindEvents(): void {
    // Search input
    const searchInput = $('#searchInput') as HTMLInputElement;
    if (searchInput) {
      let searchTimeout: NodeJS.Timeout;
      searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
          resourceService.filterResources(searchInput.value, appStore.getState().currentFilter);
        }, 300);
      });
    }

    // Items per page selector
    const itemsSelect = $('#itemsPerPageSelect') as HTMLSelectElement;
    if (itemsSelect) {
      itemsSelect.addEventListener('change', () => {
        resourceService.setItemsPerPage(parseInt(itemsSelect.value));
      });
    }

    // Filter chips
    delegate(this.container, '.filter-chip', 'click', (e, target) => {
      const filter = target.dataset.filter as 'all' | 'available' | 'unavailable';
      if (filter) {
        resourceService.filterResources(appStore.getState().searchQuery, filter);
      }
    });

    // Pagination buttons
    delegate(this.container, '[data-action="first-page"]', 'click', () => {
      resourceService.setPage(1);
    });

    delegate(this.container, '[data-action="last-page"]', 'click', () => {
      resourceService.setPage(appStore.getState().totalPages);
    });

    delegate(this.container, '[data-action="prev-page"]', 'click', () => {
      const currentPage = appStore.getState().currentPage;
      resourceService.setPage(currentPage - 1);
    });

    delegate(this.container, '[data-action="next-page"]', 'click', () => {
      const currentPage = appStore.getState().currentPage;
      resourceService.setPage(currentPage + 1);
    });

    delegate(this.container, '[data-action="goto-page"]', 'click', (e, target) => {
      const page = parseInt(target.dataset.page || '1');
      resourceService.setPage(page);
    });

    // Action buttons
    delegate(this.container, '[data-action="refresh"]', 'click', async () => {
      await resourceService.loadResources();
    });

    delegate(this.container, '[data-action="reserve"]', 'click', (e, target) => {
      const resourceId = parseInt(target.dataset.resourceId || '0');
      if (resourceId) {
        // TODO: Show reservation modal
        console.log('Show reservation modal for resource', resourceId);
      }
    });

    delegate(this.container, '[data-action="show-availability"]', 'click', (e, target) => {
      const resourceId = parseInt(target.dataset.resourceId || '0');
      if (resourceId) {
        // TODO: Show availability modal
        console.log('Show availability for resource', resourceId);
      }
    });

    delegate(this.container, '[data-action="time-search"]', 'click', () => {
      // TODO: Show time search modal
      console.log('Show time search modal');
    });

    delegate(this.container, '[data-action="create-resource"]', 'click', () => {
      // TODO: Show create resource modal
      console.log('Show create resource modal');
    });

    delegate(this.container, '[data-action="upload-csv"]', 'click', () => {
      // TODO: Show upload CSV modal
      console.log('Show upload CSV modal');
    });
  }
}