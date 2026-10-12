import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useDashboard } from '@/api/hooks';
import type { ActivityType, FieldActivity } from '@/api/types';
import { ActivityCard, shortPlace } from '@/components/ActivityCard';
import { Icon, TypeIcon } from '@/components/Icon';
import { Banner, Empty, Screen, SectionTitle, Skeletons } from '@/components/Shell';
import { useAuth } from '@/lib/auth';
import { countdown, dayjs, humanize, partOfDay, time } from '@/lib/format';
import { openExternal } from '@/lib/native';
import * as outbox from '@/lib/offline';

const ORDER = ['Morning', 'Afternoon', 'Evening'] as const;

function salutation(): string {
  const hour = dayjs().hour();
  return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
}

export function ProgressRing({
  done,
  total,
  size = 92,
}: {
  done: number;
  total: number;
  size?: number;
}) {
  const stroke = 7;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const share = total ? Math.min(done / total, 1) : 0;
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          className="ring-track"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          className="ring-value"
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - share)}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="ring-label">
        <div className="ring-figure">
          {done}
          <span>/{total}</span>
        </div>
        <div className="ring-caption">done</div>
      </div>
    </div>
  );
}

const QUICK: { type: ActivityType; label: string }[] = [
  { type: 'CALL', label: 'Call' },
  { type: 'VISIT', label: 'Visit' },
  { type: 'WHATSAPP', label: 'WhatsApp' },
];

