/**
 * Who built this.
 *
 * Two sizes. The `mark` is a quiet line for the desk's own screens, where the
 * work is the point. The `panel` is for the bidding portal, which is opened by
 * customers, suppliers and transporters who have never seen this software -
 * the one surface where the maker is in front of an audience, so it carries
 * the wordmark, the line and somewhere to go.
 */

import logo from '@/assets/felesai.png';

export const FELES_URL = 'https://felesai.vercel.app/';
export const FELES_CONTACT_URL = 'https://felesai.vercel.app/contact';
export const FELES_NAME = 'Feles AI';

export function FelesCredit({
  tone = 'light',
  size = 'sm',
}: {
  /** `dark` on the shell and the portal header, `light` on the ivory. */
  tone?: 'light' | 'dark';
  size?: 'sm' | 'md';
}) {
  return (
    <a
      className={`feles-credit tone-${tone} size-${size}`}
      href={FELES_URL}
      target="_blank"
      rel="noreferrer noopener"
    >
      <img src={logo} alt="" width={size === 'md' ? 26 : 22} height={size === 'md' ? 26 : 22} />
      <span>
        Built by <b>{FELES_NAME}</b>
      </span>
    </a>
  );
}

/** The full lockup, for the pages people outside the company see. */
export function FelesPanel() {
  return (
    <aside className="feles-panel">
      <img className="feles-panel-logo" src={logo} alt={FELES_NAME} width={48} height={48} />
      <div className="feles-panel-body">
        <div className="feles-panel-name">
          Built by <b>{FELES_NAME}</b>
        </div>
        <p>
          This bidding desk was designed and built by {FELES_NAME}, an AI-native software
          engineering company. We build custom software, digital products and AI systems for
          businesses.
        </p>
        {/* A bidder is here to answer a quote, not to read a URL. If the work
            interests them, give them the one thing worth clicking. */}
        <a
          className="feles-panel-link"
          href={FELES_CONTACT_URL}
          target="_blank"
          rel="noreferrer noopener"
        >
          Contact us
          <span aria-hidden>→</span>
        </a>
      </div>
    </aside>
  );
}
