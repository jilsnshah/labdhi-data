import { ActionIcon, Button, Card, Group, Select, TextInput } from '@mantine/core';
import { IconFilterOff, IconSearch, IconX } from '@tabler/icons-react';
import type { ReactNode } from 'react';

/**
 * The one filter toolbar. Search on the left, filters in a wrapping row, page
 * actions on the right - identical on every list screen.
 */
export function FilterBar({
  q,
  onQChange,
  placeholder = 'Search...',
  children,
  onReset,
  actions,
}: {
  q: string;
  onQChange: (value: string) => void;
  placeholder?: string;
  children?: ReactNode;
  onReset?: () => void;
  actions?: ReactNode;
}) {
  return (
    <Card padding="sm" mb="md" radius="md" style={{ background: 'var(--surface)' }}>
      <Group gap="sm" justify="space-between" align="center" wrap="wrap">
        <Group gap="xs" align="center" wrap="wrap" style={{ flex: 1, minWidth: 0 }}>
          <TextInput
            w={248}
            placeholder={placeholder}
            leftSection={<IconSearch size={15} />}
            rightSection={
              q ? (
                <ActionIcon size="sm" onClick={() => onQChange('')} aria-label="Clear search">
                  <IconX size={14} />
                </ActionIcon>
              ) : null
            }
            value={q}
            onChange={(event) => onQChange(event.currentTarget.value)}
          />
          {children}
        </Group>
        <Group gap="xs" wrap="nowrap">
          {onReset && (
            <Button
              variant="subtle"
              color="ink"
              size="sm"
              leftSection={<IconFilterOff size={15} />}
              onClick={onReset}
            >
              Clear
            </Button>
          )}
          {actions}
        </Group>
      </Group>
    </Card>
  );
}

export function StatusFilter({
  value,
  onChange,
  w = 132,
}: {
  value: string | undefined;
  onChange: (value: string | undefined) => void;
  w?: number;
}) {
  return (
    <Select
      w={w}
      placeholder="Any status"
      clearable
      data={[
        { value: 'ACTIVE', label: 'Active' },
        { value: 'INACTIVE', label: 'Inactive' },
      ]}
      value={value ?? null}
      onChange={(next) => onChange(next ?? undefined)}
    />
  );
}
