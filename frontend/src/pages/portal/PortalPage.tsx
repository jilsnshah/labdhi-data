/**
 * The participant's side of a bid. No sign-in, no CRM, no other bidders.
 *
 * Opened on a phone from a forwarded link, so it is one column, large type and
 * a single number to beat. The page shows what the server allows and nothing
 * more: their own offer, the standing best price, and how many are in.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { api } from '@/api/client';
import { ApiError } from '@/api/client';
import type { PortalBid, PortalHome } from '@/api/types';
import { formatDateTime, formatQuantity } from '@/lib/format';

import {
  PortalError,
  PortalFoot,
  PortalHeader,
  PortalLoading,
  useDocumentTitle,
  useLive,
} from './PortalChrome';

const PRIVACY = 'Offers are private. Other bidders never see your name or your price.';

const unitOf = (bid: PortalBid) => (bid.bid_type === 'TRANSPORT' ? '₹' : '₹/kg');

/**
 * What a closed bid comes to, in the words the party is owed.
 *
 * A bidder who has lost is told so plainly and told nothing about who won: the
 * portal is anonymous while the bid runs and stays anonymous afterwards.
 * UNDECIDED is the honest answer while the desk is still making up its mind.
 */
function outcomeOf(bid: PortalBid): { tone: string; label: string; said: string } | null {
  switch (bid.result) {
    case 'WON':
      return {
        tone: 'won',
        label: 'You won this',
        said: 'Your offer was accepted. We will be in touch to confirm the details.',
      };
    case 'NOT_SELECTED':
      return {
        tone: 'lost',
        label: 'Not selected',
        said: 'This one went elsewhere. Thank you for bidding — we will send you the next.',
      };
    case 'NO_WINNER':
      return {
        tone: 'none',
        label: 'Closed with no winner',
        said: 'The bid was closed without any offer being taken.',
      };
    case 'UNDECIDED':
      return {
        tone: '',
        label: 'Closed',
        said: 'Bidding has ended. We are going through the offers and will let you know.',
      };
    default:
      return null;
  }
}

export function PortalHomePage() {
  const { code = '' } = useParams();
  const [data, setData] = useState<PortalHome | null>(null);
  const [error, setError] = useState<string | null>(null);
  useDocumentTitle('Your bids');

  const load = useCallback(
    () =>
      api
        .get<PortalHome>(`/portal/${code}`)
        .then(setData)
        .catch((err) =>
          setError(err instanceof ApiError ? err.message : 'This link is not valid.'),
        ),
    [code],
  );

  useEffect(() => {
    load();
  }, [load]);
  useLive(load, Boolean(data?.open_bids.length), 15000);

  if (error) return <PortalError message={error} />;
  if (!data) return <PortalLoading />;

  return (
    <div className="portal">
      <PortalHeader name={data.participant_name} />
      <main className="portal-main">
        {/* The other direction: they ask us, rather than waiting to be asked. */}
        <Link to={`/portal/${code}/enquire`} className="portal-cta">
          <span className="portal-cta-main">Have something for us?</span>
          <span className="portal-cta-hint">
            Send us what you need or what you have, and we will come back with a rate.
          </span>
        </Link>

        <h2 className="portal-section">Open for bidding</h2>
        {data.open_bids.length ? (
          <div className="portal-list">
            {data.open_bids.map((bid) => (
              <BidCard key={bid.id} bid={bid} code={code} />
            ))}
          </div>
        ) : (
          <p className="portal-empty">Nothing open right now. We will send you the next one.</p>
        )}

        {data.closed_bids.length > 0 && (
          <>
            <h2 className="portal-section">Closed</h2>
            <div className="portal-list">
              {data.closed_bids.map((bid) => (
                <BidCard key={bid.id} bid={bid} code={code} />
              ))}
            </div>
          </>
        )}
      </main>
      <PortalFoot note={PRIVACY} />
    </div>
  );
}

