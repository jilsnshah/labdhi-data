import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

export const DATE_FORMAT = 'DD MMM YYYY';
export const DATETIME_FORMAT = 'DD MMM YYYY, HH:mm';

export function formatDate(value?: string | null): string {
  return value ? dayjs(value).format(DATE_FORMAT) : '-';
}

/** "Today" / "Tomorrow" / "Fri, 09 Oct" - keeps schedule lists readable. */
export function dayLabel(value?: string | null): string {
  if (!value) return '—';
  const date = dayjs(value);
  if (date.isSame(dayjs(), 'day')) return 'Today';
  if (date.isSame(dayjs().add(1, 'day'), 'day')) return 'Tomorrow';
  if (date.isSame(dayjs().subtract(1, 'day'), 'day')) return 'Yesterday';
  return date.format('ddd, DD MMM');
}

/** Clock time only - used in dense schedule lists. */
export function time(value?: string | null): string {
  return value ? dayjs(value).format('h:mm A') : '—';
}

export function formatDateTime(value?: string | null): string {
  return value ? dayjs(value).format(DATETIME_FORMAT) : '-';
}

export function formatRelative(value?: string | null): string {
  return value ? dayjs(value).fromNow() : '-';
}

export function formatMoney(value?: string | number | null, unit?: string | null): string {
  if (value === null || value === undefined || value === '') return '-';
  const amount = Number(value);
  if (Number.isNaN(amount)) return String(value);
  const formatted = amount.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  return unit ? `₹${formatted}/${unit}` : `₹${formatted}`;
}

/** A quoted rate, always to the paisa: ₹92.50/kg. */
export function formatRate(value?: string | number | null): string {
  if (value === null || value === undefined || value === '') return '—';
  const amount = Number(value);
  if (Number.isNaN(amount)) return String(value);
  return `₹${amount.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}/kg`;
}

/** Quantity × rate in rupees, when the quantity is a weight; otherwise null. */
export function quoteValue(
  quantity?: string | number | null,
  unit?: string | null,
  rate?: string | number | null,
): number | null {
  if (quantity == null || rate == null || rate === '') return null;
  const kilos = unit === 'MT' ? 1000 : unit === 'KG' ? 1 : null;
  if (kilos === null) return null;
  const total = Number(quantity) * kilos * Number(rate);
  return Number.isFinite(total) ? total : null;
}

export function formatQuantity(value?: string | number | null, unit?: string | null): string {
  if (value === null || value === undefined || value === '') return '-';
  const amount = Number(value);
  if (Number.isNaN(amount)) return String(value);
  const formatted = amount.toLocaleString('en-IN', { maximumFractionDigits: 3 });
  return unit ? `${formatted} ${unit}` : formatted;
}

/** Turn SCREAMING_SNAKE enum values into readable labels. */
export function humanize(value?: string | null): string {
  if (!value) return '-';
  return value
    .toLowerCase()
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function isOverdue(value?: string | null): boolean {
  return value ? dayjs(value).isBefore(dayjs()) : false;
}

/** Mantine 8 date inputs emit strings ("YYYY-MM-DD" / "YYYY-MM-DD HH:mm:ss"). */
export type DateInputValue = string | Date | null | undefined;

export function toIso(value: DateInputValue): string | undefined {
  return value ? dayjs(value).toISOString() : undefined;
}

export function toIsoDate(value: DateInputValue): string | undefined {
  return value ? dayjs(value).format('YYYY-MM-DD') : undefined;
}

/** ISO timestamp from the API -> local value for DateTimePicker. */
export function toPickerDateTime(value?: string | null): string | null {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : null;
}

export function pickerNowPlus(amount: number, unit: 'hour' | 'day'): string {
  return dayjs().add(amount, unit).format('YYYY-MM-DD HH:mm:ss');
}

export { dayjs };

/** "3 days ago" / "last week" - how stale a quote is, at a glance. */
export function relativeDay(value?: string | null): string {
  if (!value) return '—';
  const date = dayjs(value);
  const days = dayjs().startOf('day').diff(date.startOf('day'), 'day');
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 7) return `${days} days ago`;
  if (days < 14) return 'last week';
  if (days < 60) return `${Math.round(days / 7)} weeks ago`;
  return `${Math.round(days / 30)} months ago`;
}
