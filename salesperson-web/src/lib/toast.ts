/** A single transient message at the bottom of the screen, readable from anywhere. */

export interface Toast {
  id: number;
  message: string;
  tone: 'ok' | 'warn' | 'error';
}

type Listener = (toast: Toast | null) => void;
const listeners = new Set<Listener>();
let current: Toast | null = null;
let timer: ReturnType<typeof setTimeout> | undefined;

export function toast(message: string, tone: Toast['tone'] = 'ok'): void {
  current = { id: Date.now(), message, tone };
  listeners.forEach((listener) => listener(current));
  clearTimeout(timer);
  timer = setTimeout(() => {
    current = null;
    listeners.forEach((listener) => listener(null));
  }, 3600);
}

export function subscribeToast(listener: Listener): () => void {
  listeners.add(listener);
  listener(current);
  return () => listeners.delete(listener);
}
