import { Link } from 'react-router-dom';

import type { FieldActivity } from '@/api/types';
import { openExternal } from '@/lib/native';
import { dayLabel, humanize, isPast, time } from '@/lib/format';

const TYPE_ICON: Record<string, string> = {
  VISIT: '📍',
  CALL: '📞',
  WHATSAPP: '💬',
  SMS: '✉️',
  EMAIL: '📧',
  MEETING: '🤝',
};

function statusBadge(activity: FieldActivity) {
  if (activity.status === 'COMPLETED') {
    return <span className="badge green">{humanize(activity.outcome_code ?? 'COMPLETED')}</span>;
  }
  if (activity.status === 'CANCELLED') {
    return <span className="badge grey">Cancelled</span>;
  }
  if (activity.status === 'IN_PROGRESS') {
    return <span className="badge amber">In progress</span>;
  }
  if (isPast(activity.scheduled_at)) {
    return <span className="badge red">Overdue</span>;
  }
  return <span className="badge">Scheduled</span>;
}

export function ActivityCard({
  activity,
  showDay = false,
  pendingSync = false,
}: {
  activity: FieldActivity;
  showDay?: boolean;
  pendingSync?: boolean;
}) {
  const late = activity.status === 'SCHEDULED' && isPast(activity.scheduled_at);
  return (
    <div className="card raised">
      <div className="row top">
        <div className={`time-chip${late ? ' late' : ''}`}>
          <div className="t">{time(activity.scheduled_at)}</div>
          {showDay && <div className="d">{dayLabel(activity.scheduled_at)}</div>}
        </div>
        <div className="grow">
          <div className="row between">
            <div className="tiny strong muted">
              {TYPE_ICON[activity.activity_type] ?? '•'} {humanize(activity.activity_type)}
            </div>
            {pendingSync ? (
              <span className="badge amber">Waiting to sync</span>
            ) : (
              statusBadge(activity)
            )}
          </div>
          <div className="strong" style={{ marginTop: 3, fontSize: 16 }}>
            {activity.customer.name}
          </div>
          {activity.location && (
            <div className="small muted ellipsis" style={{ marginTop: 1 }}>
              📍 {activity.location.formatted}
            </div>
          )}
          {(activity.subject || activity.purpose) && (
            <div className="small" style={{ marginTop: 6, color: 'var(--ink-soft)' }}>
              {activity.subject || activity.purpose}
            </div>
          )}
        </div>
      </div>

      <div className="btn-row" style={{ marginTop: 14 }}>
        <Link className="btn secondary" to={`/activity/${activity.id}`}>
          View
        </Link>
        {activity.location && (
          <button
            className="btn"
            onClick={() => openExternal(activity.location!.maps_url)}
          >
            Navigate
          </button>
        )}
        {!activity.location && activity.customer.phone && (
          <a className="btn" href={`tel:${activity.customer.phone}`}>
            Call
          </a>
        )}
      </div>
    </div>
  );
}
