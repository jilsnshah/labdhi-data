import { Button, MultiSelect, Select, Switch } from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useActivities } from '@/api/hooks';
import { ActivityTable } from '@/components/ActivityTable';
import { EntitySelect } from '@/components/EntitySelect';
import { FilterBar } from '@/components/FilterBar';
import { PageHeader } from '@/components/PageHeader';
import { ActivityFormModal } from '@/components/modals/ActivityModals';
import { useListState } from '@/hooks/useListState';
import { humanize, toIsoDate } from '@/lib/format';

const TYPES = ['CALL', 'WHATSAPP', 'SMS', 'VISIT', 'EMAIL', 'MEETING'];
const STATUSES = ['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'];

type Scope = 'today' | 'upcoming' | 'history';

const COPY: Record<Scope, { title: string; subtitle: string }> = {
  today: {
    title: "Today's activities",
    subtitle: 'Calls, messages and visits scheduled for today.',
  },
  upcoming: {
    title: 'Upcoming activities',
    subtitle: 'Scheduled follow-ups, including anything already overdue.',
  },
  history: {
    title: 'Activity history',
    subtitle: 'What was done, what came out of it and which follow-up it led to.',
  },
};

export function ActivitiesPage({ scope }: { scope: Scope }) {
  const list = useListState<{
    activity_type?: string;
    status?: string[];
    customer_id?: number;
    assigned_salesperson_id?: number;
    unassigned_only?: boolean;
    date_from?: string;
    date_to?: string;
  }>(
    {},
    {
      sortBy: scope === 'history' ? 'completed_at' : 'scheduled_at',
      sortDir: scope === 'history' ? 'desc' : 'asc',
    },
  );
  const { data, isFetching } = useActivities({ ...list.params, scope });
  const [createOpen, setCreateOpen] = useState(false);
  const [range, setRange] = useState<[string | null, string | null]>([null, null]);

  return (
    <div className="page-fill">
      <PageHeader
        title={COPY[scope].title}
        subtitle={COPY[scope].subtitle}
        actions={
          <Button leftSection={<IconPlus size={14} />} onClick={() => setCreateOpen(true)}>
            New activity
          </Button>
        }
      />
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Customer, subject, note or outcome"
        onReset={() => {
          list.resetFilters();
          setRange([null, null]);
        }}
      >
        <Select
          className="field-md"
          placeholder="Any type"
          clearable
          data={TYPES.map((value) => ({ value, label: humanize(value) }))}
          value={list.filters.activity_type ?? null}
          onChange={(value) => list.setFilter('activity_type', value ?? undefined)}
        />
        {scope === 'history' && (
          <MultiSelect
            className="field-lg"
            placeholder="Any status"
            data={STATUSES.map((value) => ({ value, label: humanize(value) }))}
            value={(list.filters.status as string[]) ?? []}
            onChange={(value) => list.setFilter('status', value.length ? value : undefined)}
            clearable
          />
        )}
        <EntitySelect
          className="field-lg"
          kind="party"
          placeholder="Any customer"
          filters={{ party_type: 'CUSTOMER' }}
          includeInactive
          value={list.filters.customer_id ?? null}
          onChange={(value) => list.setFilter('customer_id', value ?? undefined)}
        />
        <EntitySelect
          className="field-lg"
          kind="user"
          placeholder="Any salesperson"
          filters={{ role: 'SALESPERSON' }}
          includeInactive
          value={list.filters.assigned_salesperson_id ?? null}
          onChange={(value) => {
            list.setFilter('assigned_salesperson_id', value ?? undefined);
            if (value) list.setFilter('unassigned_only', undefined);
          }}
        />
        <Switch
          label="Unassigned"
          checked={Boolean(list.filters.unassigned_only)}
          onChange={(event) => {
            list.setFilter('unassigned_only', event.currentTarget.checked ? true : undefined);
            if (event.currentTarget.checked) {
              list.setFilter('assigned_salesperson_id', undefined);
            }
          }}
        />
        <DatePickerInput
          type="range"
          className="field-lg"
          placeholder="Date range"
          valueFormat="DD MMM"
          clearable
          value={range}
          onChange={(value) => {
            const next = value as [string | null, string | null];
            setRange(next);
            list.setFilter('date_from', toIsoDate(next[0]));
            list.setFilter('date_to', toIsoDate(next[1]));
          }}
        />
      </FilterBar>
      <ActivityTable
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
        emptyMessage={
          scope === 'today'
            ? 'Nothing scheduled for today'
            : scope === 'upcoming'
              ? 'No upcoming activity'
              : 'No activity history yet'
        }
        emptyHint={
          scope === 'history'
            ? 'Completed and cancelled work lands here.'
            : 'Schedule a call or a visit and assign it to a salesperson.'
        }
      />
      {createOpen && <ActivityFormModal onClose={() => setCreateOpen(false)} />}
    </div>
  );
}
