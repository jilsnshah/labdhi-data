/** Who built this. Quiet on the desk's own screens, but on every one of them. */

import logo from '@/assets/felesai.png';

export const FELES_URL = 'https://felesai.vercel.app/';
export const FELES_NAME = 'Feles AI';

export function FelesCredit({ tone = 'dark' }: { tone?: 'dark' | 'light' }) {
  return (
    <a className={`feles-credit ${tone}`} href={FELES_URL} target="_blank" rel="noreferrer">
      <img src={logo} alt="" width={24} height={24} />
      <span>
        Built by <b>{FELES_NAME}</b>
      </span>
    </a>
  );
}
