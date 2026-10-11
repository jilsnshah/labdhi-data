import { Button, Text } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useApplications } from '@/api/hooks';
import type { Application } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { FilterBar, StatusFilter } from '@/components/FilterBar';
import { MasterFormModal } from '@/components/MasterFormModal';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { useListState } from '@/hooks/useListState';

export function ApplicationsPage() {
  const list = useListState<{ status?: string }>({}, { sortBy: 'name', sortDir: 'asc' });
  const { data, isFetching } = useApplications(list.params);
  const [editing, setEditing] = useState<Application | null>(null);
  const [opened, setOpened] = useState(false);

  const open = (record: Application | null) => {
    setEditing(record);
    setOpened(true);
  };

  const columns: Column<Application>[] = [
    {
      key: 'name',
      label: 'Application',
      sortable: true,
      render: (row) => <Text fw={500}>{row.name}</Text>,
    },
    {
      key: 'description',
      label: 'Description',
      render: (row) => (
        <Text fz="sm" c="dimmed" lineClamp={1}>
          {row.description || '-'}
        </Text>
      ),
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge value={row.status} /> },
  ];

  return (
    <div className="page-fill">
      <PageHeader
        eyebrow="Master data"
        title="Applications"
        subtitle="Where a product is used - pipes, windows, profiles, moulding, packaging."
        actions={
          <Button leftSection={<IconPlus size={14} />} onClick={() => open(null)}>
            New application
          </Button>
        }
      />
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Search applications"
        onReset={list.resetFilters}
      >
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
        onRowClick={open}
        emptyMessage="No applications match these filters"
      />
      {opened && (
        <MasterFormModal
          key={editing?.id ?? 'new'}
          opened={opened}
          onClose={() => setOpened(false)}
          record={editing}
          path="/applications"
          entityLabel="Application"
        />
      )}
    </div>
  );
}
