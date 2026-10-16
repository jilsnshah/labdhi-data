/** Who built this. Quiet, but on every screen a person lands on. */

import logo from '@/assets/felesai.png';

export const FELES_URL = 'https://felesai.vercel.app/';

export function FelesCredit({ tone = 'dark' }: { tone?: 'dark' | 'light' }) {
  return (
    <a className={`feles-credit ${tone}`} href={FELES_URL} target="_blank" rel="noreferrer">
      <img src={logo} alt="" width={16} height={16} />
      <span>
        Built by <b>FelesAI</b>
        <em>IIT Gandhinagar</em>
      </span>
    </a>
  );
}
