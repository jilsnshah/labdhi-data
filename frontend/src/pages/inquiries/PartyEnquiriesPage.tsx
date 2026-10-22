/**
 * What parties sent in through their own links.
 *
 * Every row here is already an inquiry - a party writes in and it is on the
 * book - so there is nothing to approve and nothing to press. The screen earns
 * its place by holding what an inquiry cannot: the note they wrote, and the
 * places in their own words rather than the location rows we matched them to.
 *
 * Read it as a record of where the book's newest entries came from.
 */

import { Badge, Button, SegmentedControl, Text, Tooltip } from '@mantine/core';
import { IconAdjustmentsHorizontal, IconArrowRight } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { usePortalEnquiries } from '@/api/hooks';
import type { DeskEnquiry, InquiryType } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { EntitySelect } from '@/components/EntitySelect';
import { FilterBar } from '@/components/FilterBar';
import { PageHeader } from '@/components/PageHeader';
import { useListState } from '@/hooks/useListState';
import { formatDateTime, formatQuantity } from '@/lib/format';

const SIDE: Record<InquiryType, string> = {
  CUSTOMER: 'Wants',
  SUPPLIER: 'Offers',
  TRANSPORT: 'Can carry',
};

function route(row: DeskEnquiry) {
  const places = [row.from_place, row.to_place].filter(Boolean);
  return places.length ? places.join(' → ') : '—';
}

export function PartyEnquiriesPage() {
  const list = useListState<{
    inquiry_type?: string;
    party_id?: number;
    product_id?: number;
    material_id?: number;
    grade_id?: number;
    manufacturer_id?: number;
    application_id?: number;
  }>({});
  const { data, isFetching } = usePortalEnquiries(list.params);
  const [productOpen, setProductOpen] = useState(false);

  const productFilterCount = [
    list.filters.product_id,
    list.filters.material_id,
    list.filters.grade_id,
    list.filters.manufacturer_id,
    list.filters.application_id,
  ].filter((value) => value !== undefined && value !== null).length;

  const columns: Column<DeskEnquiry>[] = [
    {
      key: 'party',
      label: 'Who asked',
      cardTitle: true,
      render: (row) => (
        <div>
          <Link to={`/parties/${row.party.id}`} className="cell-link">
            {row.party.name}
          </Link>
          <Text size="xs" c="dimmed">
            {SIDE[row.inquiry_type]}
          </Text>
        </div>
      ),
    },
    {
      key: 'product',
      label: 'Grade',
      render: (row) =>
        row.product ? (
          <Text size="sm">{row.product.display_name}</Text>
        ) : (
          <Text size="sm" c="dimmed">
            —
          </Text>
        ),
    },
    {
      key: 'quantity',
      label: 'Quantity',
      align: 'right',
      render: (row) => formatQuantity(row.quantity, row.unit),
    },
    {
      key: 'route',
      label: 'Where they said',
      cardMeta: true,
      render: (row) => (
        <Tooltip label="The words they typed, not the location we matched" withArrow>
          <Text size="sm">{route(row)}</Text>
        </Tooltip>
      ),
    },
    {
      key: 'rate',
      label: 'They said',
      align: 'right',
      render: (row) =>
        row.rate ? `${row.inquiry_type === 'TRANSPORT' ? '₹' : '₹/kg'} ${row.rate}` : '—',
    },
    {
      key: 'notes',
      label: 'Their note',
      render: (row) =>
        row.notes ? (
          <Text size="sm" fs="italic" lineClamp={2}>
            “{row.notes}”
          </Text>
        ) : (
          <Text size="sm" c="dimmed">
            —
          </Text>
        ),
    },
    {
      key: 'created_at',
      label: 'Sent',
      cardMeta: true,
      render: (row) => (
        <Text size="xs" c="dimmed">
          {formatDateTime(row.created_at)}
        </Text>
      ),
    },
    {
      key: 'inquiry',
      label: 'On the book as',
      width: 160,
      render: (row) => (
        <Button
          component={Link}
          to={`/inquiries/${row.inquiry_id}`}
          size="xs"
          variant="light"
          rightSection={<IconArrowRight size={14} />}
        >
          Inquiry #{row.inquiry_id}
        </Button>
      ),
    },
  ];

  return (
    <div className="page-fill">
      <PageHeader
        eyebrow="Inquiries"
        title="From parties"
        subtitle="Sent in by customers, suppliers and transporters through their own link. Each one is already on the book."
      />
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Party, grade, place or anything they typed"
        onReset={() => {
          list.resetFilters();
          setProductOpen(false);
        }}
      >
        <SegmentedControl
          size="xs"
          value={list.filters.inquiry_type ?? 'ALL'}
          onChange={(value) => list.setFilter('inquiry_type', value === 'ALL' ? undefined : value)}
          data={[
            { label: 'All', value: 'ALL' },
            { label: 'Customer', value: 'CUSTOMER' },
            { label: 'Supplier', value: 'SUPPLIER' },
            { label: 'Transport', value: 'TRANSPORT' },
          ]}
        />
        <div style={{ width: 190 }}>
          <EntitySelect
            kind="party"
            placeholder="Any party"
            includeInactive
            value={list.filters.party_id ?? null}
            onChange={(value) => list.setFilter('party_id', value ?? undefined)}
          />
        </div>
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
        {productOpen && (
          // These narrow through the product, so a load - which has none - is
          // never matched by them.
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
      </FilterBar>

      <DataTable
        columns={columns}
        rows={data?.items ?? []}
        total={data?.total}
        page={list.page}
        pageSize={list.pageSize}
        onPageChange={list.setPage}
        onPageSizeChange={list.setPageSize}
        loading={isFetching}
        fill
        emptyMessage="Nothing has come in yet."
        emptyHint="Send a party their enquiry link from their page, and what they send lands here - and on the book."
      />
    </div>
  );
}
