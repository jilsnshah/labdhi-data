import { NavLink, useNavigate } from 'react-router-dom';

import { Icon, type IconName } from './Icon';

const LEFT: { to: string; label: string; icon: IconName }[] = [
  { to: '/today', label: 'Today', icon: 'today' },
  { to: '/visits', label: 'Route', icon: 'route' },
];
const RIGHT: { to: string; label: string; icon: IconName }[] = [
  { to: '/upcoming', label: 'Plan', icon: 'calendar' },
  { to: '/profile', label: 'Me', icon: 'user' },
];

export function BottomNav({ badges }: { badges?: Record<string, number> }) {
  const navigate = useNavigate();
  const item = ({ to, label, icon }: (typeof LEFT)[number]) => (
    <NavLink key={to} to={to} className={({ isActive }) => (isActive ? 'active' : undefined)}>
      <span className="nav-icon">
        <Icon name={icon} size={23} />
        {badges?.[to] ? <span className="nav-badge">{badges[to]}</span> : null}
      </span>
      <span className="nav-label">{label}</span>
    </NavLink>
  );
  return (
    <nav className="bottom-nav">
      {LEFT.map(item)}
      <div className="nav-fab-slot">
        <button className="nav-fab" onClick={() => navigate('/log')} aria-label="Log an activity">
          <Icon name="plus" size={26} stroke={2.4} />
        </button>
        <span className="nav-label">Log</span>
      </div>
      {RIGHT.map(item)}
    </nav>
  );
}
