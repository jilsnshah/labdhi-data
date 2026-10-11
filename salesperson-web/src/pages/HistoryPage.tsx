import { useHistory } from '@/api/hooks';
import { Banner, Empty, Screen, Skeletons } from '@/components/Shell';
import { dateTime, humanize } from '@/lib/format';
import { Link } from 'react-router-dom';

export function HistoryPage() {
  const { data, isLoading, isError, error } = useHistory();

  return (
    <Screen title="My history" subtitle="What you have finished" back withNav={false}>
      {isError && (
        <Banner kind="error">{(error as Error)?.message ?? 'Could not load your history.'}</Banner>
      )}
      {isLoading && <Skeletons count={3} />}

      {(data ?? []).map((activity) => (
        <Link
          key={activity.id}
          to={`/activity/${activity.id}`}
          className="card"
          style={{ display: 'block', color: 'inherit', textDecoration: 'none' }}
        >
          <div className="row between">
            <div className="small strong">
              {humanize(activity.activity_type)} · {activity.customer.name}
            </div>
            <span className={`badge ${activity.status === 'CANCELLED' ? 'grey' : 'green'}`}>
              {activity.status === 'CANCELLED'
                ? 'Cancelled'
                : humanize(activity.outcome_code ?? 'Completed')}
            </span>
          </div>
          <div className="tiny muted" style={{ marginTop: 2 }}>
            {dateTime(activity.completed_at ?? activity.scheduled_at)}
          </div>
          {activity.completion_note && (
            <div className="small" style={{ marginTop: 6 }}>
              {activity.completion_note}
            </div>
          )}
        </Link>
      ))}

      {!isLoading && !data?.length && (
        <Empty icon="📁" title="Nothing completed yet" hint="Finished work will be listed here." />
      )}
    </Screen>
  );
}
