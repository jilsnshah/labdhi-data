import { STATUS_TONES, type StatusTone } from '@/theme';
import { humanize } from '@/lib/format';

const SIZES = {
  xs: { font: 11, height: 19, dot: 5 },
  sm: { font: 12, height: 22, dot: 6 },
  md: { font: 13, height: 25, dot: 7 },
} as const;

/**
 * The single status indicator for the whole product.
 *
 * A status is a dot, a word and a soft tint of its own tone: small enough for
 * a dense table, defined enough to read at a glance, and quiet enough that a
 * column of neutral ones does not compete with the amber and red ones that
 * need a decision. `quiet` drops the tint where a badge would be too much - a
 * rail line, a card's meta row.
 */
export function StatusBadge({
  value,
  size = 'sm',
  tone,
  quiet = false,
  uppercase = false,
}: {
  value?: string | null;
  size?: keyof typeof SIZES;
  /** Override the tone derived from the value. */
  tone?: StatusTone;
  /** Dot and word only, with no tinted surface. */
  quiet?: boolean;
  uppercase?: boolean;
  /** Accepted for compatibility with older call sites; styling is centralised. */
  variant?: string;
  withDot?: boolean;
}) {
  if (!value) return null;
  const resolved: StatusTone = tone ?? STATUS_TONES[value] ?? 'neutral';
  const dimensions = SIZES[size] ?? SIZES.sm;

  return (
    <span
      className={quiet ? 'status-badge status-quiet' : 'status-badge'}
      data-tone={resolved}
      style={{
        ['--dot' as string]: `${dimensions.dot}px`,
        fontSize: dimensions.font,
        height: quiet ? undefined : dimensions.height,
        textTransform: uppercase ? 'uppercase' : undefined,
        letterSpacing: uppercase ? '0.05em' : undefined,
      }}
    >
      {humanize(value)}
    </span>
  );
}
