import { useNavigate } from 'react-router-dom';

import type { FieldActivity } from '@/api/types';
import { dayLabel, humanize, isPast, time } from '@/lib/format';
import { openExternal } from '@/lib/native';
import { Icon, TypeIcon } from './Icon';

export function StatusPill({
  activity,
  pendingSync = false,
}: {
  activity: FieldActivity;
  pendingSync?: boolean;
}) {
  if (pendingSync) return <span className="pill amber">Waiting to sync</span>;
  if (activity.status === 'COMPLETED') {
    return (
      <span className="pill teal">
        <Icon name="check" size={12} stroke={2.6} />
        {humanize(activity.outcome_code ?? 'COMPLETED')}
      </span>
    );
  }
  if (activity.status === 'CANCELLED') return <span className="pill slate">Cancelled</span>;
  if (activity.status === 'IN_PROGRESS')
    return <span className="pill amber live">In progress</span>;
  if (isPast(activity.scheduled_at)) return <span className="pill rust">Overdue</span>;
  return <span className="pill slate">Scheduled</span>;
}

/** Strip the trailing state / pincode noise: "Plot 12, GIDC, Rajkot" reads better. */
export function shortPlace(activity: FieldActivity): string | null {
  const location = activity.location;
  if (!location) return null;
  return location.label || location.formatted;
}

export function ActivityCard({
  activity,
  showDay = false,
  showTime = true,
  pendingSync = false,
}: {
  activity: FieldActivity;
  showDay?: boolean;
  showTime?: boolean;
  pendingSync?: boolean;
}) {
  const navigate = useNavigate();
  const open = () => navigate(`/activity/${activity.id}`);
  const place = shortPlace(activity);
  const phone = activity.customer.phone;
  const live = activity.status === 'SCHEDULED' || activity.status === 'IN_PROGRESS';

  return (
    <div
      className={`act-card${activity.status === 'COMPLETED' ? ' done' : ''}`}
      role="link"
      tabIndex={0}
      onClick={open}
      onKeyDown={(event) => event.key === 'Enter' && open()}
    >
      <TypeIcon type={activity.activity_type} size={42} />
      <div className="grow act-body">
        <div className="act-top">
          <span className="act-type">{humanize(activity.activity_type)}</span>
          {showTime && activity.scheduled_at && (
            <span className="act-when">
              {showDay ? `${dayLabel(activity.scheduled_at)} · ` : ''}
              {time(activity.scheduled_at)}
            </span>
          )}
          {activity.self_logged && <span className="tag brass">Self-logged</span>}
        </div>
        <div className="act-name">{activity.customer.name}</div>
        {place && (
          <div className="act-meta">
            <Icon name="pin" size={13} />
            <span className="ellipsis">{place}</span>
          </div>
        )}
        {!place && activity.customer.contact_person && (
          <div className="act-meta">
            <Icon name="user" size={13} />
            <span className="ellipsis">{activity.customer.contact_person}</span>
          </div>
        )}
        {(activity.subject || activity.purpose) && activity.status !== 'COMPLETED' && (
          <div className="act-brief">{activity.subject || activity.purpose}</div>
        )}
        {activity.status === 'COMPLETED' && activity.completion_note && (
          <div className="act-brief">{activity.completion_note}</div>
        )}
        <div className="act-foot">
          <StatusPill activity={activity} pendingSync={pendingSync} />
        </div>
      </div>
      {live && (
        <div className="act-actions" onClick={(event) => event.stopPropagation()}>
          {activity.location && (
            <button
              className="round-btn brass"
              aria-label="Navigate"
              onClick={() => openExternal(activity.location!.maps_url)}
            >
              <Icon name="navigate" size={17} />
            </button>
          )}
          {phone && (
            <a className="round-btn" aria-label="Call" href={`tel:${phone}`}>
              <Icon name="phone" size={17} />
            </a>
          )}
        </div>
      )}
      {!live && <Icon name="chevron" size={18} className="act-chevron" />}
    </div>
  );
}
