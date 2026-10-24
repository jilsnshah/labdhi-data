import { Badge, Button, Code, Group, Select, Stack, Table, Tabs, Text } from '@mantine/core';
import { IconKey, IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useAuditLogs, useUsers } from '@/api/hooks';
import type { User } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { Field, SectionCard } from '@/components/ui';
import { SetPasswordModal } from '@/components/modals/SetPasswordModal';
import { UserFormModal } from '@/components/modals/UserFormModal';
import { useAuth } from '@/lib/auth';
import { useListState } from '@/hooks/useListState';
import { formatDateTime, humanize } from '@/lib/format';

export function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  return (
    <div className="page-fill">
      <PageHeader
        title="Settings"
        subtitle="Your account, the people who use the system, and what they changed."
      />
      <Tabs defaultValue="profile" className="work-tabs">
        <Tabs.List mb="md">
          <Tabs.Tab value="profile">Profile</Tabs.Tab>
          <Tabs.Tab value="users">Users</Tabs.Tab>
          {isAdmin && <Tabs.Tab value="audit">Audit log</Tabs.Tab>}
        </Tabs.List>
        <Tabs.Panel value="profile">
          <SectionCard title="Signed in as" description="Your desk account">
            <Stack gap="sm" maw={460}>
              <Field label="Name" value={user?.name ?? '—'} />
              <Field label="Email" value={user?.email ?? '—'} />
              <Field
                label="Role"
                value={
                  <Group gap="xs">
                    <Badge variant="default">{user?.role}</Badge>
                    <StatusBadge value={user?.status} />
                  </Group>
                }
              />
            </Stack>
          </SectionCard>
        </Tabs.Panel>
        <Tabs.Panel value="users">
          <UsersTab isAdmin={isAdmin} />
        </Tabs.Panel>
        {isAdmin && (
          <Tabs.Panel value="audit">
            <AuditTab />
          </Tabs.Panel>
        )}
      </Tabs>
    </div>
  );
}

function UsersTab({ isAdmin }: { isAdmin: boolean }) {
  const list = useListState<{ status?: string }>({}, { sortBy: 'name', sortDir: 'asc' });
  const { data, isFetching } = useUsers(list.params);
  const [editing, setEditing] = useState<User | null>(null);
  const [opened, setOpened] = useState(false);
  const [passwordFor, setPasswordFor] = useState<User | null>(null);

  const columns: Column<User>[] = [
    {
      key: 'name',
      label: 'Name',
      sortable: true,
      render: (row) => <Text fw={500}>{row.name}</Text>,
    },
    {
      key: 'email',
      label: 'Email',
      sortable: true,
      render: (row) => <Text fz="sm">{row.email}</Text>,
    },
    { key: 'phone', label: 'Phone', render: (row) => <Text fz="sm">{row.phone || '-'}</Text> },
    {
      key: 'role',
      label: 'Role',
      render: (row) => (
        <Badge variant="default" size="sm">
          {row.role}
        </Badge>
      ),
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge value={row.status} /> },
    ...(isAdmin
      ? [
          {
            key: 'password',
            label: 'Password',
            width: 130,
            render: (row: User) => (
              <Button
                size="compact-xs"
                variant="subtle"
                leftSection={<IconKey size={13} />}
                onClick={(event) => {
                  event.stopPropagation();
                  setPasswordFor(row);
                }}
              >
                Set password
              </Button>
            ),
          },
        ]
      : []),
  ];

  return (
    <SectionCard
      title="Users"
      description="Desk accounts and field accounts"
      dense
      actions={
        isAdmin ? (
          <Button
            size="compact-sm"
            leftSection={<IconPlus size={14} />}
            onClick={() => {
              setEditing(null);
              setOpened(true);
            }}
          >
            New user
          </Button>
        ) : undefined
      }
    >
      <DataTable
        framed={false}
        fill
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
        onRowClick={
          isAdmin
            ? (row) => {
                setEditing(row);
                setOpened(true);
              }
            : undefined
        }
      />
      {passwordFor && <SetPasswordModal user={passwordFor} onClose={() => setPasswordFor(null)} />}
      {opened && (
        <UserFormModal
          key={editing?.id ?? 'new'}
          record={editing}
          onClose={() => setOpened(false)}
        />
      )}
    </SectionCard>
  );
}

function AuditTab() {
  const list = useListState<{ entity_type?: string }>(
    {},
    { sortBy: 'created_at', sortDir: 'desc' },
  );
  const { data, isFetching } = useAuditLogs(list.params);

  return (
    <SectionCard
      title="System audit trail"
      description="Who changed what. Kept separate from business notes."
      actions={
        <Select
          w={180}
          placeholder="Any entity"
          clearable
          data={['inquiry', 'party', 'product', 'activity', 'note', 'material', 'grade', 'user']}
          value={list.filters.entity_type ?? null}
          onChange={(value) => list.setFilter('entity_type', value ?? undefined)}
        />
      }
    >
      <Table className="data-table" fz="sm" verticalSpacing={8}>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>When</Table.Th>
            <Table.Th>User</Table.Th>
            <Table.Th>Entity</Table.Th>
            <Table.Th>Action</Table.Th>
            <Table.Th>Change</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(data?.items ?? []).map((row) => (
            <Table.Tr key={row.id}>
              <Table.Td>{formatDateTime(row.created_at)}</Table.Td>
              <Table.Td>{row.user?.name ?? '-'}</Table.Td>
              <Table.Td>
                {humanize(row.entity_type)} #{row.entity_id}
              </Table.Td>
              <Table.Td>
                <Badge size="xs" variant="default">
                  {humanize(row.action)}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Code fz="xs">
                  {row.old_value ? `${JSON.stringify(row.old_value)} → ` : ''}
                  {JSON.stringify(row.new_value ?? {})}
                </Code>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      <Group justify="space-between" mt="md">
        <Text fz="xs" c="dimmed">
          {data?.total ?? 0} entries {isFetching ? '· loading' : ''}
        </Text>
        <Group gap="xs">
          <Button
            size="compact-xs"
            variant="default"
            disabled={list.page <= 1}
            onClick={() => list.setPage(list.page - 1)}
          >
            Previous
          </Button>
          <Button
            size="compact-xs"
            variant="default"
            disabled={(data?.pages ?? 1) <= list.page}
            onClick={() => list.setPage(list.page + 1)}
          >
            Next
          </Button>
        </Group>
      </Group>
    </SectionCard>
  );
}
