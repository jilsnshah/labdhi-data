import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { initials } from '@/lib/format';
import { subscribeToast, type Toast } from '@/lib/toast';
import { Icon, type IconName } from './Icon';

/**
 * A screen: a deep navy masthead with a serif title, then the ivory work
 * surface. `hero` renders inside the masthead (the Today ring, the week chart).
 */
export function Screen({
  title,
  eyebrow,
  subtitle,
  children,
  back,
  action,
  hero,
  withNav = true,
  footer,
}: {
  title: ReactNode;
  eyebrow?: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  back?: boolean;
  action?: ReactNode;
  hero?: ReactNode;
  withNav?: boolean;
  footer?: ReactNode;
}) {
  const navigate = useNavigate();
  return (
    <div className="screen">
      <header className={`masthead${hero ? ' tall' : ''}`}>
        <div className="masthead-row">
          {back && (
            <button className="icon-btn" onClick={() => navigate(-1)} aria-label="Back">
              <Icon name="back" size={20} stroke={2} />
            </button>
          )}
          <div className="grow masthead-titles">
            {eyebrow && <div className="eyebrow">{eyebrow}</div>}
            <h1>{title}</h1>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action}
        </div>
        {hero}
      </header>
      <main className={`content${withNav ? '' : ' no-nav'}${footer ? ' with-footer' : ''}`}>
        {children}
      </main>
      {footer && <div className="footer-bar">{footer}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="spinner-wrap">
      <div className="spinner" aria-label="Loading" />
      {label && <div className="tiny muted">{label}</div>}
    </div>
  );
}

export function Skeletons({ count = 3 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div className="skeleton" key={index} style={{ animationDelay: `${index * 120}ms` }} />
      ))}
    </>
  );
}

const BANNER_ICON: Record<string, IconName> = { info: 'spark', warn: 'cloud', error: 'offline' };

export function Banner({
  kind = 'info',
  children,
}: {
  kind?: 'info' | 'warn' | 'error';
  children: ReactNode;
}) {
  return (
    <div className={`banner ${kind}`}>
      <Icon name={BANNER_ICON[kind]} size={18} />
      <div className="grow">{children}</div>
    </div>
  );
}

export function Empty({
  icon = 'check',
  title,
  hint,
  children,
}: {
  icon?: IconName;
  title: string;
  hint?: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-mark">
        <Icon name={icon} size={26} />
      </div>
      <div className="empty-title">{title}</div>
      {hint && <div className="small muted">{hint}</div>}
      {children}
    </div>
  );
}

export function Sheet({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div
      className="sheet-backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="sheet" role="dialog" aria-label={title}>
        <div className="sheet-handle" />
        <div className="sheet-head">
          <div className="grow">
            <h2>{title}</h2>
            {subtitle && <div className="small muted">{subtitle}</div>}
          </div>
          <button className="icon-btn light" onClick={onClose} aria-label="Close">
            <Icon name="close" size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Avatar({ name, size = 40, tone }: { name: string; size?: number; tone?: string }) {
  return (
    <span
      className={`avatar${tone ? ` tone-${tone}` : ''}`}
      style={{ width: size, height: size, fontSize: size * 0.36 }}
    >
      {initials(name)}
    </span>
  );
}

export function SectionTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="section-title">
      <span>{children}</span>
      {aside && <span className="section-aside">{aside}</span>}
    </div>
  );
}

export function Toaster() {
  const [current, setCurrent] = useState<Toast | null>(null);
  useEffect(() => subscribeToast(setCurrent), []);
  if (!current) return null;
  return (
    <div className={`toast ${current.tone}`} key={current.id} role="status">
      <Icon
        name={current.tone === 'ok' ? 'check' : current.tone === 'warn' ? 'cloud' : 'offline'}
        size={18}
        stroke={2.2}
      />
      <span>{current.message}</span>
    </div>
  );
}
