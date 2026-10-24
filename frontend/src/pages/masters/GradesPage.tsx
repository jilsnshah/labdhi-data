import { Button, Text } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useGrades } from '@/api/hooks';
import type { Grade } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { EntitySelect } from '@/components/EntitySelect';
import { FilterBar, StatusFilter } from '@/components/FilterBar';
import { MasterFormModal } from '@/components/MasterFormModal';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { useListState } from '@/hooks/useListState';

export function GradesPage() {
  const list = useListState<{ status?: string; material_id?: number }>(
    {},
    { sortBy: 'name', sortDir: 'asc' },
  );
  const { data, isFetching } = useGrades(list.params);
  const [editing, setEditing] = useState<Grade | null>(null);
  const [opened, setOpened] = useState(false);

  const open = (record: Grade | null) => {
    setEditing(record);
    setOpened(true);
  };

  const columns: Column<Grade>[] = [
    {
      key: 'name',
      label: 'Grade',
      sortable: true,
      render: (row) => <Text fw={500}>{row.name}</Text>,
    },
    {
      key: 'material',
      label: 'Material',
      render: (row) => <Text fz="sm">{row.material.name}</Text>,
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
        title="Grades"
        subtitle="Grades are scoped to a material, so invalid material/grade pairs cannot be created."
        actions={
          <Button leftSection={<IconPlus size={14} />} onClick={() => open(null)}>
            New grade
          </Button>
        }
      />
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Search grades"
        onReset={list.resetFilters}
      >
        <EntitySelect
          className="field-lg"
          kind="material"
          placeholder="Any material"
          value={list.filters.material_id ?? null}
          onChange={(value) => list.setFilter('material_id', value ?? undefined)}
        />
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
        emptyMessage="No grades match these filters"
      />
      {opened && (
        <MasterFormModal
          key={editing?.id ?? 'new'}
          opened={opened}
          onClose={() => setOpened(false)}
          record={editing}
          path="/grades"
          entityLabel="Grade"
          withMaterial
          defaultMaterialId={list.filters.material_id ?? null}
        />
      )}
    </div>
  );
}
