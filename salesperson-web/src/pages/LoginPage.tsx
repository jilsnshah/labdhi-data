import { useState } from 'react';

import { ApiError } from '@/api/client';
import { Icon } from '@/components/Icon';
import { WrongAppError, useAuth } from '@/lib/auth';

export function LoginPage() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
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
      <div className="login-glow" aria-hidden />
      <svg className="login-contours" viewBox="0 0 400 300" preserveAspectRatio="none" aria-hidden>
        {Array.from({ length: 9 }).map((_, index) => (
          <path
            key={index}
            d={`M-20 ${70 + index * 26} C 90 ${20 + index * 30}, 210 ${130 + index * 18}, 420 ${
              50 + index * 28
            }`}
          />
        ))}
      </svg>

      <div className="login-top">
        <span className="brand-mark">L</span>
        <div>
          <div className="brand-word">Labdhi</div>
          <div className="brand-sub">Field desk</div>
        </div>
      </div>

      <div className="login-hero">
        <h1>
          Every visit,
          <br />
          every call, <em>on record.</em>
        </h1>
        <p>Your day from the trade desk - and a place to log the deals you find on your own.</p>
      </div>

      <form className="login-card" onSubmit={submit}>
        {error && (
          <div className="login-error">
            <Icon name="offline" size={16} />
            <span>{error}</span>
          </div>
        )}
        <label className="field">
          <span>Email</span>
          <input
            type="email"
            inputMode="email"
            autoCapitalize="none"
            autoCorrect="off"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.currentTarget.value)}
            placeholder="you@company.in"
          />
        </label>
        <label className="field">
          <span>Password</span>
          <div className="input-with-action">
            <input
              type={show ? 'text' : 'password'}
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.currentTarget.value)}
            />
            <button type="button" className="link-btn" onClick={() => setShow((value) => !value)}>
              {show ? 'Hide' : 'Show'}
            </button>
          </div>
        </label>
        <button className="btn brass" type="submit" disabled={busy || !email || !password}>
          {busy ? (
            'Signing in…'
          ) : (
            <>
              Sign in <Icon name="arrow" size={17} />
            </>
          )}
        </button>
        <div className="tiny login-foot">Field accounts only · office staff use the web desk</div>
      </form>
    </div>
  );
}
