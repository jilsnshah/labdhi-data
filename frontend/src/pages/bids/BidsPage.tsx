/** Every bid of one type, newest first - the room, the quotes and where it stands. */

import { Badge, Button, Group, Select, Stack, Text } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useBids } from '@/api/hooks';
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
import { formatDateTime, formatQuantity } from '@/lib/format';

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
  const list = useListState<{ status?: string; product_id?: number }>(
    {},
    { sortBy: 'created_at', sortDir: 'desc' },
  );
  const { data, isFetching } = useBids({ ...list.params, bid_type: bidType });
  const [createOpen, setCreateOpen] = useState(false);
  const copy = COPY[bidType];

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
        {bidType !== 'TRANSPORT' && (
          <EntitySelect
            kind="product"
            placeholder="Any product"
            value={(list.filters.product_id as number) ?? null}
            onChange={(value) => list.setFilter('product_id', value ?? undefined)}
          />
        )}
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
