export function $(selector: string): HTMLElement | null {
  return document.querySelector(selector);
}

export function $$(selector: string): NodeListOf<Element> {
  return document.querySelectorAll(selector);
}

export function createElement<K extends keyof HTMLElementTagNameMap>(
  tagName: K,
  attributes?: Partial<HTMLElementTagNameMap[K]> & { [key: string]: any },
  children?: (HTMLElement | string)[]
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tagName);
  
  if (attributes) {
    Object.entries(attributes).forEach(([key, value]) => {
      if (key === 'className') {
        element.className = value as string;
      } else if (key === 'innerHTML') {
        element.innerHTML = value as string;
      } else if (key === 'textContent') {
        element.textContent = value as string;
      } else if (key.startsWith('on') && typeof value === 'function') {
        (element as any)[key] = value;
      } else {
        element.setAttribute(key, String(value));
      }
    });
  }

  if (children) {
    children.forEach(child => {
      if (typeof child === 'string') {
        element.appendChild(document.createTextNode(child));
      } else {
        element.appendChild(child);
      }
    });
  }

  return element;
}

export function removeElement(element: HTMLElement | null): void {
  element?.parentNode?.removeChild(element);
}

export function show(element: HTMLElement | null): void {
  element?.classList.remove('hidden');
}

export function hide(element: HTMLElement | null): void {
  element?.classList.add('hidden');
}

export function toggleClass(element: HTMLElement | null, className: string): void {
  element?.classList.toggle(className);
}

export function addClass(element: HTMLElement | null, className: string): void {
  element?.classList.add(className);
}

export function removeClass(element: HTMLElement | null, className: string): void {
  element?.classList.remove(className);
}

export function setContent(element: HTMLElement | null, content: string): void {
  if (element) {
    element.innerHTML = content;
  }
}

export function appendContent(element: HTMLElement | null, content: string): void {
  if (element) {
    element.innerHTML += content;
  }
}

export function addEventListener<K extends keyof HTMLElementEventMap>(
  element: HTMLElement | null,
  type: K,
  listener: (this: HTMLElement, ev: HTMLElementEventMap[K]) => any,
  options?: boolean | AddEventListenerOptions
): void {
  element?.addEventListener(type, listener, options);
}

export function delegate<K extends keyof HTMLElementEventMap>(
  parent: HTMLElement | null,
  selector: string,
  type: K,
  handler: (event: HTMLElementEventMap[K], target: HTMLElement) => void
): void {
  if (!parent) return;
  
  parent.addEventListener(type, (event) => {
    const target = (event.target as HTMLElement)?.closest(selector) as HTMLElement;
    if (target) {
      handler(event, target);
    }
  });
}