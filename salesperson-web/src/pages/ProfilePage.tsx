import { useState } from 'react';
import { Link } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { useChangePassword } from '@/api/hooks';
import { Banner, Screen, Sheet } from '@/components/Shell';
import { useAuth } from '@/lib/auth';
import { isNative } from '@/lib/native';
import * as outbox from '@/lib/offline';

export function ProfilePage() {
  const { profile, signOut } = useAuth();
  const [sheet, setSheet] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const queued = outbox.pending();

  return (
    <Screen title="Profile" subtitle={profile?.email}>
      {notice && <Banner kind="info">{notice}</Banner>}
      <div className="card">
        <div className="section-title" style={{ marginTop: 0 }}>
          Account
        </div>
        <Row label="Name" value={profile?.name ?? '-'} />
        <Row label="Phone" value={profile?.phone ?? '-'} />
        <Row label="Email" value={profile?.email ?? '-'} />
        <Row label="Role" value="Salesperson" />
      </div>

      <div className="card">
        <div className="section-title" style={{ marginTop: 0 }}>
          My work
        </div>
        <Link className="btn secondary" to="/history">
          Completed activities
        </Link>
        {queued.length > 0 && (
          <div className="small muted" style={{ marginTop: 10 }}>
            {queued.length} report{queued.length > 1 ? 's' : ''} waiting to sync.{' '}
            <button
              className="btn ghost"
              onClick={async () => {
                const synced = await outbox.flush();
                setNotice(
                  synced > 0 ? `${synced} report(s) synced.` : 'Still offline, will retry later.',
                );
              }}
            >
              Retry now
            </button>
          </div>
        )}
      </div>

      <div className="card">
        <div className="section-title" style={{ marginTop: 0 }}>
          Security
        </div>
        <button className="btn secondary" onClick={() => setSheet(true)}>
          Change password
        </button>
        <button className="btn danger" style={{ marginTop: 10 }} onClick={() => signOut()}>
          Log out
        </button>
        <div className="tiny muted" style={{ marginTop: 10 }}>
          {isNative
            ? 'Your session is kept in the app’s private storage on this phone.'
            : 'Running in a browser - the session is kept in this browser only.'}
        </div>
      </div>

      {sheet && (
        <ChangePasswordSheet
          onClose={() => setSheet(false)}
          onDone={(message) => {
            setNotice(message);
            setSheet(false);
          }}
        />
      )}
    </Screen>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="kv">
      <span className="k">{label}</span>
      <span className="v">{value}</span>
    </div>
  );
}

function ChangePasswordSheet({
  onClose,
  onDone,
}: {
  onClose: () => void;
  onDone: (message: string) => void;
}) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [error, setError] = useState<string | null>(null);
  const change = useChangePassword();

  const submit = async () => {
    setError(null);
    try {
      await change.mutateAsync({ current_password: current, new_password: next });
      onDone('Password updated.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not change the password.');
    }
  };

  return (
    <Sheet title="Change password" onClose={onClose}>
      {error && <Banner kind="error">{error}</Banner>}
      <label className="field">
        <span>Current password</span>
        <input
          type="password"
          value={current}
          onChange={(event) => setCurrent(event.currentTarget.value)}
        />
      </label>
      <label className="field">
        <span>New password (min 6 characters)</span>
        <input
          type="password"
          value={next}
          onChange={(event) => setNext(event.currentTarget.value)}
        />
      </label>
      <div className="btn-row">
        <button className="btn secondary" onClick={onClose}>
          Cancel
        </button>
        <button
          className="btn"
          onClick={submit}
          disabled={change.isPending || !current || next.length < 6}
        >
          {change.isPending ? 'Saving…' : 'Update'}
        </button>
      </div>
    </Sheet>
  );
}
