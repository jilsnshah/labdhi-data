/**
 * The participant's side of a bid. No sign-in, no CRM, no other bidders.
 *
 * Opened on a phone from a forwarded link, so it is one column, large type and
 * a single number to beat. The page shows what the server allows and nothing
 * more: their own offer, the standing best price, and how many are in.
 */

import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { api } from '@/api/client';
import { ApiError } from '@/api/client';
import type { PortalBid, PortalHome } from '@/api/types';
import { formatDateTime, formatQuantity } from '@/lib/format';

const unitOf = (bid: PortalBid) => (bid.bid_type === 'TRANSPORT' ? '₹' : '₹/kg');

function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = title;
    return () => {
      document.title = 'Trader CRM';
    };
  }, [title]);
}

/** The permanent link: everything this party has been asked to quote on. */
export function PortalHomePage() {
  const { code = '' } = useParams();
  const [data, setData] = useState<PortalHome | null>(null);
  const [error, setError] = useState<string | null>(null);
  useDocumentTitle('Your bids');

  useEffect(() => {
    api
      .get<PortalHome>(`/portal/${code}`)
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'This link is not valid.'));
  }, [code]);

  if (error) return <PortalError message={error} />;
  if (!data) return <PortalLoading />;

  return (
    <div className="portal">
      <PortalHeader name={data.participant_name} />
      <main className="portal-main">
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
      <PortalFoot />
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
  useDocumentTitle(bid?.title ?? 'Bid');

  const load = () =>
    api
      .get<PortalBid>(`/portal/${code}/bids/${bidId}`)
      .then((row) => {
        setBid(row);
        if (row.my_quote) {
          setPrice((current) => current || row.my_quote!.price);
          setQuantity((current) => current || (row.my_quote!.quantity ?? ''));
          setNotes((current) => current || (row.my_quote!.notes ?? ''));
        }
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : 'This bid is not available.'),
      );

  useEffect(() => {
    load();
    // A live auction: keep the price to beat current while the page is open.
    const timer = window.setInterval(() => {
      api
        .get<PortalBid>(`/portal/${code}/bids/${bidId}`)
        .then(setBid)
        .catch(() => undefined);
    }, 20000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, bidId]);

  if (error) return <PortalError message={error} />;
  if (!bid) return <PortalLoading />;

  const unit = unitOf(bid);
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
      <PortalHeader name="" back={`/portal/${code}`} />
      <main className="portal-main">
        <div className="portal-bid-head">
          <span className={`portal-pill ${bid.status === 'OPEN' ? 'live' : ''}`}>
            {bid.status === 'OPEN' ? 'Open for bidding' : 'Closed'}
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

        <div className={`portal-board${bid.leading ? ' leading' : ''}`}>
          <div className="portal-board-main">
            <span className="portal-board-label">
              {bid.best_is_highest ? 'Highest offer so far' : 'Lowest offer so far'}
            </span>
            <span className="portal-board-value">
              {bid.best_price ? `${unit} ${bid.best_price}` : 'No offers yet'}
            </span>
            <span className="portal-board-hint">
              {bid.bidders === 0
                ? 'Be the first to bid.'
                : `${bid.bidders} ${bid.bidders === 1 ? 'party has' : 'parties have'} bid.`}
              {bid.leading && ' You are leading.'}
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
          <div className="portal-form">
            <h2>This bid is closed</h2>
            {bid.my_quote ? (
              <p className="portal-note">
                Your final offer was{' '}
                <b>
                  {unit} {bid.my_quote.price}
                </b>
                , sent {formatDateTime(bid.my_quote.submitted_at)}. We will be in touch.
              </p>
            ) : (
              <p className="portal-note">You did not bid on this one.</p>
            )}
          </div>
        )}
      </main>
      <PortalFoot />
    </div>
  );
}

function BidCard({ bid, code }: { bid: PortalBid; code: string }) {
  const unit = unitOf(bid);
  return (
    <Link to={`/portal/${code}/${bid.id}`} className="portal-card">
      <div className="portal-card-top">
        <span className={`portal-pill ${bid.status === 'OPEN' ? 'live' : ''}`}>
          {bid.status === 'OPEN' ? 'Open' : 'Closed'}
        </span>
        {bid.leading && bid.status === 'OPEN' && <span className="portal-tag">You lead</span>}
      </div>
      <div className="portal-card-title">{bid.title}</div>
      <div className="portal-card-meta">
        {formatQuantity(bid.quantity, bid.unit)}
        {bid.best_price ? ` · best ${unit} ${bid.best_price}` : ' · no offers yet'}
      </div>
      <div className="portal-card-foot">
        {bid.my_quote ? `Your offer: ${unit} ${bid.my_quote.price}` : 'You have not bid'}
      </div>
    </Link>
  );
}

function PortalHeader({ name, back }: { name: string; back?: string }) {
  return (
    <header className="portal-head">
      <div className="portal-head-row">
        {back && (
          <Link to={back} className="portal-back" aria-label="Back to your bids">
            ‹
          </Link>
        )}
        <div>
          <div className="portal-brand">Labdhi</div>
          {name && <div className="portal-who">{name}</div>}
        </div>
      </div>
    </header>
  );
}

function PortalFoot() {
  return (
    <footer className="portal-foot">
      Offers are private. Other bidders never see your name or your price.
    </footer>
  );
}

function PortalLoading() {
  return (
    <div className="portal portal-centre">
      <div className="portal-spinner" />
    </div>
  );
}

function PortalError({ message }: { message: string }) {
  return (
    <div className="portal portal-centre">
      <div className="portal-message">
        <div className="portal-brand">Labdhi</div>
        <p>{message}</p>
        <p className="portal-note">
          If you were sent this link by mistake, or it has expired, please contact us.
        </p>
      </div>
    </div>
  );
}
