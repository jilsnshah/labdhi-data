import { useState } from 'react';

import { ApiError } from '@/api/client';
import { Banner } from '@/components/Shell';
import { WrongAppError, useAuth } from '@/lib/auth';

export function LoginPage() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await signIn(email.trim(), password);
    } catch (err) {
      if (err instanceof WrongAppError) setError(err.message);
      else if (err instanceof ApiError) setError(err.message);
      else setError('Could not sign in.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <div className="brand">
        <div className="logo">📍</div>
        <h1>Field Sales</h1>
        <p>Your work for today, from the trade desk</p>
      </div>
      <form onSubmit={submit}>
        {error && <Banner kind="error">{error}</Banner>}
        <label className="field">
          <span>Email</span>
          <input
            type="email"
            inputMode="email"
            autoCapitalize="none"
            autoCorrect="off"
            required
            value={email}
            onChange={(event) => setEmail(event.currentTarget.value)}
            placeholder="you@company.in"
          />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            type="password"
            required
            value={password}
            onChange={(event) => setPassword(event.currentTarget.value)}
          />
        </label>
        <button className="btn" type="submit" disabled={busy || !email || !password}>
          {busy ? 'Signing in…' : 'Login'}
        </button>
      </form>
    </div>
  );
}
