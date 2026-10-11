/**
 * Token storage.
 *
 * On Android the token lives in Capacitor Preferences, which is backed by the
 * app's private SharedPreferences - not reachable by other apps and not part of
 * the web origin's localStorage. On the web (dev and browser preview) it falls
 * back to localStorage.
 *
 * To upgrade to OS-level encryption later, swap the native branch for a secure
 * storage plugin (e.g. EncryptedSharedPreferences): the rest of the app only
 * uses the four functions below.
 */

import { Capacitor } from '@capacitor/core';
import { Preferences } from '@capacitor/preferences';

const TOKEN_KEY = 'fieldsales.token';
const native = Capacitor.isNativePlatform();

let cachedToken: string | null = null;

export async function loadToken(): Promise<string | null> {
  if (cachedToken) return cachedToken;
  try {
    if (native) {
      const { value } = await Preferences.get({ key: TOKEN_KEY });
      cachedToken = value ?? null;
    } else {
      cachedToken = window.localStorage.getItem(TOKEN_KEY);
    }
  } catch {
    cachedToken = null;
  }
  return cachedToken;
}

export async function saveToken(token: string): Promise<void> {
  cachedToken = token;
  try {
    if (native) {
      await Preferences.set({ key: TOKEN_KEY, value: token });
    } else {
      window.localStorage.setItem(TOKEN_KEY, token);
    }
  } catch {
    /* keep the in-memory token so the session still works */
  }
}

export async function clearToken(): Promise<void> {
  cachedToken = null;
  try {
    if (native) {
      await Preferences.remove({ key: TOKEN_KEY });
    } else {
      window.localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    /* ignore */
  }
}

export function peekToken(): string | null {
  return cachedToken;
}

/** Small key/value helper for non-sensitive local state (the offline outbox). */
export const localJson = {
  read<T>(key: string, fallback: T): T {
    try {
      const raw = window.localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : fallback;
    } catch {
      return fallback;
    }
  },
  write(key: string, value: unknown): void {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* storage full or blocked - the UI still works, just without persistence */
    }
  },
};
