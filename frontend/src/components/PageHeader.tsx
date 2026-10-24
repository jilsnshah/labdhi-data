import { Group } from '@mantine/core';
import type { ReactNode } from 'react';

/**
 * Every page opens the same way: its name, one line on what it is for, and its
 * actions on the right. The section this page belongs to is already in the
 * global header's trail, so it is not repeated here.
 */
export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <Group className="page-head" justify="space-between" align="flex-end" wrap="wrap" gap="md">
      <div style={{ minWidth: 0 }}>
        <h1 className="page-title">{title}</h1>
        {subtitle && <div className="page-subtitle">{subtitle}</div>}
      </div>
      {actions && (
        <Group gap="xs" wrap="wrap">
          {actions}
        </Group>
      )}
    </Group>
  );
}
