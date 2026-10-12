/** One activity: what to do, where to go, and how to report it. */

import { useState } from 'react';
import { useParams } from 'react-router-dom';

import { ApiError, api } from '@/api/client';
import { useActivity, useRefreshAll, useStartActivity } from '@/api/hooks';
import type { ActivityOutcome, ActivityType, FieldActivity } from '@/api/types';
import { StatusPill } from '@/components/ActivityCard';
import { Icon, TypeIcon } from '@/components/Icon';
import { Avatar, Banner, Empty, Screen, Sheet, Spinner } from '@/components/Shell';
import { dateTime, dayLabel, dayjs, humanize, time } from '@/lib/format';
import { currentPosition, openExternal } from '@/lib/native';
import * as outbox from '@/lib/offline';
import { toast } from '@/lib/toast';

const OUTCOMES: { code: ActivityOutcome; label: string; tone: string }[] = [
  { code: 'COMPLETED', label: 'Done as planned', tone: 'teal' },
  { code: 'CUSTOMER_INTERESTED', label: 'Interested', tone: 'teal' },
  { code: 'FOLLOW_UP_REQUIRED', label: 'Needs follow-up', tone: 'amber' },
  { code: 'CUSTOMER_NOT_INTERESTED', label: 'Not interested', tone: 'rust' },
  { code: 'NO_RESPONSE', label: 'No response', tone: 'slate' },
  { code: 'RESCHEDULED', label: 'Rescheduled', tone: 'slate' },
  { code: 'OTHER', label: 'Other', tone: 'slate' },
];

/** Must match SALESPERSON_FOLLOWUP_TYPES on the backend. */
const FOLLOW_UP_TYPES: ActivityType[] = ['CALL', 'WHATSAPP', 'SMS', 'VISIT'];

function pickerValue(date: dayjs.Dayjs): string {
  return date.format('YYYY-MM-DDTHH:mm');
}

