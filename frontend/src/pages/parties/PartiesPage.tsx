import {
  ActionIcon,
  Badge,
  Button,
  Group,
  Modal,
  Select,
  SegmentedControl,
  Stack,
  Switch,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import {
  IconAdjustmentsHorizontal,
  IconArrowsExchange,
  IconBuildingStore,
  IconMapPin,
  IconPlus,
  IconProgressCheck,
  IconUserPlus,
} from '@tabler/icons-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  partyApi,
  useApiMutation,
  useLocationAreas,
  usePartyBookSummary,
  useParties,
} from '@/api/hooks';
import type { PartyListItem, PartyType } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { EntitySelect } from '@/components/EntitySelect';
import { FilterBar, StatusFilter } from '@/components/FilterBar';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { PartyAvatar } from '@/components/market/Visuals';
import { PartyFormModal } from '@/components/modals/PartyModals';
import { KpiTile } from '@/components/ui';
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
    area?: string;
    product_id?: number;
    material_id?: number;
    grade_id?: number;
    manufacturer_id?: number;
    application_id?: number;
    stage?: string;
    stale_days?: number;
  }>({}, { sortBy: 'name', sortDir: 'asc' });
  const { data, isFetching } = useParties({ ...list.params, party_type: partyType });
  // Book-level figures for this party type, independent of the table's filters.
  const { data: book } = usePartyBookSummary(partyType);
  /** The other side of the trade; transporters have no opposite book. */
  const moveTarget =
    partyType === 'CUSTOMER'
      ? { type: 'SUPPLIER', label: 'suppliers', noun: 'supplier' }
      : partyType === 'SUPPLIER'
        ? { type: 'CUSTOMER', label: 'customers', noun: 'customer' }
        : null;
  const [moving, setMoving] = useState<PartyListItem | null>(null);
  const [productOpen, setProductOpen] = useState(false);
  const { data: areas } = useLocationAreas();

  // How many of the product filters are set, so the button can say so.
  const productFilterCount = (
    ['product_id', 'material_id', 'grade_id', 'manufacturer_id', 'application_id'] as const
  ).filter((key) => list.filters[key] !== undefined).length;
  const move = useApiMutation((partyId: number) => partyApi.move(partyId, moveTarget!.type), {
    successMessage: `Moved to ${moveTarget?.label ?? 'the other book'}`,
  });
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
        <Group gap={8} wrap="nowrap">
          <PartyAvatar name={row.name} size={24} />
          <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
            <Text fz="sm" fw={600} c="ink.9" truncate maw={280}>
              {row.name}
            </Text>
            {row.stage !== 'ACTIVE' && <StatusBadge value={row.stage} size="xs" />}
          </Group>
        </Group>
      ),
    },
    {
      key: 'contact_person',
      label: 'Contact person',
      render: (row) => (
        <Text fz="sm" c={row.contact_person ? 'ink.8' : 'ink.4'} truncate maw={180}>
          {row.contact_person || '—'}
        </Text>
      ),
    },
    {
      key: 'contact',
      label: 'Phone',
      render: (row) => (
        <Text fz="sm" className="mono-tight" c={row.phone ? 'ink.8' : 'ink.4'}>
          {row.phone || '—'}
        </Text>
      ),
    },
    {
      key: 'email',
      label: 'Email / GST',
      cardHidden: true,
      render: (row) => (
        <Text fz="xs" c="ink.5" truncate maw={200}>
          {row.email ?? (row.gst_number ? `GST ${row.gst_number}` : '—')}
        </Text>
      ),
    },
    {
      key: 'city',
      label: 'City',
      render: (row) => (
        <Text fz="sm" c={row.primary_city ? 'ink.8' : 'ink.4'}>
          {row.primary_city || '—'}
        </Text>
      ),
    },
    {
      key: 'products',
      label: 'Products',
      align: 'right',
      render: (row) =>
        partyType === 'TRANSPORTER' ? (
          <Text fz="sm" c="ink.4">
            —
          </Text>
        ) : (
          <Text fz="sm" className="mono-tight">
            {row.product_count}
          </Text>
        ),
    },
    {
      key: 'open',
      label: 'Open inquiries',
      align: 'right',
      render: (row) => (
        <Text
          fz="sm"
          className="mono-tight"
          fw={row.open_inquiry_count > 0 ? 600 : 400}
          c={row.open_inquiry_count > 0 ? 'ink.9' : 'ink.4'}
        >
          {row.open_inquiry_count}
        </Text>
      ),
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge value={row.status} /> },
    ...(moveTarget
      ? [
          {
            key: 'move',
            label: 'Move',
            width: 62,
            render: (row: PartyListItem) => (
              <Tooltip label={`Move to ${moveTarget.label}`} withinPortal>
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  aria-label={`Move ${row.name} to ${moveTarget.label}`}
                  loading={move.isPending && move.variables === row.id}
                  onClick={(event) => {
                    event.stopPropagation();
                    setMoving(row);
                  }}
                >
                  <IconArrowsExchange size={16} />
                </ActionIcon>
              </Tooltip>
            ),
          },
        ]
      : []),
  ];

  return (
    <div className="page-fill">
      <PageHeader
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
          icon={<IconBuildingStore size={14} />}
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
          icon={<IconProgressCheck size={14} />}
          accent={accent}
        />
        <KpiTile
          label="Prospects"
          value={book?.prospects ?? '—'}
          hint="to verify"
          icon={<IconUserPlus size={14} />}
          accent="var(--brass)"
        />
        <KpiTile
          label="Cities"
          value={book?.cities ?? '—'}
          hint="primary locations"
          icon={<IconMapPin size={14} />}
          accent={accent}
        />
      </div>
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Search name, phone, email, GST"
        onReset={list.resetFilters}
        extraOpen={partyType !== 'TRANSPORTER' && productOpen}
        extra={
          partyType !== 'TRANSPORTER' ? (
            // What they deal in, read off the products linked to the party. A
            // transporter carries no products, so these do not apply there.
            <>
              <Text fz="xs" c="ink.5" w={74}>
                Deals in
              </Text>
              <EntitySelect
                className="field-lg"
                kind="product"
                placeholder="Any product"
                includeInactive
                value={list.filters.product_id ?? null}
                onChange={(value) => list.setFilter('product_id', value ?? undefined)}
              />
              <EntitySelect
                className="field-md"
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
              <EntitySelect
                className="field-md"
                kind="grade"
                placeholder="Any grade"
                includeInactive
                filters={
                  list.filters.material_id ? { material_id: list.filters.material_id } : undefined
                }
                value={list.filters.grade_id ?? null}
                onChange={(value) => list.setFilter('grade_id', value ?? undefined)}
              />
              <EntitySelect
                className="field-md"
                kind="manufacturer"
                placeholder="Any brand"
                includeInactive
                value={list.filters.manufacturer_id ?? null}
                onChange={(value) => list.setFilter('manufacturer_id', value ?? undefined)}
              />
              <EntitySelect
                className="field-lg"
                kind="application"
                placeholder="Any application"
                includeInactive
                value={list.filters.application_id ?? null}
                onChange={(value) => list.setFilter('application_id', value ?? undefined)}
              />
            </>
          ) : undefined
        }
      >
        <SegmentedControl
          value={(list.filters.stage as string) ?? 'ALL'}
          onChange={(value) => list.setFilter('stage', value === 'ALL' ? undefined : value)}
          data={[
            { value: 'ALL', label: 'All' },
            { value: 'ACTIVE', label: 'Known' },
            { value: 'PROSPECT', label: 'Prospects' },
          ]}
        />
        <TextInput
          className="field-sm"
          placeholder="City"
          value={(list.filters.city as string) ?? ''}
          onChange={(event) => list.setFilter('city', event.currentTarget.value || undefined)}
        />
        <Select
          className="field-md"
          placeholder="Any area"
          data={areas ?? []}
          value={list.filters.area ?? null}
          onChange={(value) => list.setFilter('area', value ?? undefined)}
          searchable
          clearable
        />
        <StatusFilter
          value={list.filters.status}
          onChange={(value) => list.setFilter('status', value)}
        />
        <Switch
          label="Stale leads"
          checked={list.filters.stale_days === 60}
          onChange={(event) =>
            list.setFilter('stale_days', event.currentTarget.checked ? 60 : undefined)
          }
        />
        {partyType !== 'TRANSPORTER' && (
          <Button
            variant={productFilterCount || productOpen ? 'light' : 'default'}
            color="ink"
            leftSection={<IconAdjustmentsHorizontal size={14} />}
            rightSection={
              productFilterCount ? (
                <Badge size="xs" circle color="ink" variant="filled">
                  {productFilterCount}
                </Badge>
              ) : undefined
            }
            onClick={() => setProductOpen((open) => !open)}
            aria-expanded={productOpen}
          >
            Products
          </Button>
        )}
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
      {moveTarget && (
        <Modal
          opened={moving !== null}
          onClose={() => setMoving(null)}
          title={`Move to ${moveTarget.label}`}
          centered
        >
          <Stack gap="md">
            <Text fz="sm">
              <b>{moving?.name}</b> becomes a {moveTarget.noun}. Everything else - contacts,
              addresses, notes, activities and closed inquiries - stays as it is.
            </Text>
            <Group justify="flex-end" gap="sm">
              <Button variant="default" onClick={() => setMoving(null)}>
                Cancel
              </Button>
              <Button
                loading={move.isPending}
                leftSection={<IconArrowsExchange size={16} />}
                onClick={() =>
                  moving &&
                  move.mutate(moving.id, {
                    onSuccess: () => setMoving(null),
                  })
                }
              >
                Move
              </Button>
            </Group>
          </Stack>
        </Modal>
      )}
    </div>
  );
}
