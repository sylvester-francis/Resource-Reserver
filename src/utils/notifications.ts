import type { NotificationType } from '../types';
import { createElement, removeElement } from './dom';

export function showNotification(message: string, type: NotificationType['type']): void {
  const notification = createElement('div', {
    className: `alert alert-${type}`,
    innerHTML: `
      <div class="flex items-center gap-2">
        <i class="fas fa-${getIcon(type)}"></i>
        ${message}
      </div>
    `
  });

  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1001;
    max-width: 400px;
    animation: slideIn 0.3s ease-out;
  `;

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-in';
    setTimeout(() => {
      removeElement(notification);
    }, 300);
  }, 5000);
}

function getIcon(type: NotificationType['type']): string {
  switch (type) {
    case 'success': return 'check-circle';
    case 'error': return 'times-circle';
    case 'warning': return 'exclamation-triangle';
    case 'info': return 'info-circle';
    default: return 'info-circle';
  }
}