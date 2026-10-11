import { Box, Group, Text } from '@mantine/core';

import { STATUS_TONES, TONE_DOT, TONE_TEXT, type StatusTone } from '@/theme';
import { humanize } from '@/lib/format';

const SIZES = {
  xs: { font: 11, dot: 5, gap: 5 },
  sm: { font: 12, dot: 6, gap: 6 },
  md: { font: 13, dot: 7, gap: 7 },
} as const;

/**
 * The single status indicator for the whole product.
 *
 * A status is a dot plus a word, not a coloured pill: a column of them reads as
 * one calm list, and the eye is drawn only to the amber and rust tones that
 * actually need a decision.
 */
export function StatusBadge({
  value,
  size = 'sm',
  tone,
  uppercase = false,
}: {
  value?: string | null;
  size?: keyof typeof SIZES;
  /** Override the tone derived from the value. */
  tone?: StatusTone;
  uppercase?: boolean;
  /** Accepted for compatibility with older call sites; styling is centralised. */
  variant?: string;
  withDot?: boolean;
}) {
  if (!value) return null;
  const resolved: StatusTone = tone ?? STATUS_TONES[value] ?? 'neutral';
  const dimensions = SIZES[size] ?? SIZES.sm;

  return (
    <Group gap={dimensions.gap} wrap="nowrap" style={{ display: 'inline-flex' }}>
      <Box
        style={{
          width: dimensions.dot,
          height: dimensions.dot,
          borderRadius: 999,
          background: TONE_DOT[resolved],
          flexShrink: 0,
        }}
      />
      <Text
        fz={dimensions.font}
        fw={550}
        c={TONE_TEXT[resolved]}
        tt={uppercase ? 'uppercase' : undefined}
        style={{ whiteSpace: 'nowrap', letterSpacing: uppercase ? '0.04em' : undefined }}
      >
        {humanize(value)}
      </Text>
    </Group>
  );
}
