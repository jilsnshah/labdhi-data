import { Button, Select, Stack, Text } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useNotes } from '@/api/hooks';
import type { Note } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { EntitySelect } from '@/components/EntitySelect';
import { FilterBar } from '@/components/FilterBar';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { NoteFormModal } from '@/components/modals/NoteFormModal';
import { useListState } from '@/hooks/useListState';
import { formatDateTime } from '@/lib/format';

export function NotesPage() {
  const list = useListState<{ party_type?: string; party_id?: number }>(
    {},
    { sortBy: 'created_at', sortDir: 'desc' },
  );
  const { data, isFetching } = useNotes(list.params);
  const [editing, setEditing] = useState<Note | null>(null);
  const [opened, setOpened] = useState(false);

  const columns: Column<Note>[] = [
    {
      key: 'party',
      label: 'Party',
      render: (row) => (
        <Stack gap={0}>
          <Text fz="sm" fw={500} component={Link} to={`/parties/${row.party_id}`} c="accent.9">
            {row.party?.name ?? `#${row.party_id}`}
          </Text>
          <StatusBadge value={row.party?.party_type} size="xs" />
        </Stack>
      ),
    },
    {
      key: 'note',
      label: 'Note',
      render: (row) => (
        <Text fz="sm" className="wrap" maw={620}>
          {row.note}
        </Text>
      ),
    },
    {
      key: 'created',
      label: 'Added',
      sortable: true,
      render: (row) => (
        <Stack gap={0}>
          <Text fz="xs">{formatDateTime(row.created_at)}</Text>
          <Text fz="xs" c="dimmed">
            {row.creator?.name}
          </Text>
        </Stack>
      ),
    },
  ];

  return (
    <div className="page-fill">
      <PageHeader
        eyebrow="Relationships"
        title="Notes"
        subtitle="Business context that is not an activity - kept separate from system audit logs."
        actions={
          <Button
            leftSection={<IconPlus size={14} />}
            onClick={() => {
              setEditing(null);
              setOpened(true);
            }}
          >
            New note
          </Button>
        }
      />
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Search note text or party"
        onReset={list.resetFilters}
      >
        <Select
          w={168}
          placeholder="Any party type"
          clearable
          data={[
            { value: 'CUSTOMER', label: 'Customers' },
            { value: 'SUPPLIER', label: 'Suppliers' },
            { value: 'TRANSPORTER', label: 'Transporters' },
          ]}
          value={list.filters.party_type ?? null}
          onChange={(value) => list.setFilter('party_type', value ?? undefined)}
        />
        <div style={{ width: 200 }}>
          <EntitySelect
            kind="party"
            placeholder="Any party"
            includeInactive
            filters={{ party_type: list.filters.party_type }}
            value={list.filters.party_id ?? null}
            onChange={(value) => list.setFilter('party_id', value ?? undefined)}
          />
        </div>
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
        onRowClick={(row) => {
          setEditing(row);
          setOpened(true);
        }}
        emptyMessage="No notes match these filters"
        emptyHint="Notes capture context that is not an activity."
      />
      {opened && (
        <NoteFormModal
          key={editing?.id ?? 'new'}
          record={editing}
          onClose={() => setOpened(false)}
        />
      )}
    </div>
  );
}
