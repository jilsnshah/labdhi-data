import {
  Badge,
  Button,
  Divider,
  Drawer,
  Group,
  Modal,
  Stack,
  Switch,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '@/api/client';
import {
  useApiMutation,
  useProductCustomers,
  useProductSuppliers,
  useProducts,
} from '@/api/hooks';
import type { Product } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { EntityMultiSelect, EntitySelect } from '@/components/EntitySelect';
import { FilterBar, StatusFilter } from '@/components/FilterBar';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { Field } from '@/components/ui';
import { useListState } from '@/hooks/useListState';

interface Filters extends Record<string, unknown> {
  status?: string;
  material_id?: number;
  grade_id?: number;
  manufacturer_id?: number;
  application_id?: number;
}

export function ProductsPage() {
  const list = useListState<Filters>({}, { sortBy: 'display_name', sortDir: 'asc' });
  const { data, isFetching } = useProducts(list.params);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [viewing, setViewing] = useState<Product | null>(null);

  const columns: Column<Product>[] = [
    {
      key: 'display_name',
      label: 'Product',
      sortable: true,
      render: (row) => (
        <Stack gap={0}>
          <Text fw={500}>{row.display_name}</Text>
          <Text fz="xs" c="dimmed">
            #{row.id}
          </Text>
        </Stack>
      ),
    },
    { key: 'material', label: 'Material', render: (row) => <Text fz="sm">{row.material.name}</Text> },
    { key: 'grade', label: 'Grade', render: (row) => <Text fz="sm">{row.grade.name}</Text> },
    {
      key: 'manufacturer',
      label: 'Manufacturer',
      render: (row) => <Text fz="sm">{row.manufacturer.name}</Text>,
    },
    {
      key: 'applications',
      label: 'Applications',
      render: (row) => (
        <Group gap={4}>
          {row.applications.length === 0 && (
            <Text fz="xs" c="dimmed">
              -
            </Text>
          )}
          {row.applications.map((application) => (
            <Badge key={application.id} size="xs" variant="light" color="ink">
              {application.name}
            </Badge>
          ))}
        </Group>
      ),
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge value={row.status} /> },
  ];

  return (
    <div className="page-fill">
      <PageHeader
        eyebrow="Master data"
        title="Products"
        subtitle="A product is one material + grade + manufacturer, with its own stable id."
        actions={
          <Button
            leftSection={<IconPlus size={14} />}
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            New product
          </Button>
        }
      />
      <FilterBar
        q={list.q}
        onQChange={list.setQ}
        placeholder="Search product, material, grade, manufacturer"
        onReset={list.resetFilters}
      >
        <div style={{ width: 170 }}>
          <EntitySelect
            kind="material"
            placeholder="Any material"
            value={list.filters.material_id ?? null}
            onChange={(value) => {
              list.setFilter('material_id', value ?? undefined);
              list.setFilter('grade_id', undefined);
            }}
          />
        </div>
        <div style={{ width: 160 }}>
          <EntitySelect
            kind="grade"
            placeholder="Any grade"
            filters={{ material_id: list.filters.material_id }}
            value={list.filters.grade_id ?? null}
            onChange={(value) => list.setFilter('grade_id', value ?? undefined)}
          />
        </div>
        <div style={{ width: 180 }}>
          <EntitySelect
            kind="manufacturer"
            placeholder="Any manufacturer"
            value={list.filters.manufacturer_id ?? null}
            onChange={(value) => list.setFilter('manufacturer_id', value ?? undefined)}
          />
        </div>
        <div style={{ width: 180 }}>
          <EntitySelect
            kind="application"
            placeholder="Any application"
            value={list.filters.application_id ?? null}
            onChange={(value) => list.setFilter('application_id', value ?? undefined)}
          />
        </div>
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
        onRowClick={setViewing}
        emptyMessage="No products match these filters"
      />

      {formOpen && (
        <ProductModal
          key={editing?.id ?? 'new'}
          record={editing}
          onClose={() => setFormOpen(false)}
        />
      )}

      <ProductDrawer
        product={viewing}
        onClose={() => setViewing(null)}
        onEdit={(product) => {
          setViewing(null);
          setEditing(product);
          setFormOpen(true);
        }}
      />
    </div>
  );
}

function ProductModal({ record, onClose }: { record: Product | null; onClose: () => void }) {
  const [materialId, setMaterialId] = useState<number | null>(record?.material_id ?? null);
  const [gradeId, setGradeId] = useState<number | null>(record?.grade_id ?? null);
  const [manufacturerId, setManufacturerId] = useState<number | null>(
    record?.manufacturer_id ?? null,
  );
  const [applicationIds, setApplicationIds] = useState<number[]>(
    record?.applications.map((application) => application.id) ?? [],
  );
  const [displayName, setDisplayName] = useState(record?.display_name ?? '');
  const [description, setDescription] = useState(record?.description ?? '');
  const [active, setActive] = useState((record?.status ?? 'ACTIVE') === 'ACTIVE');

  const save = useApiMutation(
    (body: Record<string, unknown>) =>
      record ? api.patch(`/products/${record.id}`, body) : api.post('/products', body),
    { successMessage: `Product ${record ? 'updated' : 'created'}` },
  );

  const submit = async () => {
    await save.mutateAsync({
      material_id: materialId,
      grade_id: gradeId,
      manufacturer_id: manufacturerId,
      application_ids: applicationIds,
      display_name: displayName.trim() || null,
      description: description.trim() || null,
      ...(record ? { status: active ? 'ACTIVE' : 'INACTIVE' } : {}),
    });
    onClose();
  };

  const valid = materialId && gradeId && manufacturerId;

  return (
    <Modal
      opened
      onClose={onClose}
      title={record ? `Product #${record.id}` : 'New product'}
      size="lg"
    >
      <Stack gap="md">
        <EntitySelect
          kind="material"
          label="Material"
          required
          value={materialId}
          onChange={(value) => {
            setMaterialId(value);
            setGradeId(null);
          }}
          initialLabel={record?.material.name}
        />
        <EntitySelect
          kind="grade"
          label="Grade"
          required
          description="Only grades of the selected material are listed."
          filters={{ material_id: materialId ?? undefined }}
          disabled={!materialId}
          value={gradeId}
          onChange={setGradeId}
          initialLabel={record?.grade.name}
        />
        <EntitySelect
          kind="manufacturer"
          label="Manufacturer"
          required
          value={manufacturerId}
          onChange={setManufacturerId}
          initialLabel={record?.manufacturer.name}
        />
        <Divider
          label="Where it is used"
          labelPosition="left"
          styles={{ label: { fontSize: 11, fontWeight: 700, letterSpacing: '0.06em' } }}
        />
        <EntityMultiSelect
          kind="application"
          label="Applications"
          description="Where this product is used. A product can have several."
          value={applicationIds}
          onChange={setApplicationIds}
          initialOptions={
            record?.applications.map((application) => ({
              id: application.id,
              label: application.name,
            })) ?? []
          }
        />
        <TextInput
          label="Display name"
          placeholder="Generated from manufacturer + material + grade when left empty"
          value={displayName}
          onChange={(event) => setDisplayName(event.currentTarget.value)}
        />
        <Textarea
          label="Description"
          autosize
          minRows={2}
          value={description}
          onChange={(event) => setDescription(event.currentTarget.value)}
        />
        {record && (
          <Switch
            label="Active"
            checked={active}
            onChange={(event) => setActive(event.currentTarget.checked)}
          />
        )}
        <Group justify="flex-end" mt="sm">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={save.isPending} disabled={!valid}>
            {record ? 'Save product' : 'Create product'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function ProductDrawer({
  product,
  onClose,
  onEdit,
}: {
  product: Product | null;
  onClose: () => void;
  onEdit: (product: Product) => void;
}) {
  const { data: suppliers } = useProductSuppliers(product?.id);
  const { data: customers } = useProductCustomers(product?.id);

  return (
    <Drawer
      opened={Boolean(product)}
      onClose={onClose}
      position="right"
      size="md"
      title={product?.display_name}
    >
      {product && (
        <Stack gap="md">
          <Group gap="xs">
            <StatusBadge value={product.status} />
            <Badge variant="default" size="sm">
              #{product.id}
            </Badge>
            <Button size="xs" variant="light" onClick={() => onEdit(product)}>
              Edit
            </Button>
          </Group>

          <Stack gap={4}>
            <Field label="Material" value={product.material.name} />
            <Field label="Grade" value={product.grade.name} />
            <Field label="Manufacturer" value={product.manufacturer.name} />
            <Field
              label="Applications"
              value={product.applications.map((a) => a.name).join(', ') || '-'}
            />
            {product.description && <Field label="Notes" value={product.description} />}
          </Stack>

          <Divider />
          <div>
            <Title order={6} mb="xs">
              Suppliers who can provide this
            </Title>
            <Stack gap={4}>
              {(suppliers ?? []).length === 0 && (
                <Text fz="sm" c="dimmed">
                  No supplier is linked to this product yet.
                </Text>
              )}
              {(suppliers ?? []).map((row) => (
                <Group key={row.party_id} justify="space-between">
                  <Text fz="sm" component={Link} to={`/parties/${row.party_id}`} c="accent.9">
                    {row.party_name}
                  </Text>
                  <Text fz="xs" c="dimmed">
                    {row.city ?? ''} {row.phone ?? ''}
                  </Text>
                </Group>
              ))}
            </Stack>
          </div>

          <Divider />
          <div>
            <Title order={6} mb="xs">
              Customers buying or interested
            </Title>
            <Stack gap={4}>
              {(customers ?? []).length === 0 && (
                <Text fz="sm" c="dimmed">
                  No customer is linked to this product yet.
                </Text>
              )}
              {(customers ?? []).map((row) => (
                <Group key={row.party_id} justify="space-between">
                  <Text fz="sm" component={Link} to={`/parties/${row.party_id}`} c="accent.9">
                    {row.party_name}
                  </Text>
                  <Badge size="xs" variant="default">
                    {row.relationship_type}
                  </Badge>
                </Group>
              ))}
            </Stack>
          </div>
        </Stack>
      )}
    </Drawer>
  );
}
