/**
 * What parties sent in through their own links.
 *
 * Every row here is already an inquiry - a party writes in and it is on the
 * book - so there is nothing to approve and nothing to press. The screen earns
 * its place by holding what an inquiry cannot: the note they wrote, and the
 * places in their own words rather than the location rows we matched them to.
 *
 * Read it as a record of where the book's newest entries came from, and as the
 * one view of what the desk is being asked for without having asked.
 */

import { Badge, Button, Group, SegmentedControl, Stack, Text, Tooltip } from '@mantine/core';
import { IconAdjustmentsHorizontal, IconArrowRight } from '@tabler/icons-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { usePortalEnquiries } from '@/api/hooks';
import type { DeskEnquiry, InquiryType } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { EntitySelect } from '@/components/EntitySelect';
import { FilterBar } from '@/components/FilterBar';
import { KpiTile } from '@/components/ui';
import { PageHeader } from '@/components/PageHeader';
import { PartyAvatar } from '@/components/market/Visuals';
import { useListState } from '@/hooks/useListState';
import { formatDateTime, formatQuantity, formatMoney } from '@/lib/format';
import { dailyCounts, fmtRate, fmtTonnes } from '@/lib/market';

/** What each side of the trade is doing when it writes in. */
const SIDE: Record<InquiryType, string> = {
  CUSTOMER: 'Wants',
  SUPPLIER: 'Offers',
  TRANSPORT: 'Can carry',
};

function route(row: DeskEnquiry) {
  const places = [row.from_place, row.to_place].filter(Boolean);
  return places.length ? places.join(' → ') : '—';
}

/**
 * The four figures above the log.
 *
 * They summarise everything the current filters match rather than the page on
 * screen, which is why the page asks for a wider slice to count from - the
 * same arrangement the other inquiry screens use.
 */
function summarise(rows: DeskEnquiry[]) {
  const tonnes = rows.reduce((total, row) => {
    const quantity = Number(row.quantity ?? 0);
    if (row.unit === 'MT') return total + quantity;
    if (row.unit === 'KG') return total + quantity / 1000;
    return total;
  }, 0);
  const parties = new Set(rows.map((row) => row.party.id));
  const prospects = new Set(
    rows.filter((row) => row.party.stage === 'PROSPECT').map((row) => row.party.id),
  );
  // A rate on a load is the whole freight; on a product it is per kilogram.
  // Averaging the two together would be a number that means nothing.
  const rated = rows.filter((row) => row.rate && row.inquiry_type !== 'TRANSPORT');
  const rates = rated.map((row) => Number(row.rate));
  const capped = rows.length >= 200 ? ' (latest 200)' : '';

  return {
    count: rows.length,
    countHint: `from ${parties.size} ${parties.size === 1 ? 'party' : 'parties'}${capped}`,
    spark: dailyCounts(rows.map((row) => row.created_at)),
    volume: fmtTonnes(tonnes),
    avg: rates.length ? fmtRate(rates.reduce((a, b) => a + b, 0) / rates.length) : '—',
    avgHint: rates.length
      ? `${rates.length} named a rate`
      : 'nobody named a rate',
    prospects: prospects.size,
    prospectsHint: prospects.size ? 'still to verify' : 'all known to the desk',
  };
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
  const { data: slice } = usePortalEnquiries({ ...list.params, page: 1, page_size: 200 });
  const kpis = useMemo(() => summarise(slice?.items ?? []), [slice]);
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
        <Group gap={10} wrap="nowrap">
          <PartyAvatar name={row.party.name} size={30} />
          <Stack gap={0} style={{ minWidth: 0 }}>
            <Text fz="sm" fw={600} c="ink.9" truncate maw={190}>
              {row.party.name}
            </Text>
            <Text fz={11} c="ink.5">
              {SIDE[row.inquiry_type]}
              {row.party.stage === 'PROSPECT' && ' · prospect'}
            </Text>
          </Stack>
        </Group>
      ),
    },
    {
      key: 'what',
      label: 'What they asked for',
      render: (row) => (
        <Stack gap={0}>
          <Text fz="sm" truncate maw={240}>
            {row.product ? row.product.display_name : 'Transport'}
          </Text>
          <Text fz="xs" c="dimmed" className="mono-tight">
            {formatQuantity(row.quantity, row.unit)}
          </Text>
        </Stack>
      ),
    },
    {
      key: 'route',
      label: 'Where',
      cardMeta: true,
      render: (row) => (
        <Tooltip label="Their own words, not the location we matched" withArrow>
          <Text fz="sm" truncate maw={190}>
            {route(row)}
          </Text>
        </Tooltip>
      ),
    },
    {
      key: 'rate',
      label: 'They said',
      align: 'right',
      width: 130,
      render: (row) => {
        if (!row.rate) {
          return (
            <Text fz="sm" c="dimmed">
              —
            </Text>
          );
        }
        return (
          <Text fz="sm" className="mono-tight">
            {row.inquiry_type === 'TRANSPORT'
              ? formatMoney(row.rate)
              : `${fmtRate(Number(row.rate))}/kg`}
          </Text>
        );
      },
    },
    {
      key: 'notes',
      label: 'Their note',
      render: (row) =>
        row.notes ? (
          <Tooltip label={row.notes} withArrow multiline w={320}>
            <Text fz="sm" fs="italic" c="ink.7" lineClamp={2} maw={230}>
              “{row.notes}”
            </Text>
          </Tooltip>
        ) : (
          <Text fz="sm" c="dimmed">
            —
          </Text>
        ),
    },
    {
      key: 'created_at',
      label: 'Sent',
      cardMeta: true,
      width: 150,
      render: (row) => (
        <Text fz="xs" c="dimmed">
          {formatDateTime(row.created_at)}
        </Text>
      ),
    },
    {
      key: 'inquiry',
      label: 'On the book as',
      width: 150,
      render: (row) => (
        <Button
          component={Link}
          to={`/inquiries/${row.inquiry_id}`}
          size="compact-sm"
          variant="light"
          rightSection={<IconArrowRight size={14} />}
        >
          #{row.inquiry_id}
        </Button>
      ),
    },
  ];

  return (
    <div className="page-fill">
      <PageHeader
        title="From parties"
        subtitle="Sent in by customers, suppliers and transporters through their own link. Each one is already on the book."
      />
      <div className="kpi-row">
        <KpiTile
          label="Enquiries"
          value={kpis.count}
          hint={kpis.countHint}
          accent="var(--brass)"
          spark={kpis.spark}
        />
        <KpiTile
          label="Volume"
          value={kpis.volume}
          hint="asked for"
          accent="var(--mantine-color-ink-7)"
        />
        <KpiTile
          label="Average rate"
          value={kpis.avg}
          hint={kpis.avgHint}
          accent="var(--demand)"
        />
        <KpiTile
          label="Prospects"
          value={kpis.prospects}
          hint={kpis.prospectsHint}
          accent="var(--supply)"
          tone={kpis.prospects ? 'attention' : undefined}
        />
      </div>
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
