import { ActionIcon, Badge, Button, Card, Collapse, Group, Select, TextInput } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { IconAdjustmentsHorizontal, IconFilterOff, IconSearch, IconX } from '@tabler/icons-react';
import { Children, isValidElement, useState } from 'react';
import type { ReactNode } from 'react';

//: Values a control carries when it is *not* filtering anything.
const NEUTRAL = new Set(['', 'ALL', 'all', 'ANY', 'any']);

/** How many of the filter controls are actually set, for the phone badge. */
function activeCount(children: ReactNode): number {
  return Children.toArray(children).filter((child) => {
    if (!isValidElement(child)) return false;
    const props = child.props as { value?: unknown; checked?: unknown };
    if (props.checked === true) return true;
    if (props.value === undefined || props.value === null) return false;
    return !NEUTRAL.has(String(props.value));
  }).length;
}

/**
 * The one filter toolbar. Search on the left, filters in a wrapping row, page
 * actions on the right - identical on every list screen.
 *
 * On a phone the filters would push the data off the screen before you saw a
 * single row, so they fold behind a button that says how many are set.
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
  const compact = useMediaQuery('(max-width: 760px)');
  const [open, setOpen] = useState(false);
  const active = compact ? activeCount(children) : 0;

  const search = (
    <TextInput
      w={compact ? undefined : 248}
      flex={compact ? 1 : undefined}
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
  );

  if (compact) {
    return (
      <Card padding="sm" mb="md" radius="md" style={{ background: 'var(--surface)' }}>
        <Group gap="xs" wrap="nowrap">
          {search}
          {children && (
            <Button
              variant={open || active ? 'light' : 'default'}
              px="sm"
              onClick={() => setOpen((value) => !value)}
              aria-expanded={open}
              leftSection={<IconAdjustmentsHorizontal size={16} />}
            >
              {active > 0 ? (
                <Badge size="sm" circle variant="filled">
                  {active}
                </Badge>
              ) : (
                'Filters'
              )}
            </Button>
          )}
        </Group>
        <Collapse in={open}>
          <Group gap="xs" align="center" wrap="wrap" mt="sm">
            {children}
          </Group>
        </Collapse>
        {(actions || (onReset && (active > 0 || q))) && (
          <Group gap="xs" mt="sm" wrap="nowrap">
            {onReset && (active > 0 || q) && (
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
        )}
      </Card>
    );
  }

  return (
    <Card padding="sm" mb="md" radius="md" style={{ background: 'var(--surface)' }}>
      <Group gap="sm" justify="space-between" align="center" wrap="wrap">
        <Group gap="xs" align="center" wrap="wrap" style={{ flex: 1, minWidth: 0 }}>
          {search}
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
