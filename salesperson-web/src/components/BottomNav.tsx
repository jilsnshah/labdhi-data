import { NavLink } from 'react-router-dom';

const ITEMS = [
  { to: '/today', label: 'Today', icon: '📋' },
  { to: '/visits', label: 'Visits', icon: '📍' },
  { to: '/upcoming', label: 'Upcoming', icon: '🗓' },
  { to: '/profile', label: 'Profile', icon: '👤' },
];

export function BottomNav({ badges }: { badges?: Record<string, number> }) {
  return (
    <nav className="bottom-nav">
      {ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) => (isActive ? 'active' : undefined)}
        >
          <span className="nav-icon">
            {item.icon}
            {badges?.[item.to] ? <span className="nav-badge">{badges[item.to]}</span> : null}
          </span>
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
