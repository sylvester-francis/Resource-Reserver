import { $, setContent } from '../utils/dom';

export abstract class BaseComponent {
  protected container: HTMLElement | null = null;

  constructor(protected containerId: string) {
    this.container = $(containerId);
  }

  protected abstract render(): string;

  public mount(): void {
    if (!this.container) {
      throw new Error(`Container with id ${this.containerId} not found`);
    }
    setContent(this.container, this.render());
    this.bindEvents();
  }

  protected bindEvents(): void {
    // Override in subclasses
  }

  public unmount(): void {
    if (this.container) {
      this.container.innerHTML = '';
    }
  }
}