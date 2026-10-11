/** Thin fetch wrapper: bearer auth, query strings and structured API errors. */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) ?? 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'trader_crm_token';

export class ApiError extends Error {
  status: number;
  code: string;
  field?: string;
  details?: Record<string, unknown>;

  constructor(
    status: number,
    message: string,
    code = 'error',
    field?: string,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.field = field;
    this.details = details;
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export type QueryValue = string | number | boolean | null | undefined | (string | number)[];

export function buildQuery(params?: Record<string, QueryValue>): string {
  if (!params) return '';
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    if (Array.isArray(value)) {
      value.forEach((item) => search.append(key, String(item)));
    } else {
      search.append(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  body?: unknown;
  params?: Record<string, QueryValue>;
  signal?: AbortSignal;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, params, signal } = options;
  const token = tokenStore.get();
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}${buildQuery(params)}`, {
      method,
      signal,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    // Distinguish "server unreachable / CORS" from a real HTTP error.
    throw new ApiError(
      0,
      navigator.onLine === false
        ? 'No internet connection.'
        : `Cannot reach the API at ${BASE_URL}. Is the backend running, and is this origin ` +
          'listed in CORS_ORIGINS?',
      'network_error',
    );
  }

  if (response.status === 204) return undefined as T;

  let payload: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { error: { message: text } };
    }
  }

  if (!response.ok) {
    const error = (payload as { error?: Record<string, unknown> } | null)?.error ?? {};
    const message =
      (error.message as string) ??
      (response.status === 401 ? 'Please sign in again.' : 'Something went wrong.');
    if (response.status === 401) tokenStore.clear();
    throw new ApiError(
      response.status,
      message,
      (error.code as string) ?? 'error',
      error.field as string | undefined,
      error.details as Record<string, unknown> | undefined,
    );
  }

  return payload as T;
}

export const api = {
  get: <T>(path: string, params?: Record<string, QueryValue>, signal?: AbortSignal) =>
    request<T>(path, { params, signal }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};
