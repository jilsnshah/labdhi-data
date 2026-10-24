/**
 * Shared layout primitives.
 *
 * Every screen is assembled from the same pieces - page header, panel, KPI
 * tile, label/value field, empty state - so spacing, type and borders are
 * decided once rather than per page.
 */

import { Box, Card, Group, Stack, Text } from '@mantine/core';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { Sparkline } from '@/components/market/Visuals';

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
          py={7}
          mih={44}
          style={{
            borderBottom: '1px solid var(--border)',
            background: 'var(--surface-sunken)',
          }}
        >
          <Stack gap={0}>
            {title && (
              <Text fz="md" fw={600} c="ink.9" lh={1.4}>
                {title}
              </Text>
            )}
            {description && (
              <Text fz="xs" c="ink.5">
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

/**
 * The product's one KPI tile: a quiet label with its icon, the figure, and one
 * line of context. The accent tints the icon and washes the top-right corner,
 * so four tiles side by side read as one instrument panel instead of four
 * coloured boxes. `tone` colours the hint when it reports something that needs
 * attention.
 */
export function KpiTile({
  label,
  value,
  hint,
  icon,
  accent = 'var(--mantine-color-ink-5)',
  tone,
  to,
  spark,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  /** A small contextual glyph - the thing being counted. */
  icon?: ReactNode;
  /** Tints the icon and the corner wash - a side of the market, or a status. */
  accent?: string;
  /** Colours the hint: a count that is overdue, or a figure below cost. */
  tone?: 'negative' | 'attention';
  /** Makes the whole tile a link to the records behind the figure. */
  to?: string;
  /** Daily counts behind the figure, drawn as a small trend line. */
  spark?: number[];
}) {
  const body = (
    <div className="kpi" style={{ ['--kpi-accent' as string]: accent }}>
      <div className="kpi-top">
        <span className="kpi-label">{label}</span>
        {icon && <span className="kpi-icon">{icon}</span>}
      </div>
      <Group justify="space-between" align="flex-end" wrap="nowrap" gap="xs">
        <div className="kpi-value">{value}</div>
        {spark && spark.some(Boolean) && (
          <Box mb={5}>
            <Sparkline values={spark} width={66} height={22} color={accent} />
          </Box>
        )}
      </Group>
      {hint && (
        <div className="kpi-hint" data-tone={tone}>
          {hint}
        </div>
      )}
    </div>
  );

  return to ? (
    <Link to={to} style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
      {body}
    </Link>
  ) : (
    body
  );
}

/** A label/value row - the one way this product shows record details. */
export function Field({
  label,
  value,
  width = 112,
}: {
  label: string;
  value: ReactNode;
  width?: number;
}) {
  return (
    <Group gap="sm" wrap="nowrap" align="flex-start">
      <Text fz="xs" c="ink.5" w={width} style={{ flexShrink: 0, lineHeight: 1.6 }}>
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
    <Stack align="center" gap={6} py={compact ? 'xl' : 44}>
      {icon && (
        <Box
          c="ink.5"
          mb={2}
          style={{
            display: 'grid',
            placeItems: 'center',
            width: 38,
            height: 38,
            borderRadius: 'var(--radius-lg)',
            background: 'var(--surface-sunken)',
            border: '1px solid var(--border)',
          }}
        >
          {icon}
        </Box>
      )}
      <Text fz="md" fw={600} c="ink.8">
        {title}
      </Text>
      {hint && (
        <Text fz="sm" c="ink.5" ta="center" maw={420}>
          {hint}
        </Text>
      )}
      {action && <Box mt="xs">{action}</Box>}
    </Stack>
  );
}
