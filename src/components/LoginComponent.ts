import { BaseComponent } from './BaseComponent';
import { authService } from '../services/AuthService';
import { $, $$, addEventListener, show, hide } from '../utils/dom';

export class LoginComponent extends BaseComponent {
  private isRegisterMode = false;

  protected render(): string {
    return `
      <div class="login-container">
        <div class="login-card">
          <div class="login-header">
            <h1><i class="fas fa-calendar-alt"></i> Resource Reservation</h1>
            <p>Please sign in to your account</p>
          </div>
          
          <div class="auth-tabs">
            <button class="auth-tab active" data-tab="login">Sign In</button>
            <button class="auth-tab" data-tab="register">Register</button>
          </div>

          <form id="authForm">
            <div class="form-group">
              <label class="form-label">Username</label>
              <input type="text" class="form-input" name="username" required>
            </div>
            
            <div class="form-group">
              <label class="form-label">Password</label>
              <input type="password" class="form-input" name="password" required>
            </div>
            
            <div class="form-group hidden" id="confirmPasswordGroup">
              <label class="form-label">Confirm Password</label>
              <input type="password" class="form-input" name="confirmPassword">
            </div>
            
            <div id="authError" class="alert alert-error hidden"></div>
            
            <button type="submit" class="btn btn-primary" style="width: 100%;" id="authSubmit">
              Sign In
            </button>
          </form>
        </div>
      </div>
    `;
  }

  protected bindEvents(): void {
    const form = $('#authForm') as HTMLFormElement;
    const authTabs = $$('.auth-tab');
    
    // Tab switching
    authTabs.forEach((tab: Element) => {
      addEventListener(tab as HTMLElement, 'click', (e) => {
        e.preventDefault();
        const tabType = (tab as HTMLElement).dataset.tab;
        this.switchTab(tabType === 'register');
      });
    });

    // Form submission
    addEventListener(form, 'submit', (e) => {
      e.preventDefault();
      this.handleAuth();
    });
  }

  private switchTab(isRegister: boolean): void {
    this.isRegisterMode = isRegister;
    
    const tabs = $$('.auth-tab');
    tabs.forEach((tab: Element) => tab.classList.remove('active'));
    
    const activeTab = $(`.auth-tab[data-tab="${isRegister ? 'register' : 'login'}"]`);
    activeTab?.classList.add('active');

    const confirmGroup = $('#confirmPasswordGroup');
    const submitBtn = $('#authSubmit');

    if (isRegister) {
      show(confirmGroup);
      if (submitBtn) submitBtn.textContent = 'Register';
    } else {
      hide(confirmGroup);
      if (submitBtn) submitBtn.textContent = 'Sign In';
    }
  }

  private async handleAuth(): Promise<void> {
    const form = $('#authForm') as HTMLFormElement;
    const formData = new FormData(form);
    const username = formData.get('username') as string;
    const password = formData.get('password') as string;
    const confirmPassword = formData.get('confirmPassword') as string;

    const errorDiv = $('#authError');
    const submitBtn = $('#authSubmit') as HTMLButtonElement;

    hide(errorDiv);

    if (this.isRegisterMode && password !== confirmPassword) {
      this.showError('Passwords do not match');
      return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

    try {
      if (this.isRegisterMode) {
        await authService.register(username, password);
        this.switchTab(false);
        form.reset();
      } else {
        await authService.login(username, password);
      }
    } catch (error) {
      this.showError((error as Error).message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = this.isRegisterMode ? 'Register' : 'Sign In';
    }
  }

  private showError(message: string): void {
    const errorDiv = $('#authError');
    if (errorDiv) {
      errorDiv.textContent = message;
      show(errorDiv);
    }
  }
}