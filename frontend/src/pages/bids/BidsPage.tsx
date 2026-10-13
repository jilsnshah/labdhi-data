/** Every bid of one type, newest first - the room, the quotes and where it stands. */

import { Badge, Button, Group, Select, Stack, Text } from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { IconAdjustmentsHorizontal, IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useBids, useLocationAreas } from '@/api/hooks';
import type { BidListItem, BidType } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { EntitySelect } from '@/components/EntitySelect';
import { FilterBar } from '@/components/FilterBar';
import { KpiTile } from '@/components/market/Visuals';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { BidFormModal } from '@/components/modals/BidFormModal';
import { useListState } from '@/hooks/useListState';
import { formatDateTime, formatQuantity, toIsoDate } from '@/lib/format';

const COPY: Record<BidType, { title: string; subtitle: string; action: string }> = {
  CUSTOMER: {
    title: 'Customer bids',
    subtitle: 'Material put out to customers. The highest offer leads.',
    action: 'New customer bid',
  },
  SUPPLIER: {
    title: 'Supplier bids',
    subtitle: 'Material asked of suppliers. The lowest offer leads.',
    action: 'New supplier bid',
  },
  TRANSPORT: {
    title: 'Transport bids',
    subtitle: 'Loads put out to transporters. The lowest offer leads.',
    action: 'New transport bid',
  },
};

/** Rupees per kilogram for material, rupees for a movement. */
export const priceUnit = (type: BidType) => (type === 'TRANSPORT' ? '₹' : '₹/kg');

