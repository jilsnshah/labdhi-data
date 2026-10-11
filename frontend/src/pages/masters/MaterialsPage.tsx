import { Button, Text } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useMaterials } from '@/api/hooks';
import type { Material } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { FilterBar, StatusFilter } from '@/components/FilterBar';
import { MasterFormModal } from '@/components/MasterFormModal';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { useListState } from '@/hooks/useListState';
import { formatDate } from '@/lib/format';

export function MaterialsPage() {
  const list = useListState<{ status?: string }>({}, { sortBy: 'name', sortDir: 'asc' });
  const { data, isFetching } = useMaterials(list.params);
  const [editing, setEditing] = useState<Material | null>(null);
  const [opened, setOpened] = useState(false);

  const open = (record: Material | null) => {
    setEditing(record);
    setOpened(true);
  };

  const columns: Column<Material>[] = [
    {
      key: 'name',
      label: 'Material',
      sortable: true,
      render: (row) => <Text fw={500}>{row.name}</Text>,
    },
    { key: 'grades', label: 'Grades', render: (row) => <Text fz="sm">{row.grade_count ?? 0}</Text> },
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
    {
      key: 'created_at',
      label: 'Added',
      sortable: true,
      render: (row) => (
        <Text fz="xs" c="dimmed">
          {formatDate(row.created_at)}
        </Text>
      ),
    },
  ];

  return (
    <div className="page-fill">
      <PageHeader
        eyebrow="Master data"
        title="Materials"
        subtitle="Base polymers traded by the business. Every grade belongs to a material."
        actions={
          <Button leftSection={<IconPlus size={14} />} onClick={() => open(null)}>
            New material
          </Button>
        }
      />
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Search materials"
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
        emptyMessage="No materials match these filters"
      />
      {opened && (
        <MasterFormModal
          key={editing?.id ?? 'new'}
          opened={opened}
          onClose={() => setOpened(false)}
          record={editing}
          path="/materials"
          entityLabel="Material"
        />
      )}
    </div>
  );
}
