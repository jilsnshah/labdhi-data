import {
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
} from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { api } from '@/api/client';
import { useApiMutation, useLocationAreas, useLocations } from '@/api/hooks';
import type { Location } from '@/api/types';
import { AreaInput } from '@/components/AreaInput';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { FilterBar, StatusFilter } from '@/components/FilterBar';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { useListState } from '@/hooks/useListState';

export function LocationsPage() {
  const list = useListState<{ status?: string; city?: string; area?: string }>(
    {},
    { sortBy: 'city', sortDir: 'asc' },
  );
  const { data, isFetching } = useLocations(list.params);
  const { data: areas } = useLocationAreas();
  const [editing, setEditing] = useState<Location | null>(null);
  const [opened, setOpened] = useState(false);

  const open = (record: Location | null) => {
    setEditing(record);
    setOpened(true);
  };

  const columns: Column<Location>[] = [
    {
      key: 'label',
      label: 'Label',
      sortable: true,
      render: (row) => <Text fw={500}>{row.label || `Location #${row.id}`}</Text>,
    },
    {
      key: 'area',
      label: 'Area',
      sortable: true,
      render: (row) => (
        <Text fz="sm" c={row.area ? undefined : 'dimmed'}>
          {row.area || '-'}
        </Text>
      ),
    },
    {
      key: 'city',
      label: 'City',
      sortable: true,
      render: (row) => <Text fz="sm">{row.city}</Text>,
    },
    { key: 'state', label: 'State', render: (row) => <Text fz="sm">{row.state || '-'}</Text> },
    {
      key: 'address',
      label: 'Address',
      render: (row) => (
        <Text fz="sm" c="dimmed" lineClamp={1}>
          {[row.address_line_1, row.address_line_2, row.pincode].filter(Boolean).join(', ') || '-'}
        </Text>
      ),
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge value={row.status} /> },
  ];

  return (
    <div className="page-fill">
      <PageHeader
        title="Locations"
        subtitle="Independent addresses: head offices, factories, warehouses and delivery points."
        actions={
          <Button leftSection={<IconPlus size={14} />} onClick={() => open(null)}>
            New location
          </Button>
        }
      />
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Search label, area, city, address, pincode"
        onReset={list.resetFilters}
      >
        <Select
          className="field-lg"
          placeholder="Any area"
          data={areas ?? []}
          value={(list.filters.area as string) ?? null}
          onChange={(value) => list.setFilter('area', value ?? undefined)}
          searchable
          clearable
        />
        <TextInput
          className="field-md"
          placeholder="City"
          value={(list.filters.city as string) ?? ''}
          onChange={(event) => list.setFilter('city', event.currentTarget.value || undefined)}
        />
        <StatusFilter
          value={list.filters.status}
          onChange={(value) => list.setFilter('status', value)}
        />
      </FilterBar>
      <DataTable
        columns={columns}
        rows={data?.items ?? []}
        total={data?.total}
        page={list.page}
        pageSize={list.pageSize}
        onPageChange={list.setPage}
        onPageSizeChange={list.setPageSize}
        sort={list.sort}
        onSortChange={list.setSort}
        loading={isFetching}
        fill
        onRowClick={open}
        emptyMessage="No locations match these filters"
      />
      {opened && (
        <LocationModal
          key={editing?.id ?? 'new'}
          record={editing}
          onClose={() => setOpened(false)}
        />
      )}
    </div>
  );
}

export function LocationModal({
  record,
  onClose,
  onCreated,
}: {
  record: Location | null;
  onClose: () => void;
  onCreated?: (location: Location) => void;
}) {
  const [form, setForm] = useState({
    label: record?.label ?? '',
    address_line_1: record?.address_line_1 ?? '',
    address_line_2: record?.address_line_2 ?? '',
    area: record?.area ?? '',
    city: record?.city ?? '',
    state: record?.state ?? '',
    country: record?.country ?? 'India',
    pincode: record?.pincode ?? '',
    latitude: record?.latitude ? Number(record.latitude) : undefined,
    longitude: record?.longitude ? Number(record.longitude) : undefined,
  });
  const [active, setActive] = useState((record?.status ?? 'ACTIVE') === 'ACTIVE');

  const save = useApiMutation(
    (body: Record<string, unknown>) =>
      record
        ? api.patch<Location>(`/locations/${record.id}`, body)
        : api.post<Location>('/locations', body),
    { successMessage: `Location ${record ? 'updated' : 'created'}` },
  );

  const submit = async () => {
    const created = await save.mutateAsync({
      ...form,
      label: form.label || null,
      address_line_1: form.address_line_1 || null,
      address_line_2: form.address_line_2 || null,
      area: form.area.trim() || null,
      state: form.state || null,
      pincode: form.pincode || null,
      ...(record ? { status: active ? 'ACTIVE' : 'INACTIVE' } : {}),
    });
    onCreated?.(created);
    onClose();
  };

  const set = (key: keyof typeof form, value: string | number | undefined) =>
    setForm((current) => ({ ...current, [key]: value }));

  return (
    <Modal opened onClose={onClose} title={record ? `Location #${record.id}` : 'New location'}>
      <Stack gap="md">
        <TextInput
          label="Label"
          placeholder="e.g. Ahmedabad Warehouse"
          data-autofocus
          value={form.label}
          onChange={(event) => set('label', event.currentTarget.value)}
        />
        <TextInput
          label="Address line 1"
          value={form.address_line_1}
          onChange={(event) => set('address_line_1', event.currentTarget.value)}
        />
        <TextInput
          label="Address line 2"
          value={form.address_line_2}
          onChange={(event) => set('address_line_2', event.currentTarget.value)}
        />
        <Group grow>
          <AreaInput value={form.area} onChange={(value) => set('area', value)} />
          <TextInput
            label="City"
            required
            value={form.city}
            onChange={(event) => set('city', event.currentTarget.value)}
          />
        </Group>
        <Group grow>
          <TextInput
            label="State"
            value={form.state}
            onChange={(event) => set('state', event.currentTarget.value)}
          />
          <TextInput
            label="Country"
            value={form.country}
            onChange={(event) => set('country', event.currentTarget.value)}
          />
          <TextInput
            label="Pincode"
            value={form.pincode}
            onChange={(event) => set('pincode', event.currentTarget.value)}
          />
        </Group>
        <Group grow>
          <NumberInput
            label="Latitude"
            value={form.latitude}
            onChange={(value) => set('latitude', typeof value === 'number' ? value : undefined)}
            decimalScale={6}
            min={-90}
            max={90}
          />
          <NumberInput
            label="Longitude"
            value={form.longitude}
            onChange={(value) => set('longitude', typeof value === 'number' ? value : undefined)}
            decimalScale={6}
            min={-180}
            max={180}
          />
        </Group>
        {record && (
          <Switch
            label="Active"
            checked={active}
            onChange={(event) => setActive(event.currentTarget.checked)}
          />
        )}
        <Group justify="flex-end" mt="sm">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={save.isPending} disabled={!form.city.trim()}>
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
