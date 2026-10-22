/**
 * The frame every portal page shares: header, footer, loading and error.
 *
 * The portal is the one part of this app a customer ever sees, and they see it
 * on a phone, from a link somebody sent them. So it carries the house name,
 * their own name, and the Feles mark - and nothing else, because none of the
 * desk's furniture belongs on a page handed to an outsider.
 */

import { Link } from 'react-router-dom';
import { useEffect, useRef } from 'react';

import felesLogo from '@/assets/felesai.png';
import { FELES_NAME, FELES_URL, FelesPanel } from '@/components/FelesCredit';

/**
 * Keep a page current without the person touching it.
 *
 * Somebody leaves this open on a phone while they decide, so it has to move on
 * its own. It pauses whenever the tab is hidden, picking up again - with an
 * immediate refresh - the moment they come back to it.
 */
export function useLive(refresh: () => void, active: boolean, intervalMs = 8000) {
  const latest = useRef(refresh);
  latest.current = refresh;

  useEffect(() => {
    if (!active) return undefined;
    const run = () => {
      if (document.visibilityState === 'visible') latest.current();
    };
    const timer = window.setInterval(run, intervalMs);
    document.addEventListener('visibilitychange', run);
    window.addEventListener('focus', run);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', run);
      window.removeEventListener('focus', run);
    };
  }, [active, intervalMs]);
}

export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = title;
    return () => {
      document.title = 'Trader CRM';
    };
  }, [title]);
}

export function PortalHeader({
  name,
  back,
  backLabel = 'Back',
}: {
  name: string;
  back?: string;
  backLabel?: string;
}) {
  return (
    <header className="portal-head">
      <div className="portal-head-row">
        {back && (
          <Link to={back} className="portal-back" aria-label={backLabel}>
            ‹
          </Link>
        )}
        <div className="grow">
          <div className="portal-brand">Labdhi</div>
          {name && <div className="portal-who">{name}</div>}
        </div>
        <a
          className="portal-powered"
          href={FELES_URL}
          target="_blank"
          rel="noreferrer noopener"
          title={`Built by ${FELES_NAME}`}
        >
          <img src={felesLogo} alt="" width={24} height={24} />
          <span>
            Built by<b>{FELES_NAME}</b>
          </span>
        </a>
      </div>
    </header>
  );
}

/** The note differs by page: a bid promises privacy, an enquiry promises a reply. */
export function PortalFoot({ note }: { note?: string }) {
  return (
    <footer className="portal-foot">
      {note && <div>{note}</div>}
      <FelesPanel />
    </footer>
  );
}

export function PortalLoading() {
  return (
    <div className="portal portal-centre">
      <div className="portal-spinner" />
    </div>
  );
}

export function PortalError({ message }: { message: string }) {
  return (
    <div className="portal portal-centre">
      <div className="portal-message">
        <div className="portal-brand">Labdhi</div>
        <p>{message}</p>
        <p className="portal-note">
          If you were sent this link by mistake, or it has expired, please contact us.
        </p>
        <FelesPanel />
      </div>
    </div>
  );
}