export function TodayPage() {
  const { profile } = useAuth();
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch, isFetching } = useDashboard();
  const [queued, setQueued] = useState(outbox.pending());

  useEffect(() => outbox.subscribe(setQueued), []);

  const counts = data?.counts;
  const queuedIds = new Set(
    queued.flatMap((item) => (outbox.isLog(item) ? [] : [item.activityId])),
  );
  const queuedLogs = queued.filter(outbox.isLog);
  const next = data?.next_activity ?? null;
  const firstName = (profile?.name ?? 'there').split(' ')[0];

  const groups = ORDER.map((part) => ({
    part,
    items: (data?.today ?? []).filter((item) => partOfDay(item.scheduled_at) === part),
  })).filter((group) => group.items.length > 0);

  return (
    <Screen
      eyebrow={dayjs().format('dddd, D MMMM')}
      title={
        <>
          {salutation()}, <em>{firstName}</em>
        </>
      }
      action={
        <button
          className={`icon-btn${isFetching ? ' spinning' : ''}`}
          onClick={() => refetch()}
          aria-label="Refresh"
        >
          <Icon name="refresh" size={19} />
        </button>
      }
      hero={
        <div className="today-hero">
          <ProgressRing done={counts?.today_completed ?? 0} total={counts?.today_total ?? 0} />
          <div className="hero-stats">
            <HeroStat value={counts?.today_pending} label="To do" />
            <HeroStat value={counts?.today_visits} label="Visits" />
            <HeroStat value={counts?.overdue} label="Overdue" alert={Boolean(counts?.overdue)} />
            <HeroStat value={counts?.upcoming} label="Ahead" />
          </div>
        </div>
      }
    >
      {next && <NextUp activity={next} pendingSync={queuedIds.has(next.id)} />}

      <div className="quick-log">
        <div className="quick-log-text">
          <div className="strong">Out on your own?</div>
          <div className="tiny muted">Log a cold call or visit in seconds.</div>
        </div>
        <div className="quick-log-actions">
          {QUICK.map((item) => (
            <button
              key={item.type}
              className="quick-chip"
              onClick={() => navigate(`/log?type=${item.type}`)}
            >
              <TypeIcon type={item.type} size={30} />
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      </div>

      {queued.length > 0 && (
        <Banner kind="warn">
          <strong>
            {queued.length} report{queued.length > 1 ? 's' : ''} saved on this phone.
          </strong>{' '}
          They sync by themselves when you have signal.
          {queuedLogs.length > 0 && (
            <div className="tiny" style={{ marginTop: 4 }}>
              {queuedLogs.map((item) => item.label).join(' · ')}
            </div>
          )}
        </Banner>
      )}
      {isError && (
        <Banner kind="error">
          {(error as Error)?.message ?? 'Could not load your activities.'}
        </Banner>
      )}

      {isLoading && <Skeletons />}

      {data?.overdue.length ? (
        <>
          <SectionTitle aside={<span className="pill rust">{data.overdue.length}</span>}>
            Missed, still open
          </SectionTitle>
          <div className="timeline">
            {data.overdue.map((activity: FieldActivity) => (
              <TimelineItem
                key={activity.id}
                activity={activity}
                showDay
                pendingSync={queuedIds.has(activity.id)}
              />
            ))}
          </div>
        </>
      ) : null}

      {groups.map((group) => (
        <div key={group.part}>
          <SectionTitle aside={`${group.items.length}`}>{group.part}</SectionTitle>
          <div className="timeline">
            {group.items.map((activity) => (
              <TimelineItem
                key={activity.id}
                activity={activity}
                pendingSync={queuedIds.has(activity.id)}
              />
            ))}
          </div>
        </div>
      ))}

      {!isLoading && !groups.length && !data?.overdue.length && (
        <Empty
          icon="today"
          title="A clear day"
          hint="Nothing is scheduled. New work from the office lands here - or log your own."
        >
          <Link to="/log" className="btn ghost small" style={{ marginTop: 14 }}>
            <Icon name="plus" size={16} /> Log an activity
          </Link>
        </Empty>
      )}
    </Screen>
  );
}

function HeroStat({ value, label, alert }: { value?: number; label: string; alert?: boolean }) {
  return (
    <div className={`hero-stat${alert ? ' alert' : ''}`}>
      <div className="hero-stat-value">{value ?? '–'}</div>
      <div className="hero-stat-label">{label}</div>
    </div>
  );
}

export function TimelineItem({
  activity,
  showDay = false,
  pendingSync = false,
}: {
  activity: FieldActivity;
  showDay?: boolean;
  pendingSync?: boolean;
}) {
  const [clock, meridiem] = time(activity.scheduled_at).split(' ');
  const state =
    activity.status === 'COMPLETED' || pendingSync
      ? 'done'
      : activity.status === 'SCHEDULED' && dayjs(activity.scheduled_at).isBefore(dayjs())
      ? 'late'
      : activity.status === 'IN_PROGRESS'
      ? 'live'
      : '';
  return (
    <div className={`tl-item ${state}`}>
      <div className="tl-time">
        <div className="tl-clock">{clock}</div>
        <div className="tl-meridiem">
          {showDay ? dayjs(activity.scheduled_at).format('DD MMM') : meridiem}
        </div>
      </div>
      <div className="tl-rail">
        <span className="tl-dot">
          {state === 'done' && <Icon name="check" size={9} stroke={3.4} />}
        </span>
      </div>
      <ActivityCard activity={activity} showTime={false} pendingSync={pendingSync} />
    </div>
  );
}

function NextUp({ activity, pendingSync }: { activity: FieldActivity; pendingSync: boolean }) {
  const navigate = useNavigate();
  const place = shortPlace(activity);
  const late = dayjs(activity.scheduled_at).isBefore(dayjs());
  return (
    <div className="next-up" onClick={() => navigate(`/activity/${activity.id}`)} role="link">
      <div className="next-up-head">
        <span className="eyebrow">Next up</span>
        <span className={`next-up-count${late ? ' late' : ''}`}>
          <Icon name="clock" size={13} />
          {pendingSync ? 'Syncing' : countdown(activity.scheduled_at)}
        </span>
      </div>
      <div className="next-up-body">
        <TypeIcon type={activity.activity_type} size={48} />
        <div className="grow" style={{ minWidth: 0 }}>
          <div className="next-up-name">{activity.customer.name}</div>
          <div className="next-up-meta">
            {humanize(activity.activity_type)} · {time(activity.scheduled_at)}
            {activity.customer.contact_person ? ` · ${activity.customer.contact_person}` : ''}
          </div>
          {place && (
            <div className="next-up-place">
              <Icon name="pin" size={13} />
              <span className="ellipsis">{place}</span>
            </div>
          )}
        </div>
      </div>
      <div className="next-up-actions" onClick={(event) => event.stopPropagation()}>
        {activity.location ? (
          <button className="btn brass" onClick={() => openExternal(activity.location!.maps_url)}>
            <Icon name="navigate" size={17} /> Navigate
          </button>
        ) : activity.customer.phone ? (
          <a className="btn brass" href={`tel:${activity.customer.phone}`}>
            <Icon name="phone" size={17} /> Call now
          </a>
        ) : null}
        <button className="btn glass" onClick={() => navigate(`/activity/${activity.id}`)}>
          Open <Icon name="arrow" size={16} />
        </button>
      </div>
    </div>
  );
}
