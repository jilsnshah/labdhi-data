/**
 * Where a party asks for something, instead of being asked.
 *
 * The bid portal is the desk talking: here is a lot, name your price. This is
 * the other direction - a customer saying what they want, a supplier what they
 * have, a transporter which load they can take - and what they send goes
 * straight onto the book.
 *
 * The grade is asked for the way a trader thinks of one: the material, then a
 * grade of that material, then whose it is. Each step offers our list and
 * takes anything they type that is not on it, because turning away business to
 * keep a master list tidy is the wrong way round. Places are place names, for
 * the same reason: nobody outside knows our locations.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiError, api } from '@/api/client';
import type { PortalEnquiry, PortalHome, PortalOption } from '@/api/types';
import { formatDateTime, formatQuantity } from '@/lib/format';

import {
  PortalError,
  PortalFoot,
  PortalHeader,
  PortalLoading,
  useDocumentTitle,
} from './PortalChrome';

const UNITS = ['MT', 'KG', 'BAG', 'LITRE', 'PIECE'] as const;

const REPLY = 'We read every enquiry and come back to you on the same number.';

/** What the form is for, in the words of whoever is filling it in. */
const COPY = {
  CUSTOMER: {
    heading: 'Tell us what you need',
    blurb: 'Send us the grade and the quantity, and we will come back with our rate.',
    quantity: 'How much do you need?',
    rate: 'Your target rate (₹/kg)',
    rateHint: 'Optional - leave it blank to just ask for our rate',
    submit: 'Send my enquiry',
  },
  SUPPLIER: {
    heading: 'Tell us what you have',
    blurb: 'Send us the grade, the quantity and your rate, and we will get back to you.',
    quantity: 'How much can you supply?',
    rate: 'Your rate (₹/kg)',
    rateHint: 'Optional',
    submit: 'Send my offer',
  },
  TRANSPORT: {
    heading: 'Tell us the load you can take',
    blurb: 'Send us the route and your freight, and we will come back to you.',
    quantity: 'Load you can take',
    rate: 'Your freight (₹)',
    rateHint: 'Optional - for the whole load',
    submit: 'Send my quote',
  },
} as const;

type Kind = keyof typeof COPY;

/** A transporter raises a load; everyone else raises something with a grade in it. */
const KIND_OF: Record<string, Kind> = {
  CUSTOMER: 'CUSTOMER',
  SUPPLIER: 'SUPPLIER',
  TRANSPORTER: 'TRANSPORT',
};

/** One step of the grade: either a row of ours, or a name they typed. */
interface Choice {
  id: number | null;
  text: string;
}

const EMPTY: Choice = { id: null, text: '' };
const named = (choice: Choice) => choice.id !== null || choice.text.trim().length > 0;

