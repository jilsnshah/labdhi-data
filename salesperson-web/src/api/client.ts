/** Fetch wrapper: bearer token from secure storage, typed errors, offline detection. */

import { clearToken, loadToken } from '@/lib/storage';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) ?? 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  status: number;
  code: string;
  field?: string;
  /** True when the request never reached the server (no network, DNS, timeout). */
  offline: boolean;

  constructor(status: number, message: string, code = 'error', offline = false, field?: string) {
    super(message);
    this.status = status;
    this.code = code;
    this.offline = offline;
    this.field = field;
  }
}

type Method = 'GET' | 'POST' | 'PATCH';

let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

export async function request<T>(
  path: string,
  options: { method?: Method; body?: unknown; timeoutMs?: number } = {},
): Promise<T> {
  const { method = 'GET', body, timeoutMs = 15000 } = options;
  const token = await loadToken();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      signal: controller.signal,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    const aborted = error instanceof DOMException && error.name === 'AbortError';
    // A failed fetch looks the same whether the phone is offline or the server
    // is unreachable (wrong API address, backend down, CORS not configured), so
    // use the connectivity state to say something the user can act on.
    const connected = typeof navigator === 'undefined' || navigator.onLine !== false;
    const message = aborted
      ? 'The network is slow right now. Your work is saved on this phone and will sync.'
      : connected
      ? `Cannot reach the server at ${BASE_URL}. Check that the app points at the right ` +
        'address and that the server allows this app.'
      : 'No internet connection.';
    throw new ApiError(0, message, 'offline', true);
  } finally {
    clearTimeout(timer);
  }

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { error: { message: text } };
    }
  }

  if (!response.ok) {
    const error = (payload as { error?: Record<string, unknown> } | null)?.error ?? {};
    if (response.status === 401) {
      await clearToken();
      onUnauthorized?.();
    }
    throw new ApiError(
      response.status,
      (error.message as string) ?? 'Something went wrong.',
      (error.code as string) ?? 'error',
      false,
      error.field as string | undefined,
    );
  }

  return payload as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
};
