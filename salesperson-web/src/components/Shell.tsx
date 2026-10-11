import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

export function Screen({
  title,
  subtitle,
  children,
  back,
  action,
  withNav = true,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  back?: boolean;
  action?: ReactNode;
  withNav?: boolean;
}) {
  const navigate = useNavigate();
  return (
    <div className="screen">
      <header className="topbar">
        <div className="topbar-row">
          {back && (
            <button className="back-btn" onClick={() => navigate(-1)} aria-label="Back">
              ‹
            </button>
          )}
          <div className="grow">
            <h1>{title}</h1>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action}
        </div>
      </header>
      <main className={withNav ? 'content' : 'content no-nav'}>{children}</main>
    </div>
  );
}

export function Spinner() {
  return <div className="spinner" aria-label="Loading" />;
}

export function Skeletons({ count = 3 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div className="skeleton" key={index} />
      ))}
    </>
  );
}

export function Banner({
  kind = 'info',
  children,
}: {
  kind?: 'info' | 'warn' | 'error';
  children: ReactNode;
}) {
  return <div className={`banner ${kind}`}>{children}</div>;
}

export function Empty({ icon = '✓', title, hint }: { icon?: string; title: string; hint?: string }) {
  return (
    <div className="empty">
      <div className="big">{icon}</div>
      <div className="strong">{title}</div>
      {hint && (
        <div className="small muted" style={{ marginTop: 4 }}>
          {hint}
        </div>
      )}
    </div>
  );
}

export function Sheet({
  title,
  onClose,
  children,
}: {
  title: string;
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
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  );
}
