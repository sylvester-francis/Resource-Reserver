import { AppController } from './AppController';
import './styles/animations.css';

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  const app = new AppController();
  app.initialize();
});