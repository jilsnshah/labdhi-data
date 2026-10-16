import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { useChangePassword, useRefreshAll, useStats } from '@/api/hooks';
import type { FieldStats } from '@/api/types';
import { FelesCredit } from '@/components/FelesCredit';
import { Icon, type IconName } from '@/components/Icon';
import { Avatar, Banner, Screen, SectionTitle, Sheet } from '@/components/Shell';
import { useAuth } from '@/lib/auth';
import { dayjs } from '@/lib/format';
import { isNative } from '@/lib/native';
import * as outbox from '@/lib/offline';
import { toast } from '@/lib/toast';

export function ProfilePage() {
  const { profile, signOut } = useAuth();
  const { data: stats } = useStats();
  const refresh = useRefreshAll();
  const [sheet, setSheet] = useState(false);
  const [queued, setQueued] = useState(outbox.pending());

  useEffect(() => outbox.subscribe(setQueued), []);

  return (
    <Screen
      eyebrow="Field salesperson"
      title={profile?.name ?? 'Me'}
      subtitle={profile?.email}
      action={<Avatar name={profile?.name ?? '?'} size={46} tone="brass" />}
      hero={stats ? <WeekChart stats={stats} /> : undefined}
    >
      {stats && (
        <>
          <SectionTitle aside="Last 7 days">My week</SectionTitle>
          <div className="kpi-grid">
            <Kpi icon="check" value={stats.completed_7d} label="Completed" tone="teal" />
            <Kpi icon="pin" value={stats.visits_7d} label="Visits" tone="brass" />
            <Kpi icon="phone" value={stats.calls_7d} label="Calls" tone="indigo" />
            <Kpi icon="bolt" value={stats.self_logged_7d} label="Self-logged" tone="brass" />
            <Kpi icon="userPlus" value={stats.new_contacts_7d} label="New prospects" tone="teal" />
            <Kpi
              icon="clock"
              value={stats.on_time_rate == null ? '–' : `${Math.round(stats.on_time_rate * 100)}%`}
              label="On time"
              tone="slate"
            />
          </div>
        </>
      )}

      {queued.length > 0 && (
        <Banner kind="warn">
          <strong>
            {queued.length} report{queued.length > 1 ? 's' : ''} waiting to sync.
          </strong>
          <div style={{ marginTop: 8 }}>
            <button
              className="btn small ghost"
              onClick={async () => {
                const synced = await outbox.flush();
                if (synced > 0) {
                  refresh();
                  toast(`${synced} report${synced > 1 ? 's' : ''} synced.`);
                } else {
                  toast('Still offline - will retry by itself.', 'warn');
                }
              }}
            >
              <Icon name="refresh" size={15} /> Retry now
            </button>
          </div>
        </Banner>
      )}

      <SectionTitle>Work</SectionTitle>
      <div className="menu">
        <Link to="/history" className="menu-row">
          <span className="menu-icon">
            <Icon name="history" size={19} />
          </span>
          <span className="grow">Completed activities</span>
          <Icon name="chevron" size={17} />
        </Link>
        <Link to="/log" className="menu-row">
          <span className="menu-icon brass">
            <Icon name="plus" size={19} />
          </span>
          <span className="grow">Log an activity</span>
          <Icon name="chevron" size={17} />
        </Link>
      </div>

      <SectionTitle>Account</SectionTitle>
      <div className="menu">
        <div className="menu-row static">
          <span className="menu-icon">
            <Icon name="phone" size={19} />
          </span>
          <span className="grow">Phone</span>
          <span className="muted small">{profile?.phone ?? 'Not set'}</span>
        </div>
        <button className="menu-row" onClick={() => setSheet(true)}>
          <span className="menu-icon">
            <Icon name="lock" size={19} />
          </span>
          <span className="grow">Change password</span>
          <Icon name="chevron" size={17} />
        </button>
        <button className="menu-row danger" onClick={() => signOut()}>
          <span className="menu-icon">
            <Icon name="logout" size={19} />
          </span>
          <span className="grow">Log out</span>
        </button>
      </div>
      <div className="profile-credit">
        <FelesCredit tone="light" />
      </div>
      <div className="tiny muted" style={{ textAlign: 'center', margin: '18px 0 6px' }}>
        {isNative
          ? 'Your session is kept in the app’s private storage on this phone.'
          : 'Running in a browser - the session is kept in this browser only.'}
      </div>

      {sheet && (
        <ChangePasswordSheet
          onClose={() => setSheet(false)}
          onDone={(message) => {
            toast(message);
            setSheet(false);
          }}
        />
      )}
    </Screen>
  );
}

function WeekChart({ stats }: { stats: FieldStats }) {
  const peak = Math.max(1, ...stats.days.map((day) => day.completed));
  return (
    <div className="week-chart">
      <div className="week-chart-head">
        <div>
          <div className="week-chart-figure">{stats.completed_7d}</div>
          <div className="week-chart-caption">done this week</div>
        </div>
        {stats.on_time_rate != null && (
          <div className="week-chart-badge">
            <Icon name="clock" size={13} /> {Math.round(stats.on_time_rate * 100)}% on time
          </div>
        )}
      </div>
      <div className="week-bars">
        {stats.days.map((day) => {
          const date = dayjs(day.date);
          const today = date.isSame(dayjs(), 'day');
          return (
            <div key={day.date} className={`week-col${today ? ' today' : ''}`}>
              <div className="week-col-value">{day.completed || ''}</div>
              <div className="week-col-bar">
                <span
                  style={{
                    height: `${Math.max(day.completed ? 8 : 3, (day.completed / peak) * 100)}%`,
                  }}
                />
              </div>
              <div className="week-col-day">{today ? 'Today' : date.format('ddd')}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Kpi({
  icon,
  value,
  label,
  tone,
}: {
  icon: IconName;
  value: number | string;
  label: string;
  tone: string;
}) {
  return (
    <div className="kpi">
      <span className={`kpi-icon tone-${tone}`}>
        <Icon name={icon} size={16} />
      </span>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
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
        <button className="btn ghost" onClick={onClose}>
          Cancel
        </button>
        <button
          className="btn primary"
          onClick={submit}
          disabled={change.isPending || !current || next.length < 6}
        >
          {change.isPending ? 'Saving…' : 'Update'}
        </button>
      </div>
    </Sheet>
  );
}
