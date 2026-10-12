/**
 * Log an activity the salesperson did (or will do) on their own: a cold call,
 * a walk-in visit, a WhatsApp to someone new. Assignment stays with the office;
 * this is the field's own record, and it is always assigned to the signed-in
 * salesperson by the server.
 */

import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useContacts, useRefreshAll } from '@/api/hooks';
import type {
  ActivityOutcome,
  ActivityType,
  FieldContact,
  LogActivityRequest,
  LogActivityResponse,
} from '@/api/types';
import { Icon, TypeIcon } from '@/components/Icon';
import { Avatar, Banner, Screen } from '@/components/Shell';
import { dayjs, humanize, shortAgo } from '@/lib/format';
import { currentPosition } from '@/lib/native';
import * as outbox from '@/lib/offline';

/** Must match SALESPERSON_FOLLOWUP_TYPES on the backend. */
const TYPES: { type: ActivityType; label: string; verb: string }[] = [
  { type: 'CALL', label: 'Call', verb: 'call' },
  { type: 'VISIT', label: 'Visit', verb: 'visit' },
  { type: 'WHATSAPP', label: 'WhatsApp', verb: 'WhatsApp' },
  { type: 'SMS', label: 'SMS', verb: 'SMS' },
];

const OUTCOMES: { code: ActivityOutcome; label: string; tone: string }[] = [
  { code: 'CUSTOMER_INTERESTED', label: 'Interested', tone: 'teal' },
  { code: 'FOLLOW_UP_REQUIRED', label: 'Needs follow-up', tone: 'amber' },
  { code: 'COMPLETED', label: 'Just a check-in', tone: 'slate' },
  { code: 'CUSTOMER_NOT_INTERESTED', label: 'Not interested', tone: 'rust' },
  { code: 'NO_RESPONSE', label: 'No response', tone: 'slate' },
  { code: 'OTHER', label: 'Other', tone: 'slate' },
];

const pickerValue = (date: dayjs.Dayjs) => date.format('YYYY-MM-DDTHH:mm');

type Who = { kind: 'known'; contact: FieldContact } | { kind: 'new' } | null;

type DoneWhen = 'now' | '30m' | '1h' | 'custom';

interface Result {
  synced: boolean;
  label: string;
  verb: string;
  done: boolean;
  followUpAt: string | null;
  response?: LogActivityResponse;
}

