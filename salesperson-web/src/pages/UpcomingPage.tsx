import { useMemo } from 'react';

import { useUpcoming } from '@/api/hooks';
import type { FieldActivity } from '@/api/types';
import { ActivityCard } from '@/components/ActivityCard';
import { Banner, Empty, Screen, Skeletons } from '@/components/Shell';
import { dayLabel, dayjs } from '@/lib/format';

export function UpcomingPage() {
  const { data, isLoading, isError, error } = useUpcoming();

  const days = useMemo(() => {
    const buckets = new Map<string, FieldActivity[]>();
    (data ?? []).forEach((activity) => {
      const key = dayjs(activity.scheduled_at).format('YYYY-MM-DD');
      buckets.set(key, [...(buckets.get(key) ?? []), activity]);
    });
    return Array.from(buckets.entries());
  }, [data]);

  // A two-week strip: how loaded each coming day is.
  const strip = useMemo(() => {
    const counts = new Map(days.map(([day, items]) => [day, items.length]));
    return Array.from({ length: 14 }, (_, offset) => {
      const date = dayjs().add(offset + 1, 'day');
      return { date, count: counts.get(date.format('YYYY-MM-DD')) ?? 0 };
    });
  }, [days]);
  const peak = Math.max(1, ...strip.map((day) => day.count));
  const total = data?.length ?? 0;

  return (
    <Screen
      eyebrow="The plan"
      title={
        total ? (
          <>
            {total} ahead <em>this fortnight</em>
          </>
        ) : (
          'Nothing planned yet'
        )
      }
      subtitle="Scheduled by the office, or by you"
      hero={
        <div className="week-strip">
          {strip.map(({ date, count }) => (
            <a
              key={date.valueOf()}
              className={`week-day${count ? ' busy' : ''}${date.day() === 0 ? ' sunday' : ''}`}
              href={count ? `#day-${date.format('YYYY-MM-DD')}` : undefined}
              onClick={(event) => {
                event.preventDefault();
                document
                  .getElementById(`day-${date.format('YYYY-MM-DD')}`)
                  ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }}
            >
              <span className="week-dow">{date.format('dd').charAt(0)}</span>
              <span className="week-bar">
                <span style={{ height: `${(count / peak) * 100}%` }} />
              </span>
              <span className="week-num">{date.format('D')}</span>
            </a>
          ))}
        </div>
      }
    >
      {isError && (
        <Banner kind="error">{(error as Error)?.message ?? 'Could not load your schedule.'}</Banner>
      )}
      {isLoading && <Skeletons count={2} />}

      {days.map(([day, items]) => (
        <section key={day} id={`day-${day}`} className="day-block">
          <div className="day-head">
            <div className="day-date">{dayjs(day).format('D')}</div>
            <div className="grow">
              <div className="day-name">{dayLabel(day)}</div>
              <div className="tiny muted">
                {dayjs(day).format('MMMM')} · {items.length} thing{items.length > 1 ? 's' : ''}
              </div>
            </div>
          </div>
          <div className="stack">
            {items.map((activity) => (
              <ActivityCard key={activity.id} activity={activity} />
            ))}
          </div>
        </section>
      ))}

      {!isLoading && !days.length && (
        <Empty
          icon="calendar"
          title="Your calendar is open"
          hint="Plan a call or visit from the + button, or wait for the office's schedule."
        />
      )}
    </Screen>
  );
}