export function BidsPage({ bidType }: { bidType: BidType }) {
  const navigate = useNavigate();
  const list = useListState<{
    status?: string;
    product_id?: number;
    material_id?: number;
    grade_id?: number;
    manufacturer_id?: number;
    application_id?: number;
    area?: string;
    created_from?: string;
    created_to?: string;
  }>({}, { sortBy: 'created_at', sortDir: 'desc' });
  const { data, isFetching } = useBids({ ...list.params, bid_type: bidType });
  const { data: areas } = useLocationAreas();
  const [createOpen, setCreateOpen] = useState(false);
  const [productOpen, setProductOpen] = useState(false);
  const [range, setRange] = useState<[string | null, string | null]>([null, null]);
  const copy = COPY[bidType];

  // How many of the product filters are set, so the button can say so.
  const productFilterCount = (
    ['product_id', 'material_id', 'grade_id', 'manufacturer_id', 'application_id'] as const
  ).filter((key) => list.filters[key] !== undefined).length;

  const rows = data?.items ?? [];
  const live = rows.filter((row) => row.status === 'OPEN').length;
  const quotes = rows.reduce((total, row) => total + row.quote_count, 0);
  const awaiting = rows.reduce(
    (total, row) => total + (row.status === 'OPEN' ? row.participant_count - row.quote_count : 0),
    0,
  );

  const columns: Column<BidListItem>[] = [
    {
      key: 'bid',
      label: 'Bid',
      cardTitle: true,
      render: (row) => (
        <Stack gap={0}>
          <Group gap={8} wrap="nowrap">
            <Text fz="sm" fw={600} c="ink.9" truncate maw={320}>
              {row.title}
            </Text>
            {row.no_winner && (
              <Badge size="xs" variant="light" color="gray">
                No winner
              </Badge>
            )}
            {row.winner_party_name && (
              <Badge size="xs" variant="light" color="moss">
                Won: {row.winner_party_name}
              </Badge>
            )}
          </Group>
          <Text fz="xs" c="ink.5">
            #{row.id} · {formatDateTime(row.created_at)}
          </Text>
        </Stack>
      ),
    },
    {
      key: 'quantity',
      label: 'Quantity',
      align: 'right',
      render: (row) => (
        <Text fz="sm" className="mono-tight">
          {formatQuantity(row.quantity, row.unit)}
        </Text>
      ),
    },
    {
      key: 'room',
      label: 'Quotes',
      align: 'right',
      render: (row) => (
        <Stack gap={0} align="flex-end">
          <Text fz="sm" className="mono-tight">
            {row.quote_count} / {row.participant_count}
          </Text>
          <Text fz="xs" c="ink.5">
            invited
          </Text>
        </Stack>
      ),
    },
    {
      key: 'best',
      label: bidType === 'CUSTOMER' ? 'Best (highest)' : 'Best (lowest)',
      align: 'right',
      render: (row) =>
        row.best_price ? (
          <Text fz="sm" fw={600} className="figure">
            {priceUnit(bidType)} {row.best_price}
          </Text>
        ) : (
          <Text fz="xs" c="dimmed">
            —
          </Text>
        ),
    },
    {
      key: 'closes',
      label: 'Closes',
      render: (row) => (
        <Text fz="xs" c="ink.5">
          {row.closes_at ? formatDateTime(row.closes_at) : '—'}
        </Text>
      ),
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge value={row.status} /> },
  ];

  return (
    <div className="page-fill">
      <PageHeader
        eyebrow="Bids"
        title={copy.title}
        subtitle={copy.subtitle}
        actions={
          <Button leftSection={<IconPlus size={14} />} onClick={() => setCreateOpen(true)}>
            {copy.action}
          </Button>
        }
      />

      <div className="kpi-row">
        <KpiTile label="Bids" value={data?.total ?? '—'} hint="all time" accent="var(--brass)" />
        <KpiTile label="Live now" value={live} hint="taking quotes" accent="var(--supply)" />
        <KpiTile label="Quotes in" value={quotes} hint="on this page" accent="var(--demand)" />
        <KpiTile
          label="Yet to quote"
          value={awaiting}
          hint="invited, no offer"
          accent="var(--mantine-color-ink-7)"
        />
      </div>

      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Bid id, product or participant"
        onReset={list.resetFilters}
      >
        <Select
          w={140}
          placeholder="Any status"
          clearable
          data={[
            { value: 'DRAFT', label: 'Draft' },
            { value: 'OPEN', label: 'Open' },
            { value: 'CLOSED', label: 'Closed' },
          ]}
          value={(list.filters.status as string) ?? null}
          onChange={(value) => list.setFilter('status', value ?? undefined)}
        />
        {bidType === 'TRANSPORT' ? (
          <Select
            w={170}
            placeholder="Any area"
            data={areas ?? []}
            value={list.filters.area ?? null}
            onChange={(value) => list.setFilter('area', value ?? undefined)}
            searchable
            clearable
          />
        ) : (
          <Button
            variant={productFilterCount ? 'light' : 'default'}
            color={productFilterCount ? 'brass' : undefined}
            leftSection={<IconAdjustmentsHorizontal size={15} />}
            rightSection={
              productFilterCount ? (
                <Badge size="xs" circle color="brass" variant="filled">
                  {productFilterCount}
                </Badge>
              ) : undefined
            }
            onClick={() => setProductOpen((open) => !open)}
          >
            Product filters
          </Button>
        )}
        {bidType !== 'TRANSPORT' && productOpen && (
          // What the lot is made of. These narrow through the bid's product, so
          // they do not apply to a transport bid, which carries none.
          <>
            <div style={{ width: 190 }}>
              <EntitySelect
                kind="product"
                placeholder="Any product"
                includeInactive
                value={list.filters.product_id ?? null}
                onChange={(value) => list.setFilter('product_id', value ?? undefined)}
              />
            </div>
            <div style={{ width: 150 }}>
              <EntitySelect
                kind="material"
                placeholder="Any material"
                includeInactive
                value={list.filters.material_id ?? null}
                onChange={(value) => {
                  list.setFilter('material_id', value ?? undefined);
                  // A grade belongs to one material; drop one that no longer fits.
                  list.setFilter('grade_id', undefined);
                }}
              />
            </div>
            <div style={{ width: 140 }}>
              <EntitySelect
                kind="grade"
                placeholder="Any grade"
                includeInactive
                filters={
                  list.filters.material_id ? { material_id: list.filters.material_id } : undefined
                }
                value={list.filters.grade_id ?? null}
                onChange={(value) => list.setFilter('grade_id', value ?? undefined)}
              />
            </div>
            <div style={{ width: 150 }}>
              <EntitySelect
                kind="manufacturer"
                placeholder="Any brand"
                includeInactive
                value={list.filters.manufacturer_id ?? null}
                onChange={(value) => list.setFilter('manufacturer_id', value ?? undefined)}
              />
            </div>
            <div style={{ width: 170 }}>
              <EntitySelect
                kind="application"
                placeholder="Any application"
                includeInactive
                value={list.filters.application_id ?? null}
                onChange={(value) => list.setFilter('application_id', value ?? undefined)}
              />
            </div>
          </>
        )}
        <DatePickerInput
          type="range"
          w={190}
          placeholder="Raised between"
          valueFormat="DD MMM"
          clearable
          value={range}
          onChange={(value) => {
            const next = value as [string | null, string | null];
            setRange(next);
            list.setFilter('created_from', toIsoDate(next[0]));
            list.setFilter('created_to', toIsoDate(next[1]));
          }}
        />
      </FilterBar>

      <DataTable
        columns={columns}
        rows={rows}
        total={data?.total}
        page={list.page}
        pageSize={list.pageSize}
        onPageChange={list.setPage}
        onPageSizeChange={list.setPageSize}
        sort={list.sort}
        onSortChange={list.setSort}
        loading={isFetching}
        onRowClick={(row) => navigate(`/bids/${row.id}`)}
        emptyMessage="No bids yet"
        emptyHint="Raise one and invite the parties who should quote."
        fill
      />

      {createOpen && <BidFormModal bidType={bidType} onClose={() => setCreateOpen(false)} />}
    </div>
  );
}