/** One bid, with the form to quote on it. */
export function PortalBidPage() {
  const { code = '', bidId = '' } = useParams();
  const [bid, setBid] = useState<PortalBid | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [price, setPrice] = useState('');
  const [quantity, setQuantity] = useState('');
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [moved, setMoved] = useState(false);
  useDocumentTitle(bid?.title ?? 'Bid');

  // The first load fills the form with whatever they last offered; the live
  // refreshes afterwards must not overwrite what they are typing.
  const load = useCallback(
    (withForm = false) =>
      api
        .get<PortalBid>(`/portal/${code}/bids/${bidId}`)
        .then((row) => {
          setBid(row);
          if (withForm && row.my_quote) {
            setPrice(row.my_quote.price);
            setQuantity(row.my_quote.quantity ?? '');
            setNotes(row.my_quote.notes ?? '');
          }
        })
        .catch((err) =>
          setError(err instanceof ApiError ? err.message : 'This bid is not available.'),
        ),
    [code, bidId],
  );

  useEffect(() => {
    load(true);
  }, [load]);
  useLive(load, bid?.status === 'OPEN');

  // When the price to beat moves, say so rather than changing a number silently.
  const previousBest = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    const best = bid?.best_price ?? null;
    if (previousBest.current !== undefined && previousBest.current !== best) {
      setMoved(true);
      const timer = window.setTimeout(() => setMoved(false), 2500);
      return () => window.clearTimeout(timer);
    }
    previousBest.current = best;
    return undefined;
  }, [bid?.best_price]);

  if (error) return <PortalError message={error} />;
  if (!bid) return <PortalLoading />;

  const unit = unitOf(bid);
  const outcome = outcomeOf(bid);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (busy || !price) return;
    setBusy(true);
    setFormError(null);
    try {
      const updated = await api.post<PortalBid>(`/portal/${code}/bids/${bidId}/quote`, {
        price,
        quantity: quantity || null,
        notes: notes.trim() || null,
      });
      setBid(updated);
      setSent(true);
      window.setTimeout(() => setSent(false), 4000);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : 'Could not send your offer.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="portal">
      <PortalHeader name="" back={`/portal/${code}`} backLabel="Back to your bids" />
      <main className="portal-main">
        <div className="portal-bid-head">
          <span className={`portal-pill ${bid.status === 'OPEN' ? 'live' : (outcome?.tone ?? '')}`}>
            {bid.status === 'OPEN' ? 'Open for bidding' : (outcome?.label ?? 'Closed')}
          </span>
          <h1>{bid.title}</h1>
          <dl className="portal-facts">
            {bid.product_name && (
              <div>
                <dt>Product</dt>
                <dd>{bid.product_name}</dd>
              </div>
            )}
            {bid.pickup_name && (
              <div>
                <dt>From</dt>
                <dd>{bid.pickup_name}</dd>
              </div>
            )}
            {bid.delivery_name && (
              <div>
                <dt>To</dt>
                <dd>{bid.delivery_name}</dd>
              </div>
            )}
            <div>
              <dt>{bid.bid_type === 'TRANSPORT' ? 'Load' : 'Quantity'}</dt>
              <dd>{formatQuantity(bid.quantity, bid.unit)}</dd>
            </div>
            {bid.closes_at && (
              <div>
                <dt>Closes</dt>
                <dd>{formatDateTime(bid.closes_at)}</dd>
              </div>
            )}
          </dl>
          {bid.specifications && <p className="portal-spec">{bid.specifications}</p>}
        </div>

        <div
          className={`portal-board${bid.leading ? ' leading' : ''}${moved ? ' moved' : ''}`}
          aria-live="polite"
        >
          <div className="portal-board-main">
            <span className="portal-board-label">
              {bid.status === 'OPEN'
                ? bid.best_is_highest
                  ? 'Highest offer so far'
                  : 'Lowest offer so far'
                : bid.best_is_highest
                  ? 'Highest offer received'
                  : 'Lowest offer received'}
              {bid.status === 'OPEN' && <span className="portal-live">Live</span>}
            </span>
            <span className="portal-board-value">
              {bid.best_price ? `${unit} ${bid.best_price}` : 'No offers yet'}
            </span>
            <span className="portal-board-hint">
              {moved && <b>Just changed · </b>}
              {bid.bidders === 0
                ? bid.status === 'OPEN'
                  ? 'Be the first to bid.'
                  : 'Nobody bid on this one.'
                : `${bid.bidders} ${bid.bidders === 1 ? 'party' : 'parties'} ${
                    bid.status === 'OPEN' ? 'have bid' : 'bid'
                  }.`}
              {bid.leading && bid.status === 'OPEN' && ' You are leading.'}
            </span>
          </div>
        </div>

        {bid.can_quote ? (
          <form className="portal-form" onSubmit={submit}>
            <h2>{bid.my_quote ? 'Change your offer' : 'Place your offer'}</h2>
            {formError && <div className="portal-error">{formError}</div>}
            {sent && <div className="portal-ok">Your offer has been received.</div>}
            <label>
              <span>Your price ({unit})</span>
              <input
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                required
                value={price}
                onChange={(event) => setPrice(event.currentTarget.value)}
                placeholder="0.00"
              />
            </label>
            <label>
              <span>
                {bid.bid_type === 'TRANSPORT' ? 'Load you can take' : 'Quantity you want'} (
                {bid.unit}, optional)
              </span>
              <input
                type="number"
                inputMode="decimal"
                step="0.001"
                min="0"
                value={quantity}
                onChange={(event) => setQuantity(event.currentTarget.value)}
                placeholder={`Full ${formatQuantity(bid.quantity, bid.unit)}`}
              />
            </label>
            <label>
              <span>Anything we should know (optional)</span>
              <textarea
                rows={3}
                value={notes}
                onChange={(event) => setNotes(event.currentTarget.value)}
                placeholder="Payment terms, delivery, packing…"
              />
            </label>
            <button type="submit" disabled={busy || !price}>
              {busy ? 'Sending…' : bid.my_quote ? 'Update my offer' : 'Send my offer'}
            </button>
            {bid.my_quote && (
              <p className="portal-note">
                Your current offer:{' '}
                <b>
                  {unit} {bid.my_quote.price}
                </b>{' '}
                · sent {formatDateTime(bid.my_quote.submitted_at)}
                {bid.my_quote.revision > 1 && ` · changed ${bid.my_quote.revision - 1}×`}
              </p>
            )}
          </form>
        ) : (
          <div className={`portal-form portal-closed ${outcome?.tone ?? ''}`}>
            <h2>{outcome?.label ?? 'This bid is closed'}</h2>
            {outcome && <p className="portal-said">{outcome.said}</p>}
            {bid.my_quote ? (
              <p className="portal-note">
                Your final offer was{' '}
                <b>
                  {unit} {bid.my_quote.price}
                </b>
                , sent {formatDateTime(bid.my_quote.submitted_at)}.
              </p>
            ) : (
              <p className="portal-note">You did not bid on this one.</p>
            )}
            {bid.closed_at && (
              <p className="portal-note">Bidding closed {formatDateTime(bid.closed_at)}.</p>
            )}
          </div>
        )}
      </main>
      <PortalFoot note={PRIVACY} />
    </div>
  );
}

function BidCard({ bid, code }: { bid: PortalBid; code: string }) {
  const unit = unitOf(bid);
  const outcome = outcomeOf(bid);
  return (
    <Link to={`/portal/${code}/${bid.id}`} className="portal-card">
      <div className="portal-card-top">
        <span className={`portal-pill ${bid.status === 'OPEN' ? 'live' : (outcome?.tone ?? '')}`}>
          {bid.status === 'OPEN' ? 'Open' : (outcome?.label ?? 'Closed')}
        </span>
        {bid.leading && bid.status === 'OPEN' && <span className="portal-tag">You lead</span>}
      </div>
      <div className="portal-card-title">{bid.title}</div>
      <div className="portal-card-meta">
        {formatQuantity(bid.quantity, bid.unit)}
        {bid.best_price
          ? ` · ${bid.status === 'OPEN' ? 'best' : 'closed at'} ${unit} ${bid.best_price}`
          : ' · no offers'}
      </div>
      <div className="portal-card-foot">
        {bid.my_quote ? `Your offer: ${unit} ${bid.my_quote.price}` : 'You have not bid'}
      </div>
    </Link>
  );
}
