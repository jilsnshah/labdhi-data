import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { api, tokenStore } from '@/api/client';
import type { LoginResponse, User } from '@/api/types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(tokenStore.get()));

  useEffect(() => {
    if (!tokenStore.get()) return;
    let cancelled = false;
    // Renew on the way in, so a desk that is opened every morning is never
    // asked to sign in again; only a session left alone for a month lapses.
    api
      .post<LoginResponse>('/auth/refresh')
      .then((result) => {
        tokenStore.set(result.token.access_token);
        if (!cancelled) setUser(result.user);
      })
      .catch(() => {
        tokenStore.clear();
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await api.post<LoginResponse>('/auth/login', { email, password });
    tokenStore.set(result.token.access_token);
    setUser(result.user);
  }, []);

  const signOut = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    window.location.href = '/login';
  }, []);

  const value = useMemo(
    () => ({ user, loading, signIn, signOut }),
    [user, loading, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>');
  return context;
}
