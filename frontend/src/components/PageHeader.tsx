import { Group, Stack, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';

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
    <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap" gap="md">
      <Stack gap={2} style={{ minWidth: 0 }}>
        {eyebrow && (
          <Text fz={11} fw={700} tt="uppercase" c="dimmed" style={{ letterSpacing: '0.08em' }}>
            {eyebrow}
          </Text>
        )}
        <Title order={2} fz={22} lh={1.25}>
          {title}
        </Title>
        {subtitle && (
          <Text c="dimmed" fz="sm" style={{ maxWidth: '72ch' }}>
            {subtitle}
          </Text>
        )}
      </Stack>
      {actions && (
        <Group gap="xs" wrap="wrap">
          {actions}
        </Group>
      )}
    </Group>
  );
}