export function ActivityDetailPage() {
  const { activityId } = useParams();
  const id = Number(activityId);
  const { data: activity, isLoading, isError, error } = useActivity(id);
  const refresh = useRefreshAll();
  const start = useStartActivity();
  const [sheet, setSheet] = useState<'complete' | 'follow-up' | null>(null);
  const [pinning, setPinning] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);

  const pinHere = async () => {
    setPinning(true);
    setPinError(null);
    try {
      const position = await currentPosition();
      await api.post(`/salesperson/activities/${id}/location-fix`, {
        latitude: position.latitude.toFixed(6),
        longitude: position.longitude.toFixed(6),
      });
      refresh();
      toast('Saved this spot for the office.');
    } catch (error) {
      setPinError(
        error instanceof ApiError
          ? error.message
          : error instanceof Error
          ? error.message
          : 'Could not save this location.',
      );
    } finally {
      setPinning(false);
    }
  };

  if (isLoading) {
    return (
      <Screen title="Activity" back withNav={false}>
        <Spinner />
      </Screen>
    );
  }

  if (isError || !activity) {
    return (
      <Screen title="Activity" back withNav={false}>
        <Banner kind="error">
          {(error as ApiError)?.message ?? 'This activity is not available.'}
        </Banner>
        <Empty icon="lock" title="Not found" hint="It may have been reassigned by the office." />
      </Screen>
    );
  }

  const open = activity.status === 'SCHEDULED' || activity.status === 'IN_PROGRESS';
  const phone = activity.customer.phone;
  const digits = phone?.replace(/[^0-9]/g, '') ?? '';
  const done = (message: string) => {
    toast(message, message.startsWith('Saved on this phone') ? 'warn' : 'ok');
    refresh();
    setSheet(null);
  };

  return (
    <Screen
      eyebrow={
        <>
          {humanize(activity.activity_type)}
          {activity.self_logged
            ? ' · self-logged'
            : activity.parent_activity_id
            ? ' · follow-up'
            : ''}
        </>
      }
      title={activity.customer.name}
      subtitle={
        activity.scheduled_at
          ? `${dayLabel(activity.scheduled_at)} · ${time(activity.scheduled_at)}`
          : undefined
      }
      back
      withNav={false}
      hero={
        <div className="contact-actions">
          {phone && (
            <a className="contact-action" href={`tel:${phone}`}>
              <span>
                <Icon name="phone" size={20} />
              </span>
              Call
            </a>
          )}
          {phone && (
            <button
              className="contact-action"
              onClick={() => openExternal(`https://wa.me/${digits}`)}
            >
              <span>
                <Icon name="chat" size={20} />
              </span>
              WhatsApp
            </button>
          )}
          {phone && (
            <a className="contact-action" href={`sms:${phone}`}>
              <span>
                <Icon name="sms" size={20} />
              </span>
              SMS
            </a>
          )}
          {activity.location && (
            <button
              className="contact-action brass"
              onClick={() => openExternal(activity.location!.maps_url)}
            >
              <span>
                <Icon name="navigate" size={20} />
              </span>
              Directions
            </button>
          )}
        </div>
      }
      footer={
        open ? (
          <div className="btn-row">
            {activity.status === 'SCHEDULED' && (
              <button
                className="btn ghost"
                onClick={() => start.mutate(activity.id)}
                disabled={start.isPending}
              >
                <Icon name="play" size={16} /> Start
              </button>
            )}
            <button className="btn primary" onClick={() => setSheet('complete')}>
              <Icon name="check" size={18} stroke={2.4} /> Complete
            </button>
          </div>
        ) : undefined
      }
    >
      <div className="detail-card">
        <div className="detail-head">
          <TypeIcon type={activity.activity_type} size={46} />
          <div className="grow">
            <div className="detail-kicker">{humanize(activity.activity_type)}</div>
            <div className="detail-when">{dateTime(activity.scheduled_at)}</div>
          </div>
          <StatusPill activity={activity} />
        </div>
        <Progress activity={activity} />
        {(activity.customer.contact_person || phone) && (
          <div className="detail-person">
            <Avatar name={activity.customer.contact_person || activity.customer.name} size={36} />
            <div className="grow">
              <div className="strong small">
                {activity.customer.contact_person ?? activity.customer.name}
              </div>
              {phone && <div className="tiny muted mono">{phone}</div>}
            </div>
          </div>
        )}
      </div>

      {activity.purpose && (
        <div className="brief">
          <div className="brief-label">
            <Icon name="note" size={14} />
            {activity.self_logged ? 'Your plan' : 'Brief from the office'}
          </div>
          <div className="brief-text">{activity.purpose}</div>
        </div>
      )}

      {activity.location && (
        <div className="where-card">
          <div className="where-map" aria-hidden>
            <svg viewBox="0 0 320 110" preserveAspectRatio="xMidYMid slice">
              <path d="M0 78 C 60 60, 110 96, 170 70 S 280 40, 320 58" className="road major" />
              <path d="M40 0 L 90 110" className="road" />
              <path d="M210 0 C 200 40, 240 70, 230 110" className="road" />
              <path d="M0 30 C 80 36, 160 18, 320 26" className="road" />
            </svg>
            <span className="where-pin">
              <Icon name="pin" size={22} stroke={2} />
            </span>
          </div>
          <div className="where-body">
            <div className="strong">
              {activity.location.label ?? activity.location.city ?? 'Location'}
            </div>
            {activity.location.formatted !== activity.location.label && (
              <div className="small muted">{activity.location.formatted}</div>
            )}
            <div className="btn-row tight" style={{ marginTop: 12 }}>
              <button
                className="btn small brass"
                onClick={() => openExternal(activity.location!.maps_url)}
              >
                <Icon name="navigate" size={15} /> Navigate
              </button>
              <button className="btn small ghost" onClick={pinHere} disabled={pinning}>
                <Icon name="crosshair" size={15} />
                {pinning ? 'Locating…' : "I'm here"}
              </button>
            </div>
            {pinError && (
              <div className="tiny" style={{ color: 'var(--rust)', marginTop: 8 }}>
                {pinError}
              </div>
            )}
            <div className="tiny muted" style={{ marginTop: 8 }}>
              “I'm here” saves this spot so the office can fix an address they only had as text.
            </div>
          </div>
        </div>
      )}

      {activity.status === 'COMPLETED' && (
        <div className="report">
          <div className="brief-label">
            <Icon name="check" size={14} stroke={2.4} /> Your report
          </div>
          <div className="brief-text">{activity.completion_note}</div>
          <div className="tiny muted" style={{ marginTop: 8 }}>
            Reported {dateTime(activity.completed_at)}
          </div>
          <button
            className="btn ghost small"
            style={{ marginTop: 12 }}
            onClick={() => setSheet('follow-up')}
          >
            <Icon name="calendar" size={15} /> Schedule a follow-up
          </button>
        </div>
      )}

      {sheet === 'complete' && (
        <CompleteSheet activity={activity} onClose={() => setSheet(null)} onDone={done} />
      )}
      {sheet === 'follow-up' && (
        <FollowUpSheet activity={activity} onClose={() => setSheet(null)} onDone={done} />
      )}
    </Screen>
  );
}

