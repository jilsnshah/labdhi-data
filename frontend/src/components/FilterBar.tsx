import { ActionIcon, Badge, Button, Collapse, Group, Select, TextInput } from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { IconAdjustmentsHorizontal, IconFilterOff, IconSearch, IconX } from '@tabler/icons-react';
import { Children, Fragment, isValidElement, useState } from 'react';
import type { ReactNode } from 'react';

//: Values a control carries when it is *not* filtering anything.
const NEUTRAL = new Set(['', 'ALL', 'all', 'ANY', 'any']);

/**
 * How many of the filter controls are actually set. Fragments and plain
 * wrappers are walked through, because a page groups its controls as it likes.
 */
function activeCount(children: ReactNode): number {
  return Children.toArray(children).reduce<number>((total, child) => {
    if (!isValidElement(child)) return total;
    const props = child.props as { value?: unknown; checked?: unknown; children?: ReactNode };
    if (child.type === Fragment || typeof child.type === 'string') {
      return total + activeCount(props.children);
    }
    if (props.checked === true) return total + 1;
    if (props.value === undefined || props.value === null) return total;
    //: A switcher resting on its first option is the page's default view.
    const options = (props as { data?: unknown }).data;
    if (Array.isArray(options) && options.length) {
      const first = options[0];
      const firstValue = typeof first === 'string' ? first : (first as { value?: unknown })?.value;
      if (firstValue !== undefined && String(firstValue) === String(props.value)) return total;
    }
    if (Array.isArray(props.value)) {
      //: A cleared date range is [null, null] - present, but filtering nothing.
      return total + (props.value.some((entry) => entry !== null && entry !== '') ? 1 : 0);
    }
    return total + (NEUTRAL.has(String(props.value)) ? 0 : 1);
  }, 0);
}

/**
 * The one filter toolbar. Search on the left, the filters that belong to this
 * screen in a group beside it, the page's own actions on the right - identical
 * on every list screen.
 *
 * Secondary filters (the product dimensions, a date range) go in `extra`: they
 * sit on their own row under a hairline instead of pushing the primary
 * controls around as they appear and disappear.
 *
 * On a phone the filters would push the data off the screen before you saw a
 * single row, so they fold behind a button that says how many are set.
 */
export function FilterBar({
  q,
  onQChange,
  placeholder = 'Search...',
  children,
  extra,
  extraOpen,
  onReset,
  actions,
}: {
  q: string;
  onQChange: (value: string) => void;
  placeholder?: string;
  children?: ReactNode;
  /** Secondary filters, shown on their own row when `extraOpen`. */
  extra?: ReactNode;
  extraOpen?: boolean;
  onReset?: () => void;
  actions?: ReactNode;
}) {
  const compact = useMediaQuery('(max-width: 760px)');
  const [open, setOpen] = useState(false);
  const active = activeCount(children) + activeCount(extra);
  const dirty = active > 0 || Boolean(q);

  const search = (
    <TextInput
      w={compact ? undefined : 260}
      flex={compact ? 1 : undefined}
      placeholder={placeholder}
      leftSection={<IconSearch size={15} />}
      rightSection={
        q ? (
          <ActionIcon size="sm" onClick={() => onQChange('')} aria-label="Clear search">
            <IconX size={13} />
          </ActionIcon>
        ) : null
      }
      value={q}
      onChange={(event) => onQChange(event.currentTarget.value)}
    />
  );

  const clear = onReset && dirty && (
    <Button
      variant="subtle"
      color="ink"
      leftSection={<IconFilterOff size={15} />}
      onClick={onReset}
    >
      Clear
      {active > 0 ? ` (${active})` : ''}
    </Button>
  );

  if (compact) {
    return (
      <div className="toolbar">
        <Group gap="xs" wrap="nowrap" w="100%">
          {search}
          {children && (
            <Button
              variant={open || active ? 'light' : 'default'}
              px="sm"
              onClick={() => setOpen((value) => !value)}
              aria-expanded={open}
              leftSection={<IconAdjustmentsHorizontal size={15} />}
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
        <Collapse in={open} style={{ width: '100%' }}>
          <div className="toolbar-group" style={{ paddingTop: 'var(--space-2)' }}>
            {children}
            {extra}
          </div>
        </Collapse>
        {(actions || clear) && (
          <Group gap="xs" wrap="nowrap" w="100%">
            {clear}
            {actions}
          </Group>
        )}
      </div>
    );
  }

  return (
    <div className="toolbar">
      {search}
      {children && (
        <>
          <span className="toolbar-divider" />
          <div className="toolbar-group">{children}</div>
        </>
      )}
      <Group gap="xs" wrap="nowrap" ml="auto">
        {clear}
        {actions}
      </Group>
      {extra && extraOpen && <div className="toolbar-extra">{extra}</div>}
    </div>
  );
}

export function StatusFilter({
  value,
  onChange,
  w,
}: {
  value: string | undefined;
  onChange: (value: string | undefined) => void;
  w?: number;
}) {
  return (
    <Select
      className={w ? undefined : 'field-sm'}
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
