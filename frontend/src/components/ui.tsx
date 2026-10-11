/**
 * Shared layout primitives.
 *
 * Every screen is assembled from the same four pieces - page header, panel,
 * label/value field, empty state - so spacing, type and borders are decided once
 * rather than per page.
 */

import { Box, Card, Group, Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';

export function SectionCard({
  title,
  description,
  actions,
  children,
  padding = 'lg',
  dense = false,
  h,
}: {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  padding?: string;
  /** Pull the body flush to the panel edge, e.g. for a table. */
  dense?: boolean;
  h?: string | number;
}) {
  return (
    <Card padding={0} h={h} style={{ overflow: 'hidden' }}>
      {(title || actions) && (
        <Group
          justify="space-between"
          align="center"
          wrap="nowrap"
          px={padding}
          py="md"
          style={{ borderBottom: '1px solid var(--hairline)' }}
        >
          <Stack gap={1}>
            {title && (
              <Text fz="md" fw={600} c="ink.9" lh={1.3}>
                {title}
              </Text>
            )}
            {description && (
              <Text fz="sm" c="ink.5">
                {description}
              </Text>
            )}
          </Stack>
          {actions && (
            <Group gap="xs" wrap="nowrap">
              {actions}
            </Group>
          )}
        </Group>
      )}
      <Box px={dense ? 0 : padding} py={dense ? 0 : padding}>
        {children}
      </Box>
    </Card>
  );
}

/** A label/value row - the one way this product shows record details. */
export function Field({
  label,
  value,
  width = 128,
}: {
  label: string;
  value: ReactNode;
  width?: number;
}) {
  return (
    <Group gap="md" wrap="nowrap" align="flex-start">
      <Text fz="sm" c="ink.5" w={width} style={{ flexShrink: 0, lineHeight: 1.6 }}>
        {label}
      </Text>
      {typeof value === 'string' || typeof value === 'number' ? (
        <Text fz="sm" c="ink.9" className="wrap">
          {value || '—'}
        </Text>
      ) : (
        <Box style={{ minWidth: 0 }}>{value}</Box>
      )}
    </Group>
  );
}

export function EmptyState({
  icon,
  title,
  hint,
  action,
  compact = false,
}: {
  icon?: ReactNode;
  title: string;
  hint?: string;
  action?: ReactNode;
  compact?: boolean;
}) {
  return (
    <Stack align="center" gap={6} py={compact ? 'xl' : 48}>
      {icon && <Box c="ink.4">{icon}</Box>}
      <Text fz="sm" fw={550} c="ink.8">
        {title}
      </Text>
      {hint && (
        <Text fz="sm" c="ink.5" ta="center" maw={420}>
          {hint}
        </Text>
      )}
      {action && <Box mt="sm">{action}</Box>}
    </Stack>
  );
}

/** Compact number + label for the detail-page summary strips. */
export function Metric({
  label,
  value,
  color,
  hint,
}: {
  label: string;
  value: ReactNode;
  color?: string;
  hint?: string;
}) {
  return (
    <Stack gap={2}>
      <Text fz="sm" c="ink.5">
        {label}
      </Text>
      <Text fz={24} fw={600} lh={1.1} c={color ?? 'ink.9'} className="mono-tight">
        {value}
      </Text>
      {hint && (
        <Text fz="xs" c="ink.5">
          {hint}
        </Text>
      )}
    </Stack>
  );
}
