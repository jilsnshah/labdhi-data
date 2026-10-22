/**
 * Where a party asks for something, instead of being asked.
 *
 * The bid portal is the desk talking: here is a lot, name your price. This is
 * the other direction - a customer saying what they want, a supplier what they
 * have, a transporter which load they can take - and it arrives on the desk as
 * a request, not as a record.
 *
 * So the form asks for as little as it can get away with. Nobody filling this
 * in on a phone knows our product master or our location list: they pick a
 * grade if they can find it, type its name if they cannot, and write place
 * names as places, not as rows. Mapping that onto master data is the desk's
 * job, which is the one thing a public form must never be trusted with.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiError, api } from '@/api/client';
import type { PortalEnquiry, PortalHome, PortalProduct } from '@/api/types';
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
    product: 'Which grade do you need?',
    quantity: 'How much do you need?',
    place: 'Deliver to',
    placeHint: 'City or area is enough',
    rate: 'Your target rate (₹/kg)',
    rateHint: 'Optional - leave it blank to just ask for our rate',
    submit: 'Send my enquiry',
  },
  SUPPLIER: {
    heading: 'Tell us what you have',
    blurb: 'Send us the grade, the quantity and your rate, and we will get back to you.',
    product: 'Which grade are you offering?',
    quantity: 'How much can you supply?',
    place: 'Ships from',
    placeHint: 'City or area is enough',
    rate: 'Your rate (₹/kg)',
    rateHint: 'Optional',
    submit: 'Send my offer',
  },
  TRANSPORT: {
    heading: 'Tell us the load you can take',
    blurb: 'Send us the route and your freight, and we will come back to you.',
    product: '',
    quantity: 'Load you can take',
    place: '',
    placeHint: '',
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

export function PortalEnquiryPage() {
  const { code = '' } = useParams();
  const [who, setWho] = useState<PortalHome | null>(null);
  const [mine, setMine] = useState<PortalEnquiry[]>([]);
  const [error, setError] = useState<string | null>(null);
  useDocumentTitle('Place an enquiry');

  const [productId, setProductId] = useState<number | null>(null);
  const [productText, setProductText] = useState('');
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
  const needsProduct = kind !== 'TRANSPORT';
  const namedProduct = productId !== null || productText.trim().length > 0;
  const bothEnds = fromPlace.trim().length > 0 && toPlace.trim().length > 0;
  const ready =
    Number(quantity) > 0 && (needsProduct ? namedProduct : bothEnds) && !busy;

  const clear = () => {
    setProductId(null);
    setProductText('');
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
        product_id: productId,
        product_text: productId === null ? productText.trim() || null : null,
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

          {needsProduct && (
            <GradePicker
              code={code}
              label={copy.product}
              productId={productId}
              typed={productText}
              onPick={(product) => {
                setProductId(product?.id ?? null);
                setProductText(product?.display_name ?? '');
              }}
              onType={(value) => {
                setProductId(null);
                setProductText(value);
              }}
            />
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

          {kind === 'TRANSPORT' ? (
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
          ) : (
            <label>
              <span>{copy.place}</span>
              <input
                value={kind === 'SUPPLIER' ? fromPlace : toPlace}
                onChange={(event) =>
                  kind === 'SUPPLIER'
                    ? setFromPlace(event.currentTarget.value)
                    : setToPlace(event.currentTarget.value)
                }
                placeholder="Rajkot"
              />
              <small className="portal-hint">{copy.placeHint}</small>
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

/** How far one of their enquiries has got. They are never told who else wrote in. */
const STANDING: Record<PortalEnquiry['status'], { tone: string; label: string }> = {
  NEW: { tone: '', label: 'With the desk' },
  ACCEPTED: { tone: 'won', label: 'Taken up' },
  DECLINED: { tone: 'lost', label: 'Not this time' },
};

function SentCard({ enquiry }: { enquiry: PortalEnquiry }) {
  const standing = STANDING[enquiry.status];
  const route = [enquiry.from_place, enquiry.to_place].filter(Boolean).join(' → ');
  const unit = enquiry.inquiry_type === 'TRANSPORT' ? '₹' : '₹/kg';
  return (
    <div className="portal-card portal-card-still">
      <div className="portal-card-top">
        <span className={`portal-pill ${standing.tone}`}>{standing.label}</span>
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
 * Pick a grade from ours, or type your own.
 *
 * Searching is the whole interaction: a trader knows what they want and types
 * three characters of it. If nothing matches, what they typed is the answer -
 * refusing an enquiry because our master data is short of a grade would be
 * turning away business to keep a list tidy.
 */
function GradePicker({
  code,
  label,
  productId,
  typed,
  onPick,
  onType,
}: {
  code: string;
  label: string;
  productId: number | null;
  typed: string;
  onPick: (product: PortalProduct | null) => void;
  onType: (value: string) => void;
}) {
  const [matches, setMatches] = useState<PortalProduct[]>([]);
  const [open, setOpen] = useState(false);
  const query = typed.trim();

  useEffect(() => {
    if (productId !== null || query.length < 2) {
      setMatches([]);
      return undefined;
    }
    const timer = window.setTimeout(() => {
      api
        .get<PortalProduct[]>(`/portal/${code}/products`, { q: query })
        .then(setMatches)
        .catch(() => setMatches([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [code, query, productId]);

  const showList = open && productId === null && matches.length > 0;
  const nothingFound = useMemo(
    () => open && productId === null && query.length >= 2 && matches.length === 0,
    [open, productId, query, matches],
  );

  return (
    <label className="portal-picker">
      <span>{label}</span>
      <input
        value={typed}
        onChange={(event) => {
          onType(event.currentTarget.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        placeholder="Start typing, e.g. K-67"
        autoComplete="off"
      />
      {productId !== null && (
        <small className="portal-hint">
          Picked from our list.{' '}
          <button type="button" className="portal-link" onClick={() => onPick(null)}>
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
          {matches.map((product) => (
            <button
              key={product.id}
              type="button"
              className="portal-option"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                onPick(product);
                setOpen(false);
              }}
            >
              {product.display_name}
            </button>
          ))}
        </div>
      )}
    </label>
  );
}
