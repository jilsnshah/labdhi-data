import { Badge, Button, SegmentedControl, Select } from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { IconAdjustmentsHorizontal, IconPlus } from '@tabler/icons-react';
import { useMemo, useState } from 'react';

import { useInquiries, useLocationAreas } from '@/api/hooks';
import type { InquiryListItem, InquiryType } from '@/api/types';
import { EntitySelect } from '@/components/EntitySelect';
import { FilterBar } from '@/components/FilterBar';
import { InquiryTable } from '@/components/InquiryTable';
import { KpiTile } from '@/components/market/Visuals';
import { PageHeader } from '@/components/PageHeader';
import { InquiryFormModal } from '@/components/modals/InquiryFormModal';
import { useListState } from '@/hooks/useListState';
import { formatMoney, toIsoDate } from '@/lib/format';
import { dailyCounts, fmtRate, fmtTonnes } from '@/lib/market';

const COPY: Record<
  InquiryType,
  { title: string; subtitle: string; party: string; accent: string }
> = {
  CUSTOMER: {
    title: 'Customer inquiries',
    subtitle: 'What each customer wants, where, and the rate quoted.',
    party: 'CUSTOMER',
    accent: 'var(--demand)',
  },
  SUPPLIER: {
    title: 'Supplier inquiries',
    subtitle: 'What each supplier offered, from where, and at what rate.',
    party: 'SUPPLIER',
    accent: 'var(--supply)',
  },
  TRANSPORT: {
    title: 'Transport inquiries',
    subtitle: 'Routes and the freight each transporter quoted.',
    party: 'TRANSPORTER',
    accent: 'var(--mantine-color-ink-7)',
  },
};

