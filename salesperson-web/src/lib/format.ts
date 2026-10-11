import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import calendar from 'dayjs/plugin/calendar';

dayjs.extend(relativeTime);
dayjs.extend(calendar);

export function time(value?: string | null): string {
  return value ? dayjs(value).format('h:mm A') : '--:--';
}

export function dayLabel(value?: string | null): string {
  if (!value) return '';
  const date = dayjs(value);
  if (date.isSame(dayjs(), 'day')) return 'Today';
  if (date.isSame(dayjs().add(1, 'day'), 'day')) return 'Tomorrow';
  return date.format('ddd, DD MMM');
}

export function dateTime(value?: string | null): string {
  return value ? dayjs(value).format('DD MMM YYYY, h:mm A') : '-';
}

export function fromNow(value?: string | null): string {
  return value ? dayjs(value).fromNow() : '';
}

export function isPast(value?: string | null): boolean {
  return value ? dayjs(value).isBefore(dayjs()) : false;
}

/** Morning / Afternoon / Evening buckets for the Today screen. */
export function partOfDay(value?: string | null): 'Morning' | 'Afternoon' | 'Evening' {
  const hour = value ? dayjs(value).hour() : 12;
  if (hour < 12) return 'Morning';
  if (hour < 17) return 'Afternoon';
  return 'Evening';
}

export function humanize(value?: string | null): string {
  if (!value) return '';
  return value
    .toLowerCase()
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function greeting(name: string): string {
  const hour = dayjs().hour();
  const part = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  return `${part}, ${name.split(' ')[0]}`;
}

export { dayjs };
