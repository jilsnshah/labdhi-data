import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { ApiError, api, setUnauthorizedHandler } from '@/api/client';
import type { LoginResponse, Profile } from '@/api/types';
import { clearToken, loadToken, saveToken } from './storage';

interface AuthValue {
  profile: Profile | null;
  restoring: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

/** This app is for field accounts only - a desk/admin login is refused here. */
export class WrongAppError extends Error {}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [restoring, setRestoring] = useState(true);

  useEffect(() => {
    setUnauthorizedHandler(() => setProfile(null));
    let cancelled = false;
    (async () => {
      const token = await loadToken();
      if (!token) {
        if (!cancelled) setRestoring(false);
        return;
      }
      try {
        const me = await api.get<Profile>('/salesperson/me');
        if (!cancelled) setProfile(me);
      } catch (error) {
        // Keep the session on a network error so the app still opens offline.
        if (error instanceof ApiError && !error.offline) {
          await clearToken();
        }
      } finally {
        if (!cancelled) setRestoring(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await api.post<LoginResponse>('/auth/login', { email, password });
    if (result.user.role !== 'SALESPERSON') {
      throw new WrongAppError(
        'This app is for field salespeople. Use the web CRM with an office account.',
      );
    }
    await saveToken(result.token.access_token);
    const me = await api.get<Profile>('/salesperson/me');
    setProfile(me);
  }, []);

  const signOut = useCallback(async () => {
    await clearToken();
    setProfile(null);
  }, []);

  const value = useMemo(
    () => ({ profile, restoring, signIn, signOut }),
    [profile, restoring, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>');
  return context;
}