export function InquiriesPage({ inquiryType }: { inquiryType: InquiryType }) {
  const list = useListState<{
    status?: string;
    party_id?: number;
    area?: string;
    product_id?: number;
    material_id?: number;
    grade_id?: number;
    manufacturer_id?: number;
    application_id?: number;
    created_from?: string;
    created_to?: string;
  }>({ status: 'ACTIVE' }, { sortBy: 'created_at', sortDir: 'desc' });
  const { data: areas } = useLocationAreas();
  const productFilterCount = [
    list.filters.product_id,
    list.filters.material_id,
    list.filters.grade_id,
    list.filters.manufacturer_id,
    list.filters.application_id,
  ].filter((value) => value !== undefined && value !== null).length;
  const [productOpen, setProductOpen] = useState(false);
  const { data, isFetching } = useInquiries({ ...list.params, inquiry_type: inquiryType });
  // The KPI row summarises everything the current filters match, not just this page.
  const { data: slice } = useInquiries({
    ...list.params,
    inquiry_type: inquiryType,
    page: 1,
    page_size: 200,
  });
  const kpis = useMemo(() => summarise(slice?.items ?? [], inquiryType), [slice, inquiryType]);
  const [createOpen, setCreateOpen] = useState(false);
  const [range, setRange] = useState<[string | null, string | null]>([null, null]);

  const copy = COPY[inquiryType];

  return (
    <div className="page-fill">
      <PageHeader
        eyebrow="Inquiries"
        title={copy.title}
        subtitle={copy.subtitle}
        actions={
          <Button leftSection={<IconPlus size={14} />} onClick={() => setCreateOpen(true)}>
            New {copy.title.split(' ')[0].toLowerCase()} inquiry
          </Button>
        }
      />
      <div className="kpi-row">
        <KpiTile
          label={inquiryType === 'TRANSPORT' ? 'Quotes' : 'Inquiries'}
          value={kpis.count}
          hint={kpis.countHint}
          accent={copy.accent}
          spark={kpis.spark}
        />
        <KpiTile label="Volume" value={kpis.volume} hint={kpis.volumeHint} accent={copy.accent} />
        <KpiTile label={kpis.avgLabel} value={kpis.avg} hint={kpis.avgHint} accent={copy.accent} />
        <KpiTile
          label={kpis.bestLabel}
          value={kpis.best}
          hint={kpis.bestHint}
          accent="var(--brass)"
        />
      </div>
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder={
          inquiryType === 'TRANSPORT' ? 'Inquiry id or transporter' : 'Inquiry id, party or product'
        }
        onReset={() => {
          list.resetFilters();
          setRange([null, null]);
        }}
      >
        <SegmentedControl
          size="xs"
          value={list.filters.status ?? 'ALL'}
          onChange={(value) => list.setFilter('status', value === 'ALL' ? undefined : value)}
          data={[
            { label: 'Active', value: 'ACTIVE' },
            { label: 'Closed', value: 'CLOSED' },
            { label: 'All', value: 'ALL' },
          ]}
        />
        <div style={{ width: 190 }}>
          <EntitySelect
            kind="party"
            placeholder={`Any ${copy.party.toLowerCase()}`}
            filters={{ party_type: copy.party }}
            includeInactive
            value={list.filters.party_id ?? null}
            onChange={(value) => list.setFilter('party_id', value ?? undefined)}
          />
        </div>
        <Select
          w={170}
          placeholder="Any area"
          data={areas ?? []}
          value={list.filters.area ?? null}
          onChange={(value) => list.setFilter('area', value ?? undefined)}
          searchable
          clearable
        />
        {inquiryType !== 'TRANSPORT' && (
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
        {inquiryType !== 'TRANSPORT' && productOpen && (
          // What the product is: these narrow through the inquiry's product,
          // so they do not apply to transport quotes.
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
          placeholder="Created between"
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
      <InquiryTable
        inquiryType={inquiryType}
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
        emptyMessage="No inquiries match these filters"
        emptyHint="Clear the filters, or create the first one with “New inquiry”."
      />
      {createOpen && (
        <InquiryFormModal
          opened
          onClose={() => setCreateOpen(false)}
          defaultType={inquiryType}
          lockType
        />
      )}
    </div>
  );
}

/** Headline figures for whatever the filters currently match. */
function summarise(rows: InquiryListItem[], type: InquiryType) {
  const tonnes = rows.reduce((total, row) => {
    const quantity = Number(row.quantity ?? 0);
    if (row.unit === 'MT') return total + quantity;
    if (row.unit === 'KG') return total + quantity / 1000;
    return total;
  }, 0);
  const active = rows.filter((row) => row.status === 'ACTIVE').length;
  const spark = dailyCounts(rows.map((row) => row.created_at));
  const capped = rows.length >= 200 ? ' (latest 200)' : '';

  if (type === 'TRANSPORT') {
    const priced = rows.filter((row) => row.price);
    const prices = priced.map((row) => Number(row.price));
    const cheapest = priced.reduce<InquiryListItem | null>(
      (best, row) => (!best || Number(row.price) < Number(best.price) ? row : best),
      null,
    );
    return {
      count: rows.length,
      countHint: `${active} active${capped}`,
      spark,
      volume: fmtTonnes(tonnes),
      volumeHint: 'to be moved',
      avgLabel: 'Average freight',
      avg: prices.length ? formatMoney(prices.reduce((a, b) => a + b, 0) / prices.length) : '—',
      avgHint: `${prices.length} priced quote${prices.length === 1 ? '' : 's'}`,
      bestLabel: 'Lowest freight',
      best: cheapest ? formatMoney(cheapest.price) : '—',
      bestHint: cheapest ? cheapest.party_name : 'No price recorded',
    };
  }

  const rated = rows.filter((row) => row.rate);
  const rates = rated.map((row) => Number(row.rate));
  // Suppliers: the cheapest offer wins. Customers: the best price we can get.
  const pick = (a: number, b: number) => (type === 'SUPPLIER' ? a < b : a > b);
  const best = rated.reduce<InquiryListItem | null>(
    (current, row) => (!current || pick(Number(row.rate), Number(current.rate)) ? row : current),
    null,
  );
  return {
    count: rows.length,
    countHint: `${active} active${capped}`,
    spark,
    volume: fmtTonnes(tonnes),
    volumeHint: type === 'SUPPLIER' ? 'on offer' : 'wanted',
    avgLabel: 'Average rate',
    avg: rates.length ? `${fmtRate(rates.reduce((a, b) => a + b, 0) / rates.length)}` : '—',
    avgHint: `per kg · ${rates.length} rated`,
    bestLabel: type === 'SUPPLIER' ? 'Cheapest offer' : 'Best price',
    best: best ? fmtRate(Number(best.rate)) : '—',
    bestHint: best ? `${best.party_name} · ${best.product_name}` : 'No rate recorded',
  };
}
