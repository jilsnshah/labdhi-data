/**
 * Inline stroke icons, drawn on a 24px grid. Kept in-house so the APK needs no
 * icon package and renders identically offline.
 */

import type { ActivityType } from '@/api/types';

const PATHS = {
  today:
    'M8 2v4M16 2v4M3.5 9.5h17M5 4.5h14a1.5 1.5 0 0 1 1.5 1.5v13A1.5 1.5 0 0 1 19 20.5H5A1.5 1.5 0 0 1 3.5 19V6A1.5 1.5 0 0 1 5 4.5ZM8.5 15l2.2 2.2 4.8-4.7',
  route:
    'M6 19a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM18 10a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM8.5 16.5h6a3 3 0 0 0 0-6h-5a3 3 0 0 1 0-6h6',
  calendar:
    'M8 2v4M16 2v4M3.5 9.5h17M5 4.5h14a1.5 1.5 0 0 1 1.5 1.5v13A1.5 1.5 0 0 1 19 20.5H5A1.5 1.5 0 0 1 3.5 19V6A1.5 1.5 0 0 1 5 4.5ZM8 13.5h.01M12 13.5h.01M16 13.5h.01M8 17h.01M12 17h.01',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4.5 20.5c.8-3.6 3.8-6 7.5-6s6.7 2.4 7.5 6',
  plus: 'M12 5v14M5 12h14',
  phone:
    'M5 3.5h3.2l1.6 4.2-2.1 1.3a11 11 0 0 0 5.3 5.3l1.3-2.1 4.2 1.6V17a2 2 0 0 1-2 2A15.5 15.5 0 0 1 3 5.5a2 2 0 0 1 2-2Z',
  chat: 'M20.5 11.5a8.5 8.5 0 0 1-12.6 7.4L3.5 20l1.2-4.2A8.5 8.5 0 1 1 20.5 11.5ZM8.5 11.5h.01M12 11.5h.01M15.5 11.5h.01',
  sms: 'M4 5.5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H9l-4.5 3v-3H4a1 1 0 0 1-1-1v-10a1 1 0 0 1 1-1ZM7 9.5h10M7 13h6',
  mail: 'M3.5 6.5h17v11h-17zM3.5 7l8.5 6 8.5-6',
  pin: 'M12 21s-7-6.2-7-11.5a7 7 0 1 1 14 0C19 14.8 12 21 12 21ZM12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z',
  people:
    'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM2.5 20c.6-3.3 3.2-5.5 6.5-5.5s5.9 2.2 6.5 5.5M16 4.3a3.5 3.5 0 0 1 0 6.4M18.5 14.8c1.7.8 2.8 2.6 3 5.2',
  navigate: 'M20.5 3.5 3.5 10.6l7 2.9 2.9 7z',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 7.5V12l3 2',
  back: 'M15 5l-7 7 7 7',
  chevron: 'M9 5l7 7-7 7',
  refresh: 'M20 11a8 8 0 0 0-14.6-4.5M4 4v3.5h3.5M4 13a8 8 0 0 0 14.6 4.5M20 20v-3.5h-3.5',
  search: 'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14ZM20 20l-4-4',
  offline:
    'M3 3l18 18M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 5-2.6M19 13a10 10 0 0 0-2.2-1.6M2 9.5A15 15 0 0 1 7 6.6M22 9.5A15 15 0 0 0 11 5.6M12 20h.01',
  history: 'M3.5 12a8.5 8.5 0 1 0 2.5-6M3.5 4v4h4M12 7.5V12l3 2',
  logout:
    'M14.5 4.5h4a1.5 1.5 0 0 1 1.5 1.5v12a1.5 1.5 0 0 1-1.5 1.5h-4M10 16.5l-4.5-4.5L10 7.5M5.5 12H15',
  lock: 'M6.5 10.5h11a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1ZM8.5 10.5V7.5a3.5 3.5 0 0 1 7 0v3',
  userPlus:
    'M10 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM3 20.5c.8-3.6 3.5-6 7-6 1.4 0 2.6.4 3.6 1M18.5 14v6M15.5 17h6',
  crosshair:
    'M12 19.5a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM12 2v4M12 18v4M2 12h4M18 12h4M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z',
  close: 'M6 6l12 12M18 6 6 18',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  note: 'M6 3.5h8.5L19 8v12a.5.5 0 0 1-.5.5h-12A.5.5 0 0 1 6 20V4a.5.5 0 0 1 .5-.5ZM14 3.5V8h5M9 12.5h6M9 16h4',
  spark:
    'M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6zM19 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z',
  flag: 'M5 21V4M5 4.5h11.5l-2 4 2 4H5',
  play: 'M7 4.5v15l12-7.5z',
  bolt: 'M13 2.5 4.5 13.5H12l-1 8 8.5-11H12z',
  building:
    'M4 20.5h16M6 20.5V5a1.5 1.5 0 0 1 1.5-1.5h9A1.5 1.5 0 0 1 18 5v15.5M9.5 7.5h1M13.5 7.5h1M9.5 11h1M13.5 11h1M9.5 14.5h1M13.5 14.5h1M10.5 20.5V18h3v2.5',
  cloud:
    'M7 18.5a4.5 4.5 0 0 1-.6-9 6 6 0 0 1 11.4 1.6A3.8 3.8 0 0 1 17.5 18.5ZM9.5 14l2 2 3.5-3.5',
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({
  name,
  size = 20,
  stroke = 1.8,
  className,
}: {
  name: IconName;
  size?: number;
  stroke?: number;
  className?: string;
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d={PATHS[name]} />
    </svg>
  );
}

export const TYPE_ICON: Record<ActivityType, IconName> = {
  VISIT: 'pin',
  CALL: 'phone',
  WHATSAPP: 'chat',
  SMS: 'sms',
  EMAIL: 'mail',
  MEETING: 'people',
};

/** Colour family per activity type; matches the `.tone-*` classes in styles.css. */
export const TYPE_TONE: Record<ActivityType, string> = {
  VISIT: 'brass',
  CALL: 'indigo',
  WHATSAPP: 'teal',
  SMS: 'slate',
  EMAIL: 'slate',
  MEETING: 'indigo',
};

export function TypeIcon({ type, size = 40 }: { type: ActivityType; size?: number }) {
  return (
    <span
      className={`type-tile tone-${TYPE_TONE[type]}`}
      style={{ width: size, height: size, borderRadius: size * 0.32 }}
    >
      <Icon name={TYPE_ICON[type]} size={Math.round(size * 0.48)} />
    </span>
  );
}
