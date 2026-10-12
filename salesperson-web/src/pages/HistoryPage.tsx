import { useMemo, useState } from 'react';

import { useHistory } from '@/api/hooks';
import type { FieldActivity } from '@/api/types';
import { ActivityCard } from '@/components/ActivityCard';
import { Banner, Empty, Screen, SectionTitle, Skeletons } from '@/components/Shell';
import { dayLabel, dayjs } from '@/lib/format';

type Filter = 'all' | 'mine' | 'assigned';

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'mine', label: 'Self-logged' },
  { key: 'assigned', label: 'From the office' },
];

export function HistoryPage() {
  const { data, isLoading, isError, error } = useHistory();
  const [filter, setFilter] = useState<Filter>('all');

  const rows = useMemo(
    () =>
      (data ?? []).filter((activity) =>
        filter === 'all' ? true : filter === 'mine' ? activity.self_logged : !activity.self_logged,
      ),
    [data, filter],
  );

  const days = useMemo(() => {
    const buckets = new Map<string, FieldActivity[]>();
    rows.forEach((activity) => {
      const key = dayjs(activity.completed_at ?? activity.scheduled_at).format('YYYY-MM-DD');
      buckets.set(key, [...(buckets.get(key) ?? []), activity]);
    });
    return Array.from(buckets.entries());
  }, [rows]);

  return (
    <Screen
      eyebrow="Track record"
      title="My history"
      subtitle={data ? `${data.length} finished` : undefined}
      back
      withNav={false}
    >
      <div className="segmented" role="tablist">
        {FILTERS.map((item) => (
          <button
            key={item.key}
            role="tab"
            aria-selected={filter === item.key}
            className={filter === item.key ? 'on' : undefined}
            onClick={() => setFilter(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {isError && (
        <Banner kind="error">{(error as Error)?.message ?? 'Could not load your history.'}</Banner>
      )}
      {isLoading && <Skeletons count={3} />}

      {days.map(([day, items]) => (
        <div key={day}>
          <SectionTitle aside={dayjs(day).format('DD MMM')}>
            {dayLabel(day) || 'Earlier'}
          </SectionTitle>
          <div className="stack">
            {items.map((activity) => (
              <ActivityCard key={activity.id} activity={activity} showTime={false} />
            ))}
          </div>
        </div>
      ))}

      {!isLoading && !rows.length && (
        <Empty icon="history" title="Nothing here yet" hint="Finished work will be listed here." />
      )}
    </Screen>
  );
}
