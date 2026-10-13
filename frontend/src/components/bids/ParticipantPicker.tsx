/**
 * Choosing who gets asked to quote.
 *
 * A bid is only as good as the room it goes to, and the room is picked out of a
 * thousand parties. This is the customer list's own filters - search, city,
 * area, product, stage - over a checkbox list, with "select all that match" so
 * a whole city can be invited in one action.
 */

import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Checkbox,
  Group,
  Loader,
  ScrollArea,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconSearch, IconUsersGroup, IconX } from '@tabler/icons-react';
import { useMemo, useState } from 'react';

import { useLocationAreas, useParties } from '@/api/hooks';
import type { PartyListItem, PartyType } from '@/api/types';
import { EntitySelect } from '@/components/EntitySelect';
import { PartyAvatar } from '@/components/market/Visuals';

const PAGE_SIZE = 50;

export function ParticipantPicker({
  partyType,
  selected,
  onChange,
  /** Parties already on the bid: shown ticked and locked. */
  locked = [],
}: {
  partyType: PartyType;
  selected: number[];
  onChange: (ids: number[]) => void;
  locked?: number[];
}) {
  const [q, setQ] = useState('');
  const [debouncedQ] = useDebouncedValue(q, 250);
  const [city, setCity] = useState('');
  const [debouncedCity] = useDebouncedValue(city, 250);
  const [area, setArea] = useState<string | null>(null);
  const [productId, setProductId] = useState<number | null>(null);
  const [stage, setStage] = useState<string | null>(null);

  const { data, isFetching } = useParties({
    party_type: partyType,
    q: debouncedQ || undefined,
    city: debouncedCity || undefined,
    area: area ?? undefined,
    product_id: productId ?? undefined,
    stage: stage ?? undefined,
    status: 'ACTIVE',
    page_size: PAGE_SIZE,
    sort_by: 'name',
    sort_dir: 'asc',
  });
  const { data: areas } = useLocationAreas();

  const rows = useMemo(() => data?.items ?? [], [data]);
  const lockedSet = useMemo(() => new Set(locked), [locked]);
  const selectable = rows.filter((row) => !lockedSet.has(row.id));
  const allShown = selectable.length > 0 && selectable.every((row) => selected.includes(row.id));

  const toggle = (id: number) =>
    onChange(selected.includes(id) ? selected.filter((value) => value !== id) : [...selected, id]);

  const toggleAllShown = () => {
    const shown = selectable.map((row) => row.id);
    onChange(
      allShown
        ? selected.filter((id) => !shown.includes(id))
        : Array.from(new Set([...selected, ...shown])),
    );
  };

  const clearFilters = () => {
    setQ('');
    setCity('');
    setArea(null);
    setProductId(null);
    setStage(null);
  };
  const filtered = Boolean(q || city || area || productId || stage);

  return (
    <Stack gap="sm">
      <Group gap="xs" align="flex-end" wrap="wrap">
        <TextInput
          flex={1}
          miw={180}
          label="Search"
          placeholder="Name, phone, GST"
          leftSection={<IconSearch size={15} />}
          value={q}
          onChange={(event) => setQ(event.currentTarget.value)}
        />
        <TextInput
          w={130}
          label="City"
          placeholder="Any city"
          value={city}
          onChange={(event) => setCity(event.currentTarget.value)}
        />
        <Select
          w={140}
          label="Area"
          placeholder="Any area"
          searchable
          clearable
          data={areas ?? []}
          value={area}
          onChange={setArea}
        />
        <Box w={170}>
          <Text fz="sm" fw={500} mb={4}>
            Deals in
          </Text>
          <EntitySelect
            kind="product"
            placeholder="Any product"
            value={productId}
            onChange={setProductId}
          />
        </Box>
        <Select
          w={120}
          label="Stage"
          placeholder="Any"
          clearable
          data={[
            { value: 'ACTIVE', label: 'Known' },
            { value: 'PROSPECT', label: 'Prospect' },
          ]}
          value={stage}
          onChange={setStage}
        />
        {filtered && (
          <ActionIcon variant="subtle" size={36} onClick={clearFilters} aria-label="Clear filters">
            <IconX size={16} />
          </ActionIcon>
        )}
      </Group>

      <Group justify="space-between" wrap="nowrap">
        <Group gap={8}>
          <Button
            size="xs"
            variant="light"
            leftSection={<IconUsersGroup size={14} />}
            onClick={toggleAllShown}
            disabled={!selectable.length}
          >
            {allShown ? 'Unselect these' : `Select these ${selectable.length}`}
          </Button>
          {isFetching && <Loader size="xs" />}
        </Group>
        <Text fz="xs" c="ink.5">
          {data?.total ?? 0} match{(data?.total ?? 0) === 1 ? '' : 'es'}
          {(data?.total ?? 0) > PAGE_SIZE && ` · showing first ${PAGE_SIZE}`}
        </Text>
      </Group>

      <ScrollArea.Autosize mah={320} type="auto">
        <Stack gap={2} pr="xs">
          {rows.map((row) => (
            <Row
              key={row.id}
              row={row}
              checked={lockedSet.has(row.id) || selected.includes(row.id)}
              locked={lockedSet.has(row.id)}
              onToggle={() => toggle(row.id)}
            />
          ))}
          {!rows.length && !isFetching && (
            <Text fz="sm" c="ink.5" ta="center" py="lg">
              No {partyType.toLowerCase()}s match these filters.
            </Text>
          )}
        </Stack>
      </ScrollArea.Autosize>

      <Group justify="space-between">
        <Text fz="sm" fw={600}>
          {selected.length + locked.length} invited
        </Text>
        {selected.length > 0 && (
          <Button size="xs" variant="subtle" color="ink" onClick={() => onChange([])}>
            Clear selection
          </Button>
        )}
      </Group>
    </Stack>
  );
}

function Row({
  row,
  checked,
  locked,
  onToggle,
}: {
  row: PartyListItem;
  checked: boolean;
  locked: boolean;
  onToggle: () => void;
}) {
  return (
    <Group
      gap={10}
      wrap="nowrap"
      px="xs"
      py={6}
      style={{
        borderRadius: 8,
        cursor: locked ? 'default' : 'pointer',
        background: checked ? 'var(--row-hover)' : undefined,
        opacity: locked ? 0.6 : 1,
      }}
      onClick={locked ? undefined : onToggle}
    >
      <Checkbox checked={checked} disabled={locked} onChange={() => undefined} tabIndex={-1} />
      <PartyAvatar name={row.name} size={28} />
      <Box style={{ minWidth: 0, flex: 1 }}>
        <Group gap={6} wrap="nowrap">
          <Text fz="sm" fw={550} truncate>
            {row.name}
          </Text>
          {row.stage === 'PROSPECT' && (
            <Badge size="xs" color="amber" variant="light">
              Prospect
            </Badge>
          )}
          {locked && (
            <Badge size="xs" variant="light" color="gray">
              Invited
            </Badge>
          )}
        </Group>
        <Text fz="xs" c="ink.5" truncate>
          {[row.primary_city, row.gst_number].filter(Boolean).join(' · ') || '—'}
        </Text>
      </Box>
    </Group>
  );
}
