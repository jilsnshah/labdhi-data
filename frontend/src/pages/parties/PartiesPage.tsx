import {
  Badge,
  Button,
  Group,
  SegmentedControl,
  Stack,
  Switch,
  Text,
  TextInput,
} from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { usePartyBookSummary, useParties } from '@/api/hooks';
import type { PartyListItem, PartyType } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { EntitySelect } from '@/components/EntitySelect';
import { FilterBar, StatusFilter } from '@/components/FilterBar';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { KpiTile, PartyAvatar } from '@/components/market/Visuals';
import { PartyFormModal } from '@/components/modals/PartyModals';
import { useListState } from '@/hooks/useListState';
import { humanize } from '@/lib/format';

const COPY: Record<PartyType, { title: string; subtitle: string }> = {
  CUSTOMER: {
    title: 'Customers',
    subtitle: 'Who buys material, what they buy and what they have asked for.',
  },
  SUPPLIER: {
    title: 'Suppliers',
    subtitle: 'Who can source material, and at what rates they have quoted.',
  },
  TRANSPORTER: {
    title: 'Transporters',
    subtitle: 'Who moves the material, on which routes.',
  },
};

export function PartiesPage({ partyType }: { partyType: PartyType }) {
  const navigate = useNavigate();
  const list = useListState<{
    status?: string;
    city?: string;
    product_id?: number;
    stage?: string;
    stale_days?: number;
  }>({}, { sortBy: 'name', sortDir: 'asc' });
  const { data, isFetching } = useParties({ ...list.params, party_type: partyType });
  // Book-level figures for this party type, independent of the table's filters.
  const { data: book } = usePartyBookSummary(partyType);
  const accent =
    partyType === 'SUPPLIER'
      ? 'var(--supply)'
      : partyType === 'CUSTOMER'
        ? 'var(--demand)'
        : 'var(--mantine-color-ink-7)';
  const [createOpen, setCreateOpen] = useState(false);

  const columns: Column<PartyListItem>[] = [
    {
      key: 'name',
      label: humanize(partyType),
      sortable: true,
      render: (row) => (
        <Group gap={12} wrap="nowrap">
          <PartyAvatar name={row.name} size={36} />
          <Stack gap={0} style={{ minWidth: 0 }}>
            <Group gap={6} wrap="nowrap">
              <Text fw={600} c="ink.9" truncate maw={240}>
                {row.name}
              </Text>
              {row.stage !== 'ACTIVE' && <StatusBadge value={row.stage} size="xs" />}
            </Group>
            {row.contact_person && (
              <Text fz="xs" c="dimmed">
                {row.contact_person}
              </Text>
            )}
          </Stack>
        </Group>
      ),
    },
    {
      key: 'contact',
      label: 'Contact',
      render: (row) => (
        <Stack gap={0}>
          <Text fz="sm">{row.phone || '—'}</Text>
          {(row.email || row.gst_number) && (
            <Text fz="xs" c="dimmed" truncate maw={200}>
              {row.email ?? `GST ${row.gst_number}`}
            </Text>
          )}
        </Stack>
      ),
    },
    {
      key: 'city',
      label: 'City',
      render: (row) => <Text fz="sm">{row.primary_city || '-'}</Text>,
    },
    {
      key: 'products',
      label: 'Products',
      align: 'right',
      render: (row) =>
        partyType === 'TRANSPORTER' ? (
          <Text fz="sm" c="dimmed">
            -
          </Text>
        ) : (
          <Text fz="sm">{row.product_count}</Text>
        ),
    },
    {
      key: 'open',
      label: 'Open inquiries',
      align: 'right',
      render: (row) =>
        row.open_inquiry_count > 0 ? (
          <Badge variant="default" size="sm">
            {row.open_inquiry_count}
          </Badge>
        ) : (
          <Text fz="sm" c="dimmed">
            0
          </Text>
        ),
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge value={row.status} /> },
  ];

  return (
    <div className="page-fill">
      <PageHeader
        eyebrow="Relationships"
        title={COPY[partyType].title}
        subtitle={COPY[partyType].subtitle}
        actions={
          <Button leftSection={<IconPlus size={14} />} onClick={() => setCreateOpen(true)}>
            New {partyType.toLowerCase()}
          </Button>
        }
      />
      <div className="kpi-row">
        <KpiTile
          label={`${humanize(partyType)}s`}
          value={book?.total ?? '—'}
          hint={book ? `${book.verified} verified` : '—'}
          accent={accent}
        />
        <KpiTile
          label="With live inquiries"
          value={book?.with_open_inquiries ?? '—'}
          hint={
            book?.total
              ? `${Math.round((book.with_open_inquiries / book.total) * 100)}% of the book`
              : '—'
          }
          accent={accent}
        />
        <KpiTile
          label="Prospects"
          value={book?.prospects ?? '—'}
          hint="to verify"
          accent="var(--brass)"
        />
        <KpiTile
          label="Cities"
          value={book?.cities ?? '—'}
          hint="primary locations"
          accent={accent}
        />
      </div>
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Search name, phone, email, GST"
        onReset={list.resetFilters}
      >
        <SegmentedControl
          size="xs"
          value={(list.filters.stage as string) ?? 'ALL'}
          onChange={(value) => list.setFilter('stage', value === 'ALL' ? undefined : value)}
          data={[
            { value: 'ALL', label: 'All' },
            { value: 'ACTIVE', label: 'Known' },
            { value: 'PROSPECT', label: 'Prospects' },
          ]}
        />
        <Switch
          label="Stale leads"
          description="60 days, untouched"
          checked={list.filters.stale_days === 60}
          onChange={(event) =>
            list.setFilter('stale_days', event.currentTarget.checked ? 60 : undefined)
          }
        />
        <TextInput
          w={132}
          placeholder="City"
          value={(list.filters.city as string) ?? ''}
          onChange={(event) => list.setFilter('city', event.currentTarget.value || undefined)}
        />
        {partyType !== 'TRANSPORTER' && (
          <div style={{ width: 200 }}>
            <EntitySelect
              kind="product"
              placeholder="Linked to product"
              value={list.filters.product_id ?? null}
              onChange={(value) => list.setFilter('product_id', value ?? undefined)}
            />
          </div>
        )}
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
        onRowClick={(row) => navigate(`/parties/${row.id}`)}
        emptyMessage={`No ${partyType.toLowerCase()}s match these filters`}
        emptyHint="Try clearing the filters, or add the first one."
      />
      {createOpen && <PartyFormModal partyType={partyType} onClose={() => setCreateOpen(false)} />}
    </div>
  );
}
