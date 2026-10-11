/**
 * The record layout used by every detail screen.
 *
 * A record has two jobs: tell you what it *is*, and let you work on it. So the
 * identity lives in a sticky left rail that never scrolls away, and the work -
 * sourcing, responses, activities, history - sits in a tabbed pane on the right.
 * Nothing important ends up three screens down.
 */

import { Box, Group, Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';

export function DetailLayout({
  rail,
  children,
}: {
  rail: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="detail-grid">
      <aside className="detail-rail">{rail}</aside>
      <div className="detail-main">{children}</div>
    </div>
  );
}

/** A labelled block inside the rail, separated by a hairline rather than a card. */
export function RailSection({
  label,
  children,
  action,
}: {
  label?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Box className="rail-section">
      {(label || action) && (
        <Group justify="space-between" align="center" mb="sm" wrap="nowrap">
          {label && (
            <Text
              fz={11}
              fw={600}
              tt="uppercase"
              c="ink.5"
              style={{ letterSpacing: '0.08em' }}
            >
              {label}
            </Text>
          )}
          {action}
        </Group>
      )}
      <Stack gap="sm">{children}</Stack>
    </Box>
  );
}

/** The one headline figure a record is judged by (best quote, order value). */
export function RailHighlight({
  label,
  value,
  caption,
  tone,
}: {
  label: string;
  value: ReactNode;
  caption?: string;
  tone?: 'default' | 'muted';
}) {
  return (
    <Box className="rail-highlight" data-tone={tone ?? 'default'}>
      <Text fz="sm" c="ink.5">
        {label}
      </Text>
      <Text fz={24} fw={600} lh={1.2} mt={2} c="ink.9" className="mono-tight">
        {value}
      </Text>
      {caption && (
        <Text fz="sm" c="ink.5" mt={2}>
          {caption}
        </Text>
      )}
    </Box>
  );
}
