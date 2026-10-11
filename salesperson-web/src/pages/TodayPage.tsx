import { useEffect, useState } from 'react';

import { useDashboard } from '@/api/hooks';
import type { FieldActivity } from '@/api/types';
import { ActivityCard } from '@/components/ActivityCard';
import { Banner, Empty, Screen, Skeletons } from '@/components/Shell';
import { greeting, partOfDay } from '@/lib/format';
import * as outbox from '@/lib/offline';
import { useAuth } from '@/lib/auth';

const ORDER = ['Morning', 'Afternoon', 'Evening'] as const;

export function TodayPage() {
  const { profile } = useAuth();
  const { data, isLoading, isError, error, refetch, isFetching } = useDashboard();
  const [queued, setQueued] = useState(outbox.pending());

  useEffect(() => outbox.subscribe(setQueued), []);

  const counts = data?.counts;
  const queuedIds = new Set(queued.map((item) => item.activityId));

  const groups = ORDER.map((part) => ({
    part,
    items: (data?.today ?? []).filter((item) => partOfDay(item.scheduled_at) === part),
  })).filter((group) => group.items.length > 0);

  return (
    <Screen
      title={greeting(profile?.name ?? 'there')}
      subtitle={
        counts
          ? `${counts.today_pending} to do · ${counts.today_completed} done today`
          : 'Loading your day…'
      }
      action={
        <button
          className="back-btn"
          onClick={() => refetch()}
          aria-label="Refresh"
          disabled={isFetching}
        >
          ↻
        </button>
      }
    >
      {queued.length > 0 && (
        <Banner kind="warn">
          {queued.length} report{queued.length > 1 ? 's' : ''} saved on this phone, waiting for
          network. They will sync automatically.
        </Banner>
      )}
      {isError && (
        <Banner kind="error">
          {(error as Error)?.message ?? 'Could not load your activities.'}
        </Banner>
      )}

      {counts && (
        <div className="stat-row">
          <div className="stat">
            <div className="value">{counts.today_total}</div>
            <div className="label">Today</div>
          </div>
          <div className="stat">
            <div className="value">{counts.today_visits}</div>
            <div className="label">Visits</div>
          </div>
          <div className="stat">
            <div className="value" style={{ color: counts.overdue ? 'var(--danger)' : undefined }}>
              {counts.overdue}
            </div>
            <div className="label">Overdue</div>
          </div>
        </div>
      )}

      {isLoading && <Skeletons />}

      {data?.overdue.length ? (
        <>
          <div className="section-title">Missed, still open</div>
          {data.overdue.map((activity: FieldActivity) => (
            <ActivityCard
              key={activity.id}
              activity={activity}
              showDay
              pendingSync={queuedIds.has(activity.id)}
            />
          ))}
        </>
      ) : null}

      {groups.map((group) => (
        <div key={group.part}>
          <div className="section-title">{group.part}</div>
          {group.items.map((activity) => (
            <ActivityCard
              key={activity.id}
              activity={activity}
              pendingSync={queuedIds.has(activity.id)}
            />
          ))}
        </div>
      ))}

      {!isLoading && !groups.length && !data?.overdue.length && (
        <Empty
          icon="☕"
          title="Nothing scheduled for today"
          hint="New work assigned by the office will show up here."
        />
      )}
    </Screen>
  );
}