export function PortalEnquiryPage() {
  const { code = '' } = useParams();
  const [who, setWho] = useState<PortalHome | null>(null);
  const [mine, setMine] = useState<PortalEnquiry[]>([]);
  const [error, setError] = useState<string | null>(null);
  useDocumentTitle('Place an enquiry');

  const [material, setMaterial] = useState<Choice>(EMPTY);
  const [grade, setGrade] = useState<Choice>(EMPTY);
  const [maker, setMaker] = useState<Choice>(EMPTY);
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState<string>('MT');
  const [fromPlace, setFromPlace] = useState('');
  const [toPlace, setToPlace] = useState('');
  const [rate, setRate] = useState('');
  const [notes, setNotes] = useState('');

  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadMine = useCallback(
    () => api.get<PortalEnquiry[]>(`/portal/${code}/enquiries`).then(setMine),
    [code],
  );

  useEffect(() => {
    api
      .get<PortalHome>(`/portal/${code}`)
      .then(setWho)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'This link is not valid.'));
    loadMine().catch(() => undefined);
  }, [code, loadMine]);

  if (error) return <PortalError message={error} />;
  if (!who) return <PortalLoading />;

  const kind = KIND_OF[who.party_type] ?? 'CUSTOMER';
  const copy = COPY[kind];
  const needsGrade = kind !== 'TRANSPORT';
  const bothEnds = fromPlace.trim().length > 0 && toPlace.trim().length > 0;
  const ready =
    Number(quantity) > 0 &&
    !busy &&
    (needsGrade ? named(material) && named(grade) && named(maker) : bothEnds);

  const clear = () => {
    setMaterial(EMPTY);
    setGrade(EMPTY);
    setMaker(EMPTY);
    setQuantity('');
    setFromPlace('');
    setToPlace('');
    setRate('');
    setNotes('');
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    setBusy(true);
    setFormError(null);
    try {
      await api.post<PortalEnquiry>(`/portal/${code}/enquiries`, {
        material_id: material.id,
        material_text: material.id === null ? material.text.trim() || null : null,
        grade_id: grade.id,
        grade_text: grade.id === null ? grade.text.trim() || null : null,
        manufacturer_id: maker.id,
        manufacturer_text: maker.id === null ? maker.text.trim() || null : null,
        quantity,
        unit,
        from_place: fromPlace.trim() || null,
        to_place: toPlace.trim() || null,
        rate: rate.trim() || null,
        notes: notes.trim() || null,
      });
      await loadMine();
      clear();
      setSent(true);
      window.setTimeout(() => setSent(false), 6000);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : 'Could not send your enquiry.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="portal">
      <PortalHeader
        name={who.participant_name}
        back={`/portal/${code}`}
        backLabel="Back to your bids"
      />
      <main className="portal-main">
        <div className="portal-bid-head">
          <h1>{copy.heading}</h1>
          <p className="portal-spec">{copy.blurb}</p>
        </div>

        <form className="portal-form" onSubmit={submit}>
          {formError && <div className="portal-error">{formError}</div>}
          {sent && (
            <div className="portal-ok">
              Your enquiry has reached the desk. We will come back to you.
            </div>
          )}

          {needsGrade && (
            <>
              <Picker
                code={code}
                path="materials"
                label="Which material?"
                placeholder="PVC, HDPE, PP…"
                choice={material}
                onChange={(next) => {
                  setMaterial(next);
                  // A grade belongs to one material; drop one that no longer fits.
                  setGrade(EMPTY);
                }}
              />
              <Picker
                code={code}
                path="grades"
                label="Which grade?"
                placeholder="K-67, MFI 0.3…"
                query={material.id !== null ? { material_id: material.id } : undefined}
                disabled={!named(material)}
                disabledHint="Tell us the material first."
                choice={grade}
                onChange={setGrade}
              />
              <Picker
                code={code}
                path="manufacturers"
                label="Whose material?"
                placeholder="Reliance, Finolex…"
                choice={maker}
                onChange={setMaker}
              />
            </>
          )}

          <div className="portal-row">
            <label className="grow">
              <span>{copy.quantity}</span>
              <input
                type="number"
                inputMode="decimal"
                step="0.001"
                min="0"
                required
                value={quantity}
                onChange={(event) => setQuantity(event.currentTarget.value)}
                placeholder="20"
              />
            </label>
            <label className="portal-narrow">
              <span>Unit</span>
              <select value={unit} onChange={(event) => setUnit(event.currentTarget.value)}>
                {UNITS.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {kind === 'TRANSPORT' && (
            <div className="portal-row">
              <label className="grow">
                <span>Pick up from</span>
                <input
                  required
                  value={fromPlace}
                  onChange={(event) => setFromPlace(event.currentTarget.value)}
                  placeholder="Gandhidham"
                />
              </label>
              <label className="grow">
                <span>Deliver to</span>
                <input
                  required
                  value={toPlace}
                  onChange={(event) => setToPlace(event.currentTarget.value)}
                  placeholder="Mumbai"
                />
              </label>
            </div>
          )}

          {kind === 'CUSTOMER' && (
            <label>
              <span>Deliver to</span>
              <input
                value={toPlace}
                onChange={(event) => setToPlace(event.currentTarget.value)}
                placeholder="Rajkot"
              />
              <small className="portal-hint">City or area is enough</small>
            </label>
          )}

          <label>
            <span>{copy.rate}</span>
            <input
              type="number"
              inputMode="decimal"
              step="0.01"
              min="0"
              value={rate}
              onChange={(event) => setRate(event.currentTarget.value)}
              placeholder="0.00"
            />
            <small className="portal-hint">{copy.rateHint}</small>
          </label>

          <label>
            <span>Anything we should know (optional)</span>
            <textarea
              rows={3}
              value={notes}
              onChange={(event) => setNotes(event.currentTarget.value)}
              placeholder="Packing, payment terms, when you need it…"
            />
          </label>

          <button type="submit" disabled={!ready}>
            {busy ? 'Sending…' : copy.submit}
          </button>
        </form>

        {mine.length > 0 && (
          <>
            <h2 className="portal-section">What you have sent us</h2>
            <div className="portal-list">
              {mine.map((enquiry) => (
                <SentCard key={enquiry.id} enquiry={enquiry} />
              ))}
            </div>
          </>
        )}

        <p className="portal-note">
          Looking for a bid you were invited to? <Link to={`/portal/${code}`}>Your bids</Link>.
        </p>
      </main>
      <PortalFoot note={REPLY} />
    </div>
  );
}

function SentCard({ enquiry }: { enquiry: PortalEnquiry }) {
  const route = [enquiry.from_place, enquiry.to_place].filter(Boolean).join(' → ');
  const unit = enquiry.inquiry_type === 'TRANSPORT' ? '₹' : '₹/kg';
  return (
    <div className="portal-card portal-card-still">
      <div className="portal-card-top">
        <span className="portal-pill">With the desk</span>
      </div>
      <div className="portal-card-title">{enquiry.product_name ?? (route || 'Enquiry')}</div>
      <div className="portal-card-meta">
        {formatQuantity(enquiry.quantity, enquiry.unit)}
        {enquiry.product_name && route ? ` · ${route}` : ''}
        {enquiry.rate ? ` · you said ${unit} ${enquiry.rate}` : ''}
      </div>
      <div className="portal-card-foot">Sent {formatDateTime(enquiry.created_at)}</div>
    </div>
  );
}

/**
 * One step of the grade: search ours, or keep what you typed.
 *
 * Searching is the whole interaction - a trader types three characters of what
 * they want. Nothing matching is not an error: what they typed is the answer,
 * and the desk ends up with the name rather than a shrug.
 */
function Picker({
  code,
  path,
  label,
  placeholder,
  query,
  disabled,
  disabledHint,
  choice,
  onChange,
}: {
  code: string;
  path: 'materials' | 'grades' | 'manufacturers';
  label: string;
  placeholder: string;
  query?: Record<string, number>;
  disabled?: boolean;
  disabledHint?: string;
  choice: Choice;
  onChange: (choice: Choice) => void;
}) {
  const [matches, setMatches] = useState<PortalOption[]>([]);
  const [open, setOpen] = useState(false);
  const typed = choice.text.trim();
  const picked = choice.id !== null;
  // Serialised so the effect below compares it by value, not by identity.
  const scope = JSON.stringify(query ?? {});

  useEffect(() => {
    if (disabled || picked) {
      setMatches([]);
      return undefined;
    }
    const timer = window.setTimeout(() => {
      api
        .get<PortalOption[]>(`/portal/${code}/${path}`, { ...JSON.parse(scope), q: typed })
        .then(setMatches)
        .catch(() => setMatches([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [code, path, typed, picked, disabled, scope]);

  const showList = open && !picked && !disabled && matches.length > 0;
  const nothingFound = open && !picked && !disabled && typed.length >= 2 && matches.length === 0;

  return (
    <label className="portal-picker">
      <span>{label}</span>
      <input
        value={choice.text}
        disabled={disabled}
        onChange={(event) => {
          onChange({ id: null, text: event.currentTarget.value });
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        placeholder={disabled ? '' : placeholder}
        autoComplete="off"
      />
      {disabled && <small className="portal-hint">{disabledHint}</small>}
      {picked && (
        <small className="portal-hint">
          Picked from our list.{' '}
          <button
            type="button"
            className="portal-link"
            onClick={() => onChange({ id: null, text: '' })}
          >
            change
          </button>
        </small>
      )}
      {nothingFound && (
        <small className="portal-hint">
          Not in our list - that is fine, we will go by what you have typed.
        </small>
      )}
      {showList && (
        <div className="portal-options" role="listbox">
          {matches.map((option) => (
            <button
              key={option.id}
              type="button"
              className="portal-option"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                onChange({ id: option.id, text: option.name });
                setOpen(false);
              }}
            >
              {option.name}
            </button>
          ))}
        </div>
      )}
    </label>
  );
}
