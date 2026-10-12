import { Group } from '@mantine/core';
import type { ReactNode } from 'react';

/**
 * Every page opens the same way: a brass eyebrow naming the section, a serif
 * title, one line on what the page is for, and the page's actions on the right.
 */
export function PageHeader({
  title,
  subtitle,
  actions,
  eyebrow,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  /** Small context line above the title, e.g. the section name. */
  eyebrow?: string;
}) {
  return (
    <Group className="page-head" justify="space-between" align="flex-end" wrap="wrap" gap="md">
      <div style={{ minWidth: 0 }}>
        {eyebrow && <div className="page-eyebrow">{eyebrow}</div>}
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
