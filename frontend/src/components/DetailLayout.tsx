/**
 * The record layout used by every detail screen.
 *
 * A record has two jobs: tell you what it *is*, and let you work on it. So the
 * identity lives in a sticky left rail that never scrolls away, and the work -
 * sourcing, responses, activities, history - sits in a tabbed pane on the right.
 * Nothing important ends up three screens down.
 */

import { Box, Collapse, Group, Stack, Text, UnstyledButton } from '@mantine/core';
import { IconChevronRight } from '@tabler/icons-react';
import { useState } from 'react';
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

/**
 * A labelled block inside the rail, separated by a hairline rather than a card.
 *
 * Foldable, because a rail of four or five of these runs past the bottom of a
 * laptop screen and the sections underneath may as well not exist - on a
 * supplier, Locations and Supplies were both below the fold. Folded, every
 * heading is in view and one click opens the one wanted, which is the whole
 * difference between knowing what a record holds and having to go looking.
 *
 * Sections are open unless told otherwise; the ones a page can usually do
 * without pass ``defaultOpen={false}``.
 */
export function RailSection({
  label,
  children,
  action,
  defaultOpen = true,
}: {
  label?: string;
  children: ReactNode;
  action?: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const foldable = Boolean(label);

  return (
    <Box className="rail-section" data-open={open || undefined}>
      {(label || action) && (
        <Group justify="space-between" align="center" wrap="nowrap" mb={open ? 'sm' : 0}>
          {label && (
            <UnstyledButton
              className="rail-section-head"
              onClick={() => foldable && setOpen((was) => !was)}
              aria-expanded={open}
            >
              <IconChevronRight size={11} className="rail-section-chevron" />
              <Text
                fz={11}
                fw={600}
                tt="uppercase"
                c="ink.5"
                style={{ letterSpacing: '0.08em' }}
              >
                {label}
              </Text>
            </UnstyledButton>
          )}
          {action}
        </Group>
      )}
      <Collapse in={open}>
        <Stack gap="sm">{children}</Stack>
      </Collapse>
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
