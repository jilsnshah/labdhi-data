import { Card, Group, Text } from '@mantine/core';
import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

/**
 * A headline figure.
 *
 * Monochrome by default - the label is quiet, the number carries the weight, and
 * colour appears only on a figure that demands action.
 */
export function StatCard({
  label,
  value,
  icon,
  color = 'rust',
  to,
  hint,
  emphasis = false,
}: {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  color?: string;
  to?: string;
  hint?: string;
  emphasis?: boolean;
}) {
  const alert = emphasis && Number(value) > 0;

  const content = (
    <Card padding="lg" h="100%" className={to ? 'clickable' : undefined}>
      <Group justify="space-between" align="center" wrap="nowrap" gap="sm">
        <Text fz="sm" c="ink.6">
          {label}
        </Text>
        {icon && (
          <Text c="ink.3" lh={1} span>
            {icon}
          </Text>
        )}
      </Group>
      <Text
        fz={32}
        fw={600}
        lh={1.15}
        mt={10}
        className="mono-tight"
        c={alert ? `${color}.8` : 'ink.9'}
      >
        {value}
      </Text>
      {hint && (
        <Text fz="sm" c="ink.5" mt={2} lineClamp={1}>
          {hint}
        </Text>
      )}
    </Card>
  );

  return to ? (
    <Link to={to} style={{ textDecoration: 'none', color: 'inherit' }}>
      {content}
    </Link>
  ) : (
    content
  );
}
