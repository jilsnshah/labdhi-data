import { Button, SegmentedControl } from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useInquiries } from '@/api/hooks';
import type { InquiryType } from '@/api/types';
import { EntitySelect } from '@/components/EntitySelect';
import { FilterBar } from '@/components/FilterBar';
import { InquiryTable } from '@/components/InquiryTable';
import { PageHeader } from '@/components/PageHeader';
import { InquiryFormModal } from '@/components/modals/InquiryFormModal';
import { useListState } from '@/hooks/useListState';
import { toIsoDate } from '@/lib/format';

const COPY: Record<InquiryType, { title: string; subtitle: string; party: string }> = {
  CUSTOMER: {
    title: 'Customer inquiries',
    subtitle: 'What each customer wants, where, and the rate quoted.',
    party: 'CUSTOMER',
  },
  SUPPLIER: {
    title: 'Supplier inquiries',
    subtitle: 'What each supplier offered, from where, and at what rate.',
    party: 'SUPPLIER',
  },
  TRANSPORT: {
    title: 'Transport inquiries',
    subtitle: 'Routes and the freight each transporter quoted.',
    party: 'TRANSPORTER',
  },
};

export function InquiriesPage({ inquiryType }: { inquiryType: InquiryType }) {
  const list = useListState<{
    status?: string;
    party_id?: number;
    product_id?: number;
    created_from?: string;
    created_to?: string;
  }>({ status: 'ACTIVE' }, { sortBy: 'created_at', sortDir: 'desc' });
  const { data, isFetching } = useInquiries({ ...list.params, inquiry_type: inquiryType });
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
        {inquiryType !== 'TRANSPORT' && (
          <div style={{ width: 190 }}>
            <EntitySelect
              kind="product"
              placeholder="Any product"
              includeInactive
              value={list.filters.product_id ?? null}
              onChange={(value) => list.setFilter('product_id', value ?? undefined)}
            />
          </div>
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
