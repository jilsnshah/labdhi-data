/**
 * Who built this.
 *
 * Present on every surface - the desk, the sign-in page, the bidding portal a
 * customer opens - but sized to sit under the work rather than next to it.
 */

import logo from '@/assets/felesai.png';

export const FELES_URL = 'https://felesai.vercel.app/';

export function FelesCredit({
  tone = 'light',
  size = 'sm',
}: {
  /** `dark` for the navy shell and the portal header, `light` on the ivory. */
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
      <img src={logo} alt="" width={size === 'md' ? 20 : 16} height={size === 'md' ? 20 : 16} />
      <span>
        Built by <b>FelesAI</b>
        <em>IIT Gandhinagar</em>
      </span>
    </a>
  );
}