export function LogActivityPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const refresh = useRefreshAll();
  const initialType = (params.get('type') as ActivityType) || 'CALL';

  const [type, setType] = useState<ActivityType>(
    TYPES.some((item) => item.type === initialType) ? initialType : 'CALL',
  );
  const [done, setDone] = useState(true);

  const [who, setWho] = useState<Who>(null);
  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [newName, setNewName] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newPerson, setNewPerson] = useState('');
  const [newKind, setNewKind] = useState<'CUSTOMER' | 'SUPPLIER'>('CUSTOMER');

  const [place, setPlace] = useState('');
  const [gps, setGps] = useState<{ latitude: number; longitude: number } | null>(null);
  const [gpsBusy, setGpsBusy] = useState(false);
  const [gpsError, setGpsError] = useState<string | null>(null);

  const [outcome, setOutcome] = useState<ActivityOutcome | null>(null);
  const [note, setNote] = useState('');
  const [doneWhen, setDoneWhen] = useState<DoneWhen>('now');
  const [doneAt, setDoneAt] = useState(pickerValue(dayjs().subtract(2, 'hour')));
  const [planAt, setPlanAt] = useState(pickerValue(dayjs().add(1, 'day').hour(11).minute(0)));

  const [withFollowUp, setWithFollowUp] = useState(false);
  const [followUpType, setFollowUpType] = useState<ActivityType>('CALL');
  const [followUpAt, setFollowUpAt] = useState(
    pickerValue(dayjs().add(3, 'day').hour(11).minute(0)),
  );

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 220);
    return () => clearTimeout(timer);
  }, [query]);

  const contacts = useContacts(debounced);
  const isVisit = type === 'VISIT';
  const verb = TYPES.find((item) => item.type === type)?.verb ?? 'activity';
  const name = who?.kind === 'known' ? who.contact.name : newName.trim();
  const knownPlace = who?.kind === 'known' ? who.contact.place : null;

  // Follow outcome to the obvious next step.
  useEffect(() => {
    if (outcome === 'FOLLOW_UP_REQUIRED' || outcome === 'CUSTOMER_INTERESTED')
      setWithFollowUp(true);
  }, [outcome]);

  const missing = useMemo(() => {
    if (!who) return 'Choose who it was with';
    if (who.kind === 'new' && !newName.trim()) return 'Add a name for the new contact';
    if (isVisit && !place.trim() && !gps && !knownPlace) return 'Say where the visit is';
    if (done && !outcome) return 'Pick how it went';
    if (done && !note.trim()) return 'Add a short note';
    if (done && doneWhen === 'custom') {
      const at = dayjs(doneAt);
      if (at.isAfter(dayjs())) return 'A finished activity cannot be in the future';
      if (at.isBefore(dayjs().subtract(7, 'day'))) return 'Only the last 7 days can be logged';
    }
    if (!done && !dayjs(planAt).isAfter(dayjs())) return 'Pick a time in the future';
    return null;
  }, [
    who,
    newName,
    isVisit,
    place,
    gps,
    knownPlace,
    done,
    outcome,
    note,
    doneWhen,
    doneAt,
    planAt,
  ]);

  const pin = async () => {
    setGpsBusy(true);
    setGpsError(null);
    try {
      setGps(await currentPosition());
    } catch (err) {
      setGpsError(err instanceof Error ? err.message : 'Could not read your location.');
    } finally {
      setGpsBusy(false);
    }
  };

  const doneTime = () => {
    if (doneWhen === 'now') return dayjs();
    if (doneWhen === '30m') return dayjs().subtract(30, 'minute');
    if (doneWhen === '1h') return dayjs().subtract(1, 'hour');
    return dayjs(doneAt);
  };

  const submit = async () => {
    if (busy || missing || !who) return;
    setBusy(true);
    setError(null);
    const payload: LogActivityRequest = {
      activity_type: type,
      done,
      contact_ref: who.kind === 'known' ? who.contact.ref : null,
      new_contact:
        who.kind === 'new'
          ? {
              name: newName.trim(),
              phone: newPhone.trim() || null,
              contact_person: newPerson.trim() || null,
              party_type: newKind,
            }
          : null,
      outcome_code: done ? outcome : null,
      note: note.trim() || null,
      at: (done ? doneTime() : dayjs(planAt)).toISOString(),
      place: isVisit ? place.trim() || null : null,
      latitude: isVisit && gps ? gps.latitude.toFixed(6) : null,
      longitude: isVisit && gps ? gps.longitude.toFixed(6) : null,
    };
    const token = outbox.newToken();
    const label = `${humanize(type)} · ${name}`;
    outbox.enqueue({
      kind: 'log',
      token,
      label,
      payload,
      followUp:
        done && withFollowUp
          ? {
              activity_type: followUpType,
              scheduled_at: dayjs(followUpAt).toISOString(),
              note: null,
            }
          : null,
    });
    await outbox.flush();
    setBusy(false);

    const response = outbox.resultFor(token);
    const stillQueued = outbox.pending().some((item) => item.token === token);
    if (!response && !stillQueued) {
      setError(outbox.takeRejection() ?? 'The office server refused this entry.');
      return;
    }
    refresh();
    setResult({
      synced: Boolean(response),
      label,
      verb: TYPES.find((item) => item.type === type)?.label ?? 'Activity',
      done,
      followUpAt: done && withFollowUp ? followUpAt : null,
      response,
    });
  };

  const reset = () => {
    setResult(null);
    setWho(null);
    setQuery('');
    setNewName('');
    setNewPhone('');
    setNewPerson('');
    setPlace('');
    setGps(null);
    setOutcome(null);
    setNote('');
    setDoneWhen('now');
    setWithFollowUp(false);
  };

  if (result) {
    return <LoggedScreen result={result} onAnother={reset} onDone={() => navigate('/today')} />;
  }

  const contactList = contacts.data ?? [];
  const searching = Boolean(debounced);

  return (
    <Screen
      eyebrow="Your own work"
      title={
        <>
          Log a <em>{verb}</em>
        </>
      }
      back
      withNav={false}
      footer={
        <>
          {missing && <div className="footer-hint">{missing}</div>}
          <button
            className={`btn ${done ? 'primary' : 'brass'}`}
            disabled={Boolean(missing) || busy}
            onClick={submit}
          >
            {busy ? (
              'Saving…'
            ) : done ? (
              <>
                <Icon name="check" size={18} stroke={2.4} /> Save {verb}
              </>
            ) : (
              <>
                <Icon name="calendar" size={18} /> Plan {verb}
              </>
            )}
          </button>
        </>
      }
    >
      {error && <Banner kind="error">{error}</Banner>}

      {/* 1. What --------------------------------------------------------- */}
      <section className="form-card">
        <StepLabel n={1} title="What" />
        <div className="type-grid">
          {TYPES.map((item) => (
            <button
              key={item.type}
              className={`type-option${type === item.type ? ' on' : ''}`}
              onClick={() => setType(item.type)}
            >
              <TypeIcon type={item.type} size={36} />
              <span>{item.label}</span>
            </button>
          ))}
        </div>
        <div className="segmented" style={{ marginTop: 14 }}>
          <button className={done ? 'on' : undefined} onClick={() => setDone(true)}>
            <Icon name="check" size={15} stroke={2.2} /> Already done
          </button>
          <button className={!done ? 'on' : undefined} onClick={() => setDone(false)}>
            <Icon name="calendar" size={15} /> Plan for later
          </button>
        </div>
      </section>

      {/* 2. Who ---------------------------------------------------------- */}
      <section className="form-card">
        <StepLabel n={2} title="Who" />
        {who?.kind === 'known' && (
          <div className="picked">
            <Avatar
              name={who.contact.name}
              size={44}
              tone={who.contact.party_type === 'SUPPLIER' ? 'teal' : 'indigo'}
            />
            <div className="grow" style={{ minWidth: 0 }}>
              <div className="strong ellipsis">{who.contact.name}</div>
              <div className="tiny muted ellipsis">
                {[who.contact.contact_person, who.contact.phone, who.contact.place]
                  .filter(Boolean)
                  .join(' · ') || humanize(who.contact.party_type)}
              </div>
            </div>
            <button className="btn ghost small" onClick={() => setWho(null)}>
              Change
            </button>
          </div>
        )}

        {who?.kind === 'new' && (
          <div className="new-contact">
            <div className="row between" style={{ marginBottom: 10 }}>
              <span className="tag brass">
                <Icon name="userPlus" size={13} /> New contact
              </span>
              <button className="link-btn" onClick={() => setWho(null)}>
                Pick existing instead
              </button>
            </div>
            <div className="segmented small" style={{ marginBottom: 12 }}>
              <button
                className={newKind === 'CUSTOMER' ? 'on' : undefined}
                onClick={() => setNewKind('CUSTOMER')}
              >
                Buyer / customer
              </button>
              <button
                className={newKind === 'SUPPLIER' ? 'on' : undefined}
                onClick={() => setNewKind('SUPPLIER')}
              >
                Seller / supplier
              </button>
            </div>
            <label className="field">
              <span>Business name</span>
              <input
                value={newName}
                autoFocus
                onChange={(event) => setNewName(event.currentTarget.value)}
                placeholder="e.g. Shree Ganesh Pipes"
              />
            </label>
            <div className="field-pair">
              <label className="field">
                <span>Phone</span>
                <input
                  type="tel"
                  inputMode="tel"
                  value={newPhone}
                  onChange={(event) => setNewPhone(event.currentTarget.value)}
                  placeholder="+91"
                />
              </label>
              <label className="field">
                <span>Person met</span>
                <input
                  value={newPerson}
                  onChange={(event) => setNewPerson(event.currentTarget.value)}
                  placeholder="Optional"
                />
              </label>
            </div>
            <div className="tiny muted">The office sees this as a new prospect from the field.</div>
          </div>
        )}

        {!who && (
          <>
            <div className="search">
              <Icon name="search" size={18} />
              <input
                value={query}
                onChange={(event) => setQuery(event.currentTarget.value)}
                placeholder="Search people you've worked with"
              />
              {query && (
                <button className="link-btn" onClick={() => setQuery('')} aria-label="Clear">
                  <Icon name="close" size={16} />
                </button>
              )}
            </div>
            <button
              className="new-contact-btn"
              onClick={() => {
                setNewName(query.trim());
                setWho({ kind: 'new' });
              }}
            >
              <span className="round-btn brass">
                <Icon name="userPlus" size={17} />
              </span>
              <span className="grow">
                <span className="strong">
                  {query.trim() ? `Add “${query.trim()}” as new` : 'Someone new'}
                </span>
                <span className="tiny muted" style={{ display: 'block' }}>
                  Cold call or walk-in - they become a prospect
                </span>
              </span>
              <Icon name="chevron" size={16} />
            </button>
            <div className="contact-list">
              {!searching && contactList.length > 0 && <div className="list-caption">Recent</div>}
              {contactList.slice(0, searching ? 20 : 6).map((contact) => (
                <button
                  key={contact.ref}
                  className="contact-row"
                  onClick={() => setWho({ kind: 'known', contact })}
                >
                  <Avatar
                    name={contact.name}
                    size={38}
                    tone={contact.party_type === 'SUPPLIER' ? 'teal' : 'indigo'}
                  />
                  <span className="grow" style={{ minWidth: 0 }}>
                    <span className="contact-name ellipsis">
                      {contact.name}
                      {contact.is_prospect && <span className="tag brass">Prospect</span>}
                    </span>
                    <span className="tiny muted ellipsis" style={{ display: 'block' }}>
                      {[humanize(contact.party_type), contact.place].filter(Boolean).join(' · ')}
                    </span>
                  </span>
                  <span className="contact-when">{shortAgo(contact.last_activity_at)}</span>
                </button>
              ))}
              {searching && !contacts.isFetching && contactList.length === 0 && (
                <div className="tiny muted" style={{ padding: '6px 2px' }}>
                  No one by that name in your book yet.
                </div>
              )}
              {contacts.isError && (
                <div className="tiny muted" style={{ padding: '6px 2px' }}>
                  Offline - your contacts load when you have signal. You can still add someone new.
                </div>
              )}
            </div>
          </>
        )}
      </section>

      {/* 3. Where (visits) ------------------------------------------------ */}
      {isVisit && (
        <section className="form-card">
          <StepLabel n={3} title="Where" />
          <label className="field">
            <span>Place</span>
            <input
              value={place}
              onChange={(event) => setPlace(event.currentTarget.value)}
              placeholder={knownPlace ? `Usual: ${knownPlace}` : 'Shop / area / landmark'}
            />
          </label>
          {gps ? (
            <div className="gps-chip">
              <Icon name="crosshair" size={16} />
              <span className="grow">
                Pinned ·{' '}
                <span className="mono">
                  {gps.latitude.toFixed(4)}, {gps.longitude.toFixed(4)}
                </span>
              </span>
              <button className="link-btn" onClick={() => setGps(null)}>
                Remove
              </button>
            </div>
          ) : (
            <button className="btn ghost" onClick={pin} disabled={gpsBusy}>
              <Icon name="crosshair" size={17} />
              {gpsBusy ? 'Reading your location…' : 'Use my current location'}
            </button>
          )}
          {gpsError && (
            <div className="tiny" style={{ color: 'var(--rust)', marginTop: 8 }}>
              {gpsError}
            </div>
          )}
          {knownPlace && !place && !gps && (
            <div className="tiny muted" style={{ marginTop: 8 }}>
              Leave empty to use {knownPlace}.
            </div>
          )}
        </section>
      )}

      {/* 4. How it went / when ------------------------------------------- */}
      {done ? (
        <section className="form-card">
          <StepLabel n={isVisit ? 4 : 3} title="How did it go" />
          <div className="outcome-grid">
            {OUTCOMES.map((item) => (
              <button
                key={item.code}
                className={`outcome tone-${item.tone}${outcome === item.code ? ' on' : ''}`}
                onClick={() => setOutcome(item.code)}
              >
                <span className="outcome-dot" />
                {item.label}
              </button>
            ))}
          </div>
          <label className="field" style={{ marginTop: 14 }}>
            <span>Note for the office</span>
            <textarea
              value={note}
              onChange={(event) => setNote(event.currentTarget.value)}
              placeholder={
                type === 'VISIT'
                  ? 'Uses 20 MT/month PVC K-67, buys from Ahmedabad. Wants a rate.'
                  : 'Spoke to the owner - send rate for LLDPE film by Friday.'
              }
            />
          </label>
          <div className="field">
            <span>When</span>
            <div className="chip-group fit">
              {(
                [
                  ['now', 'Just now'],
                  ['30m', '30 min ago'],
                  ['1h', '1 h ago'],
                  ['custom', 'Earlier…'],
                ] as [DoneWhen, string][]
              ).map(([key, label]) => (
                <button
                  key={key}
                  className={`chip${doneWhen === key ? ' selected' : ''}`}
                  onClick={() => setDoneWhen(key)}
                >
                  {label}
                </button>
              ))}
            </div>
            {doneWhen === 'custom' && (
              <input
                type="datetime-local"
                style={{ marginTop: 10 }}
                value={doneAt}
                min={pickerValue(dayjs().subtract(7, 'day'))}
                max={pickerValue(dayjs())}
                onChange={(event) => setDoneAt(event.currentTarget.value)}
              />
            )}
          </div>
        </section>
      ) : (
        <section className="form-card">
          <StepLabel n={isVisit ? 4 : 3} title="When" />
          <div className="chip-group">
            {[
              ...(dayjs().hour() < 16 ? [['Today 5 PM', dayjs().hour(17).minute(0)]] : []),
              ['Tomorrow 11 AM', dayjs().add(1, 'day').hour(11).minute(0)],
              ['In 3 days', dayjs().add(3, 'day').hour(11).minute(0)],
              ['Next week', dayjs().add(7, 'day').hour(11).minute(0)],
            ].map(([label, value]) => {
              const picked = pickerValue(value as dayjs.Dayjs);
              return (
                <button
                  key={label as string}
                  className={`chip${planAt === picked ? ' selected' : ''}`}
                  onClick={() => setPlanAt(picked)}
                >
                  {label as string}
                </button>
              );
            })}
          </div>
          <input
            type="datetime-local"
            style={{ marginTop: 10 }}
            value={planAt}
            min={pickerValue(dayjs())}
            onChange={(event) => setPlanAt(event.currentTarget.value)}
          />
          <label className="field" style={{ marginTop: 14 }}>
            <span>Purpose (optional)</span>
            <textarea
              style={{ minHeight: 72 }}
              value={note}
              onChange={(event) => setNote(event.currentTarget.value)}
              placeholder="Introduce our HDPE range, ask for monthly volume."
            />
          </label>
        </section>
      )}

      {/* 5. Follow-up ----------------------------------------------------- */}
      {done && (
        <section className={`form-card toggle-card${withFollowUp ? ' on' : ''}`}>
          <button className="toggle-row" onClick={() => setWithFollowUp((value) => !value)}>
            <span className="grow">
              <span className="strong">Schedule a follow-up</span>
              <span className="tiny muted" style={{ display: 'block' }}>
                Lands in your plan, with {name || 'them'}
              </span>
            </span>
            <span className={`switch${withFollowUp ? ' on' : ''}`} />
          </button>
          {withFollowUp && (
            <div style={{ marginTop: 14 }}>
              <div className="chip-group">
                {TYPES.map((item) => (
                  <button
                    key={item.type}
                    className={`chip${followUpType === item.type ? ' selected' : ''}`}
                    onClick={() => setFollowUpType(item.type)}
                  >
                    {item.label}
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
            </div>
          )}
        </section>
      )}
    </Screen>
  );
}

function StepLabel({ n, title }: { n: number; title: string }) {
  return (
    <div className="step-label">
      <span className="step-n">{n}</span>
      {title}
    </div>
  );
}

function LoggedScreen({
  result,
  onAnother,
  onDone,
}: {
  result: Result;
  onAnother: () => void;
  onDone: () => void;
}) {
  return (
    <div className="logged">
      <div className="logged-mark">
        <svg viewBox="0 0 96 96" width="96" height="96" aria-hidden>
          <circle cx="48" cy="48" r="44" className="logged-ring" />
          <path d="M30 49l12 12 24-26" className="logged-check" />
        </svg>
      </div>
      <div className="eyebrow">{result.synced ? 'Sent to the office' : 'Saved on this phone'}</div>
      <h1>
        {result.done ? (
          <>
            {result.verb} <em>logged</em>
          </>
        ) : (
          <>
            {result.verb} <em>planned</em>
          </>
        )}
      </h1>
      <p className="logged-label">{result.label.split(' · ').slice(1).join(' · ')}</p>
      <div className="logged-notes">
        {result.response?.new_contact_created && (
          <div className="logged-note">
            <Icon name="userPlus" size={16} /> Added as a new prospect for the office
          </div>
        )}
        {result.followUpAt && (
          <div className="logged-note">
            <Icon name="calendar" size={16} /> Follow-up on{' '}
            {dayjs(result.followUpAt).format('ddd D MMM, h:mm A')}
          </div>
        )}
        {!result.done && (
          <div className="logged-note">
            <Icon name="calendar" size={16} /> It's in your plan
          </div>
        )}
        {!result.synced && (
          <div className="logged-note warn">
            <Icon name="cloud" size={16} /> No signal - it syncs by itself later
          </div>
        )}
      </div>
      <div className="logged-actions">
        <button className="btn glass" onClick={onAnother}>
          <Icon name="plus" size={17} /> Log another
        </button>
        <button className="btn brass" onClick={onDone}>
          Back to today
        </button>
      </div>
    </div>
  );
}
