import { useMemo } from 'react';

import { useUpcoming } from '@/api/hooks';
import { ActivityCard } from '@/components/ActivityCard';
import { Banner, Empty, Screen, Skeletons } from '@/components/Shell';
import { dayLabel, dayjs } from '@/lib/format';

export function UpcomingPage() {
  const { data, isLoading, isError, error } = useUpcoming();

  const days = useMemo(() => {
    const buckets = new Map<string, typeof data>();
    (data ?? []).forEach((activity) => {
      const key = dayjs(activity.scheduled_at).format('YYYY-MM-DD');
      buckets.set(key, [...(buckets.get(key) ?? []), activity]);
    });
    return Array.from(buckets.entries());
  }, [data]);

  return (
    <Screen title="Upcoming" subtitle="Work the office has already scheduled for you">
      {isError && (
        <Banner kind="error">{(error as Error)?.message ?? 'Could not load your schedule.'}</Banner>
      )}
      {isLoading && <Skeletons count={2} />}

      {days.map(([day, items]) => (
        <div key={day}>
          <div className="section-title">{dayLabel(day)}</div>
          {(items ?? []).map((activity) => (
            <ActivityCard key={activity.id} activity={activity} />
          ))}
        </div>
      ))}

      {!isLoading && !days.length && (
        <Empty icon="🗓" title="Nothing scheduled yet" hint="Check back after the office plans your week." />
      )}
    </Screen>
  );
}