function Progress({ activity }: { activity: FieldActivity }) {
  const steps = [
    { label: 'Planned', at: activity.scheduled_at, on: true },
    {
      label: 'Started',
      at: activity.started_at,
      on: Boolean(activity.started_at) || activity.status === 'COMPLETED',
    },
    {
      label: activity.status === 'CANCELLED' ? 'Cancelled' : 'Reported',
      at: activity.completed_at,
      on: activity.status === 'COMPLETED' || activity.status === 'CANCELLED',
    },
  ];
  return (
    <div className="progress">
      {steps.map((step, index) => (
        <div key={step.label} className={`progress-step${step.on ? ' on' : ''}`}>
          <span className="progress-dot" />
          {index < steps.length - 1 && <span className="progress-line" />}
          <div className="progress-label">{step.label}</div>
          <div className="progress-at">{step.at && step.on ? time(step.at) : '—'}</div>
        </div>
      ))}
    </div>
  );
}

function CompleteSheet({
  activity,
  onClose,
  onDone,
}: {
  activity: FieldActivity;
  onClose: () => void;
  onDone: (message: string) => void;
}) {
  const [outcome, setOutcome] = useState<ActivityOutcome>('COMPLETED');
  const [note, setNote] = useState('');
  const [withFollowUp, setWithFollowUp] = useState(false);
  const [followUpType, setFollowUpType] = useState<ActivityType>('CALL');
  const [followUpAt, setFollowUpAt] = useState(
    pickerValue(dayjs().add(3, 'day').hour(11).minute(0)),
  );
  const [followUpNote, setFollowUpNote] = useState('');
  const [busy, setBusy] = useState(false);

  const pick = (code: ActivityOutcome) => {
    setOutcome(code);
    if (code === 'FOLLOW_UP_REQUIRED') setWithFollowUp(true);
  };

  const submit = async () => {
    if (busy || !note.trim()) return;
    setBusy(true);
    // Persist locally first: a report must survive a dead network.
    outbox.enqueue({
      token: outbox.newToken(),
      activityId: activity.id,
      outcome_code: outcome,
      completion_note: note.trim(),
      completed_at: new Date().toISOString(),
      followUp: withFollowUp
        ? {
            activity_type: followUpType,
            scheduled_at: dayjs(followUpAt).toISOString(),
            note: followUpNote.trim() || null,
          }
        : null,
    });
    const synced = await outbox.flush();
    setBusy(false);
    onDone(
      synced > 0
        ? 'Report sent to the office.'
        : 'Saved on this phone. It will sync when you have signal.',
    );
  };

  return (
    <Sheet title="Report back" subtitle={activity.customer.name} onClose={onClose}>
      <div className="field">
        <span>How did it go</span>
        <div className="outcome-grid">
          {OUTCOMES.map((item) => (
            <button
              key={item.code}
              type="button"
              className={`outcome tone-${item.tone}${outcome === item.code ? ' on' : ''}`}
              onClick={() => pick(item.code)}
            >
              <span className="outcome-dot" />
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <label className="field">
        <span>What happened?</span>
        <textarea
          value={note}
          onChange={(event) => setNote(event.currentTarget.value)}
          placeholder="Customer wants a quotation for 30 MT."
        />
      </label>

      <div className={`toggle-card${withFollowUp ? ' on' : ''}`}>
        <button
          type="button"
          className="toggle-row"
          onClick={() => setWithFollowUp((value) => !value)}
        >
          <span className="grow strong">Schedule a follow-up for me</span>
          <span className={`switch${withFollowUp ? ' on' : ''}`} />
        </button>
        {withFollowUp && (
          <div style={{ marginTop: 12 }}>
            <div className="chip-group">
              {FOLLOW_UP_TYPES.map((value) => (
                <button
                  key={value}
                  type="button"
                  className={`chip${followUpType === value ? ' selected' : ''}`}
                  onClick={() => setFollowUpType(value)}
                >
                  {humanize(value)}
                </button>
              ))}
            </div>
            <input
              type="datetime-local"
              style={{ marginTop: 10 }}
              value={followUpAt}
              min={pickerValue(dayjs())}
              onChange={(event) => setFollowUpAt(event.currentTarget.value)}
            />
            <textarea
              style={{ minHeight: 64, marginTop: 10 }}
              value={followUpNote}
              onChange={(event) => setFollowUpNote(event.currentTarget.value)}
              placeholder="Note for the follow-up (optional)"
            />
          </div>
        )}
      </div>

      <div className="btn-row" style={{ marginTop: 16 }}>
        <button className="btn ghost" onClick={onClose} disabled={busy}>
          Cancel
        </button>
        <button className="btn primary" onClick={submit} disabled={busy || !note.trim()}>
          {busy ? 'Saving…' : 'Send report'}
        </button>
      </div>
    </Sheet>
  );
}

function FollowUpSheet({
  activity,
  onClose,
  onDone,
}: {
  activity: FieldActivity;
  onClose: () => void;
  onDone: (message: string) => void;
}) {
  const [type, setType] = useState<ActivityType>('CALL');
  const [when, setWhen] = useState(pickerValue(dayjs().add(3, 'day').hour(11).minute(0)));
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/salesperson/activities/${activity.id}/follow-up`, {
        activity_type: type,
        scheduled_at: dayjs(when).toISOString(),
        note: note.trim() || null,
      });
      onDone('Follow-up scheduled.');
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.offline
            ? 'You are offline. Try again once you have signal.'
            : err.message
          : 'Could not schedule the follow-up.',
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet
      title="Schedule follow-up"
      subtitle={`Stays with ${activity.customer.name} and with you`}
      onClose={onClose}
    >
      {error && <Banner kind="error">{error}</Banner>}
      <label className="field">
        <span>Type</span>
        <div className="chip-group">
          {FOLLOW_UP_TYPES.map((value) => (
            <button
              key={value}
              type="button"
              className={`chip${type === value ? ' selected' : ''}`}
              onClick={() => setType(value)}
            >
              {humanize(value)}
            </button>
          ))}
        </div>
      </label>
      <label className="field">
        <span>When</span>
        <input
          type="datetime-local"
          value={when}
          min={pickerValue(dayjs())}
          onChange={(event) => setWhen(event.currentTarget.value)}
        />
      </label>
      <label className="field">
        <span>Note (optional)</span>
        <textarea
          style={{ minHeight: 80 }}
          value={note}
          onChange={(event) => setNote(event.currentTarget.value)}
        />
      </label>
      <div className="btn-row">
        <button className="btn ghost" onClick={onClose} disabled={busy}>
          Cancel
        </button>
        <button className="btn primary" onClick={submit} disabled={busy}>
          {busy ? 'Scheduling…' : 'Schedule'}
        </button>
      </div>
    </Sheet>
  );
}
