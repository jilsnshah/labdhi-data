/** The field team: workload at a glance, one click into a person's day. */

import { Button, Drawer, Group, Stack, Switch, Tabs, Text } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { useActivities, useSalespeopleWorkload } from '@/api/hooks';
import type { SalespersonWorkload } from '@/api/types';
import { ActivityTable } from '@/components/ActivityTable';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { UserFormModal } from '@/components/modals/UserFormModal';

export function SalespeoplePage() {
  const [includeInactive, setIncludeInactive] = useState(false);
  const { data, isFetching } = useSalespeopleWorkload(includeInactive);
  const [selected, setSelected] = useState<SalespersonWorkload | null>(null);
  const [creating, setCreating] = useState(false);

  const columns: Column<SalespersonWorkload>[] = [
    {
      key: 'name',
      label: 'Salesperson',
      render: (row) => (
        <Stack gap={0}>
          <Text fz="sm" fw={550} c="ink.9">
            {row.name}
          </Text>
          <Text fz="xs" c="ink.5">
            {row.email}
            {row.phone ? ` · ${row.phone}` : ''}
          </Text>
        </Stack>
      ),
    },
    {
      key: 'today',
      label: 'Today',
      align: 'right',
      width: 110,
      render: (row) => (
        <Text fz="sm" className="mono-tight" c="ink.9">
          {row.today_pending}
          <Text component="span" c="ink.4">
            /{row.today_total}
          </Text>
        </Text>
      ),
    },
    {
      key: 'done',
      label: 'Completed',
      align: 'right',
      width: 110,
      render: (row) => (
        <Text fz="sm" className="mono-tight" c={row.today_completed ? 'ink.9' : 'ink.4'}>
          {row.today_completed}
        </Text>
      ),
    },
    {
      key: 'upcoming',
      label: 'Upcoming',
      align: 'right',
      width: 110,
      render: (row) => (
        <Text fz="sm" className="mono-tight" c={row.upcoming ? 'ink.9' : 'ink.4'}>
          {row.upcoming}
        </Text>
      ),
    },
    {
      key: 'overdue',
      label: 'Overdue',
      align: 'right',
      width: 110,
      render: (row) => (
        <Text
          fz="sm"
          fw={row.overdue ? 600 : 400}
          className="mono-tight"
          c={row.overdue ? 'rust.8' : 'ink.4'}
        >
          {row.overdue}
        </Text>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      width: 120,
      render: (row) => <StatusBadge value={row.status} />,
    },
  ];

  return (
    <div className="page-fill">
      <PageHeader
        title="Salespeople"
        subtitle="Field accounts. They only ever see the activities you assign to them."
        actions={
          <Group gap="md">
            <Switch
              label="Show inactive"
              checked={includeInactive}
              onChange={(event) => setIncludeInactive(event.currentTarget.checked)}
            />
            <Button leftSection={<IconPlus size={15} />} onClick={() => setCreating(true)}>
              New salesperson
            </Button>
          </Group>
        }
      />

      <DataTable
        columns={columns}
        rows={data ?? []}
        loading={isFetching}
        fill
        onRowClick={setSelected}
        emptyMessage="No salesperson accounts yet"
        emptyHint="Create one, then assign visits and calls from any activity form."
      />

      <SalespersonDrawer person={selected} onClose={() => setSelected(null)} />
      {creating && (
        <UserFormModal
          record={null}
          lockedRole="SALESPERSON"
          title="New salesperson"
          onClose={() => setCreating(false)}
        />
      )}
    </div>
  );
}

function SalespersonDrawer({
  person,
  onClose,
}: {
  person: SalespersonWorkload | null;
  onClose: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const today = useActivities(
    person ? { assigned_salesperson_id: person.id, scope: 'today', page_size: 50 } : {},
  );
  const upcoming = useActivities(
    person ? { assigned_salesperson_id: person.id, scope: 'upcoming', page_size: 50 } : {},
  );
  const history = useActivities(
    person ? { assigned_salesperson_id: person.id, scope: 'history', page_size: 50 } : {},
  );

  return (
    <Drawer
      opened={Boolean(person)}
      onClose={onClose}
      position="right"
      size="xl"
      title={person?.name}
    >
      {person && (
        <Stack gap="lg">
          <Group justify="space-between" align="center">
            <Group gap="md">
              <Text fz="sm" c="ink.6">
                {person.email}
                {person.phone ? ` · ${person.phone}` : ''}
              </Text>
              <StatusBadge value={person.status} />
            </Group>
            <Button size="compact-sm" variant="default" onClick={() => setEditing(true)}>
              Edit account
            </Button>
          </Group>

          <Tabs defaultValue="today" className="work-tabs">
            <Tabs.List mb="md">
              <Tabs.Tab value="today">Today ({person.today_total})</Tabs.Tab>
              <Tabs.Tab value="upcoming">Upcoming ({person.upcoming})</Tabs.Tab>
              <Tabs.Tab value="history">Completed</Tabs.Tab>
            </Tabs.List>
            <Tabs.Panel value="today">
              <ActivityTable
                rows={today.data?.items ?? []}
                loading={today.isFetching}
                showAssignee={false}
                emptyMessage="Nothing scheduled for today"
              />
            </Tabs.Panel>
            <Tabs.Panel value="upcoming">
              <ActivityTable
                rows={upcoming.data?.items ?? []}
                loading={upcoming.isFetching}
                showAssignee={false}
                emptyMessage="No upcoming work assigned"
              />
            </Tabs.Panel>
            <Tabs.Panel value="history">
              <ActivityTable
                rows={history.data?.items ?? []}
                loading={history.isFetching}
                showAssignee={false}
                emptyMessage="Nothing completed yet"
              />
            </Tabs.Panel>
          </Tabs>

          {editing && (
            <UserFormModal
              record={{
                id: person.id,
                name: person.name,
                email: person.email,
                phone: person.phone,
                role: 'SALESPERSON',
                status: person.status,
                created_at: '',
                updated_at: '',
              }}
              onClose={() => setEditing(false)}
            />
          )}
        </Stack>
      )}
    </Drawer>
  );
}
