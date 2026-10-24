import { Badge, Button, Text } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useManufacturers } from '@/api/hooks';
import type { Manufacturer } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { FilterBar, StatusFilter } from '@/components/FilterBar';
import { MasterFormModal } from '@/components/MasterFormModal';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { useListState } from '@/hooks/useListState';

export function ManufacturersPage() {
  const list = useListState<{ status?: string }>({}, { sortBy: 'name', sortDir: 'asc' });
  const { data, isFetching } = useManufacturers(list.params);
  const [editing, setEditing] = useState<Manufacturer | null>(null);
  const [opened, setOpened] = useState(false);

  const open = (record: Manufacturer | null) => {
    setEditing(record);
    setOpened(true);
  };

  const columns: Column<Manufacturer>[] = [
    {
      key: 'name',
      label: 'Manufacturer',
      sortable: true,
      render: (row) => <Text fw={500}>{row.name}</Text>,
    },
    {
      key: 'code',
      label: 'Code',
      sortable: true,
      render: (row) =>
        row.code ? (
          <Badge variant="default" size="sm">
            {row.code}
          </Badge>
        ) : (
          <Text fz="sm" c="dimmed">
            -
          </Text>
        ),
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
        title="Manufacturers"
        subtitle="Who produces the material. A manufacturer is not the same as a supplier."
        actions={
          <Button leftSection={<IconPlus size={14} />} onClick={() => open(null)}>
            New manufacturer
          </Button>
        }
      />
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Search name or code"
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
        emptyMessage="No manufacturers match these filters"
      />
      {opened && (
        <MasterFormModal
          key={editing?.id ?? 'new'}
          opened={opened}
          onClose={() => setOpened(false)}
          record={editing}
          path="/manufacturers"
          entityLabel="Manufacturer"
          withCode
        />
      )}
    </div>
  );
}
