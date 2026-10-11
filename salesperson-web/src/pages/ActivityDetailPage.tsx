/** One activity: what to do, where to go, and how to report it. */

import { useState } from 'react';
import { useParams } from 'react-router-dom';

import { ApiError, api } from '@/api/client';
import { useActivity, useRefreshAll, useStartActivity } from '@/api/hooks';
import type { ActivityOutcome, ActivityType, FieldActivity } from '@/api/types';
import { Banner, Empty, Screen, Sheet, Spinner } from '@/components/Shell';
import { dateTime, dayjs, humanize, time } from '@/lib/format';
import { currentPosition, openExternal } from '@/lib/native';
import * as outbox from '@/lib/offline';

const OUTCOMES: ActivityOutcome[] = [
  'COMPLETED',
  'CUSTOMER_INTERESTED',
  'FOLLOW_UP_REQUIRED',
  'CUSTOMER_NOT_INTERESTED',
  'NO_RESPONSE',
  'RESCHEDULED',
  'OTHER',
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
  const [notice, setNotice] = useState<string | null>(null);
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
      setNotice('Saved this spot for the office.');
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
        <Empty icon="🔒" title="Not found" hint="It may have been reassigned by the office." />
      </Screen>
    );
  }

  const open = activity.status === 'SCHEDULED' || activity.status === 'IN_PROGRESS';

  return (
    <Screen
      title={humanize(activity.activity_type)}
      subtitle={`${activity.customer.name} · ${time(activity.scheduled_at)}`}
      back
      withNav={false}
    >
      {notice && <Banner kind="info">{notice}</Banner>}

      <div className="card raised">
        <div className="row between">
          <div className="strong" style={{ fontSize: 18 }}>
            {activity.customer.name}
          </div>
          <span className={`badge ${activity.status === 'COMPLETED' ? 'green' : ''}`}>
            {activity.status === 'COMPLETED'
              ? humanize(activity.outcome_code ?? 'Completed')
              : humanize(activity.status)}
          </span>
        </div>
        {activity.customer.contact_person && (
          <div className="small muted" style={{ marginTop: 2 }}>
            {activity.customer.contact_person}
          </div>
        )}
        <div className="small muted">🕑 {dateTime(activity.scheduled_at)}</div>

        {activity.customer.phone && (
          <a className="btn secondary" style={{ marginTop: 12 }} href={`tel:${activity.customer.phone}`}>
            📞 {activity.customer.phone}
          </a>
        )}
        {activity.activity_type === 'WHATSAPP' && activity.customer.phone && (
          <button
            className="btn secondary"
            style={{ marginTop: 10 }}
            onClick={() =>
              openExternal(
                `https://wa.me/${activity.customer.phone!.replace(/[^0-9]/g, '')}`,
              )
            }
          >
            💬 Open WhatsApp
          </button>
        )}
      </div>

      {activity.location && (
        <div className="card raised">
          <div className="section-title" style={{ marginTop: 0 }}>
            Where
          </div>
          <div className="strong">{activity.location.label ?? activity.location.city}</div>
          <div className="small muted">{activity.location.formatted}</div>
          <button
            className="btn"
            style={{ marginTop: 12 }}
            onClick={() => openExternal(activity.location!.maps_url)}
          >
            🧭 Navigate with Google Maps
          </button>
          {pinError && (
            <div style={{ marginTop: 10 }}>
              <Banner kind="error">{pinError}</Banner>
            </div>
          )}
          <button
            className="btn secondary"
            style={{ marginTop: 10 }}
            onClick={pinHere}
            disabled={pinning}
          >
            {pinning ? 'Reading your location…' : "📌 I'm here - save this spot"}
          </button>
          <div className="tiny muted" style={{ marginTop: 6 }}>
            Helps the office fix an address they only had as text.
          </div>
        </div>
      )}

      {activity.purpose && (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>
            Purpose from the office
          </div>
          <div className="timeline-note">{activity.purpose}</div>
        </div>
      )}

      {activity.status === 'COMPLETED' && (
        <div className="card">
          <div className="section-title" style={{ marginTop: 0 }}>
            Your report
          </div>
          <div className="small">{activity.completion_note}</div>
          <div className="tiny muted" style={{ marginTop: 6 }}>
            Reported {dateTime(activity.completed_at)}
          </div>
          <button className="btn secondary" style={{ marginTop: 12 }} onClick={() => setSheet('follow-up')}>
            Schedule a follow-up
          </button>
        </div>
      )}

      {open && (
        <div className="sticky-actions">
          <div className="btn-row">
            {activity.status === 'SCHEDULED' && (
              <button
                className="btn secondary"
                onClick={() => start.mutate(activity.id)}
                disabled={start.isPending}
              >
                Start
              </button>
            )}
            <button className="btn success" onClick={() => setSheet('complete')}>
              Complete
            </button>
          </div>
        </div>
      )}

      {sheet === 'complete' && (
        <CompleteSheet
          activity={activity}
          onClose={() => setSheet(null)}
          onDone={(message) => {
            setNotice(message);
            refresh();
            setSheet(null);
          }}
        />
      )}
      {sheet === 'follow-up' && (
        <FollowUpSheet
          activity={activity}
          onClose={() => setSheet(null)}
          onDone={(message) => {
            setNotice(message);
            refresh();
            setSheet(null);
          }}
        />
      )}
    </Screen>
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
  const [followUpAt, setFollowUpAt] = useState(pickerValue(dayjs().add(3, 'day').hour(11).minute(0)));
  const [followUpNote, setFollowUpNote] = useState('');
  const [busy, setBusy] = useState(false);

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
    <Sheet title="Complete activity" onClose={onClose}>
      <label className="field">
        <span>Outcome</span>
        <div className="chip-group">
          {OUTCOMES.map((value) => (
            <button
              key={value}
              type="button"
              className={`chip ${outcome === value ? 'selected' : ''}`}
              onClick={() => setOutcome(value)}
            >
              {humanize(value)}
            </button>
          ))}
        </div>
      </label>

      <label className="field">
        <span>What happened?</span>
        <textarea
          value={note}
          onChange={(event) => setNote(event.currentTarget.value)}
          placeholder="Customer wants a quotation for 30 MT."
        />
      </label>

      <label className="field">
        <span>
          <input
            type="checkbox"
            style={{ width: 20, height: 20, minHeight: 20, marginRight: 8, verticalAlign: 'middle' }}
            checked={withFollowUp}
            onChange={(event) => setWithFollowUp(event.currentTarget.checked)}
          />
          Schedule a follow-up for me
        </span>
      </label>

      {withFollowUp && (
        <>
          <label className="field">
            <span>Follow-up type</span>
            <div className="chip-group">
              {FOLLOW_UP_TYPES.map((value) => (
                <button
                  key={value}
                  type="button"
                  className={`chip ${followUpType === value ? 'selected' : ''}`}
                  onClick={() => setFollowUpType(value)}
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
              value={followUpAt}
              min={pickerValue(dayjs())}
              onChange={(event) => setFollowUpAt(event.currentTarget.value)}
            />
          </label>
          <label className="field">
            <span>Note (optional)</span>
            <textarea
              style={{ minHeight: 70 }}
              value={followUpNote}
              onChange={(event) => setFollowUpNote(event.currentTarget.value)}
              placeholder="Call about the October requirement."
            />
          </label>
        </>
      )}

      <div className="btn-row">
        <button className="btn secondary" onClick={onClose} disabled={busy}>
          Cancel
        </button>
        <button className="btn success" onClick={submit} disabled={busy || !note.trim()}>
          {busy ? 'Saving…' : 'Complete activity'}
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
    <Sheet title="Schedule follow-up" onClose={onClose}>
      {error && <Banner kind="error">{error}</Banner>}
      <div className="small muted" style={{ marginBottom: 12 }}>
        Stays with {activity.customer.name} and with you.
      </div>
      <label className="field">
        <span>Type</span>
        <div className="chip-group">
          {FOLLOW_UP_TYPES.map((value) => (
            <button
              key={value}
              type="button"
              className={`chip ${type === value ? 'selected' : ''}`}
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
        <button className="btn secondary" onClick={onClose} disabled={busy}>
          Cancel
        </button>
        <button className="btn" onClick={submit} disabled={busy}>
          {busy ? 'Scheduling…' : 'Schedule'}
        </button>
      </div>
    </Sheet>
  );
}
