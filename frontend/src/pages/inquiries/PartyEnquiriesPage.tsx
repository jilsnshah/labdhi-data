/**
 * The inbox for enquiries parties raised themselves.
 *
 * These did not come from the desk, so they are not inquiries yet: each one is
 * somebody's own words, waiting to be read. The desk accepts one - which is
 * the moment a real inquiry exists, with master data behind every field and a
 * name against it - or declines it. Either way the words stay on the record.
 *
 * Waiting ones sort first, because every NEW row is a person outside expecting
 * an answer.
 */

import { Badge, Button, SegmentedControl, Text, Tooltip } from '@mantine/core';
import { IconAdjustmentsHorizontal, IconCheck, IconX } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { portalEnquiryApi, useApiMutation, usePortalEnquiries } from '@/api/hooks';
import type { DeskEnquiry, InquiryType, PortalEnquiryStatus } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { EntitySelect } from '@/components/EntitySelect';
import { FilterBar } from '@/components/FilterBar';
import { PageHeader } from '@/components/PageHeader';
import { AcceptEnquiryModal } from '@/components/modals/AcceptEnquiryModal';
import { useListState } from '@/hooks/useListState';
import { formatDateTime, formatQuantity } from '@/lib/format';

const STANDING: Record<PortalEnquiryStatus, { label: string; color: string }> = {
  NEW: { label: 'Waiting', color: 'brass' },
  ACCEPTED: { label: 'Accepted', color: 'teal' },
  DECLINED: { label: 'Declined', color: 'gray' },
};

const SIDE: Record<InquiryType, string> = {
  CUSTOMER: 'Wants',
  SUPPLIER: 'Offers',
  TRANSPORT: 'Can carry',
};

/** What they asked about: our grade if they found it, their words if not. */
function grade(row: DeskEnquiry) {
  if (row.product) return <Text size="sm">{row.product.display_name}</Text>;
  if (row.product_text) {
    return (
      <Tooltip label="Typed by the party - not a grade in our master data" withArrow>
        <Text size="sm" fs="italic" c="dimmed">
          “{row.product_text}”
        </Text>
      </Tooltip>
    );
  }
  return (
    <Text size="sm" c="dimmed">
      —
    </Text>
  );
}

function route(row: DeskEnquiry) {
  const places = [row.from_place, row.to_place].filter(Boolean);
  return places.length ? places.join(' → ') : '—';
}

export function PartyEnquiriesPage() {
  const list = useListState<{
    status?: string;
    inquiry_type?: string;
    party_id?: number;
    product_id?: number;
    material_id?: number;
    grade_id?: number;
    manufacturer_id?: number;
    application_id?: number;
  }>({ status: 'NEW' });
  const { data, isFetching } = usePortalEnquiries(list.params);
  const [accepting, setAccepting] = useState<DeskEnquiry | null>(null);
  const [productOpen, setProductOpen] = useState(false);

  const productFilterCount = [
    list.filters.product_id,
    list.filters.material_id,
    list.filters.grade_id,
    list.filters.manufacturer_id,
    list.filters.application_id,
  ].filter((value) => value !== undefined && value !== null).length;

  const decline = useApiMutation((id: number) => portalEnquiryApi.decline(id), {
    successMessage: 'Enquiry declined.',
    invalidate: ['portal-enquiries', 'portal-enquiry-counts'],
  });

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
    { key: 'product', label: 'Grade', render: grade },
    {
      key: 'quantity',
      label: 'Quantity',
      align: 'right',
      render: (row) => formatQuantity(row.quantity, row.unit),
    },
    { key: 'route', label: 'Where', cardMeta: true, render: route },
    {
      key: 'rate',
      label: 'They said',
      align: 'right',
      render: (row) =>
        row.rate ? `${row.inquiry_type === 'TRANSPORT' ? '₹' : '₹/kg'} ${row.rate}` : '—',
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
      key: 'status',
      label: 'Standing',
      render: (row) => (
        <div>
          <Badge size="sm" variant="light" color={STANDING[row.status].color}>
            {STANDING[row.status].label}
          </Badge>
          {row.status === 'ACCEPTED' && row.inquiry_id && (
            <div>
              <Link to={`/inquiries/${row.inquiry_id}`} className="cell-link">
                Inquiry #{row.inquiry_id}
              </Link>
            </div>
          )}
          {row.handler && (
            <Text size="xs" c="dimmed">
              by {row.handler.name}
            </Text>
          )}
        </div>
      ),
    },
    {
      key: 'decision',
      label: 'Decision',
      width: 190,
      render: (row) =>
        row.status === 'NEW' ? (
          <div className="row-actions">
            <Button
              size="xs"
              leftSection={<IconCheck size={14} />}
              onClick={() => setAccepting(row)}
            >
              Accept
            </Button>
            <Button
              size="xs"
              variant="default"
              leftSection={<IconX size={14} />}
              loading={decline.isPending && decline.variables === row.id}
              onClick={() => decline.mutate(row.id)}
            >
              Decline
            </Button>
          </div>
        ) : (
          <Text size="xs" c="dimmed">
            Decided {row.handled_at ? formatDateTime(row.handled_at) : ''}
          </Text>
        ),
    },
  ];

  return (
    <div className="page-fill">
      <PageHeader
        eyebrow="Inquiries"
        title="From parties"
        subtitle="Enquiries customers, suppliers and transporters sent in through their own link."
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
          value={list.filters.status ?? 'ALL'}
          onChange={(value) => list.setFilter('status', value === 'ALL' ? undefined : value)}
          data={[
            { label: 'Waiting', value: 'NEW' },
            { label: 'Accepted', value: 'ACCEPTED' },
            { label: 'Declined', value: 'DECLINED' },
            { label: 'All', value: 'ALL' },
          ]}
        />
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
          // These narrow through the grade we recognised, so an enquiry whose
          // product was typed as free text is not reachable by them.
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
        emptyHint="Send a party their enquiry link from their page, and what they send lands here."
      />

      <AcceptEnquiryModal
        enquiry={accepting}
        onClose={() => setAccepting(null)}
      />
    </div>
  );
}
