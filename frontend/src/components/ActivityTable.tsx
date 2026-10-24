import { ActionIcon, Badge, Group, Stack, Text, Tooltip } from '@mantine/core';
import { IconCircleCheck, IconUserCheck } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { isFieldLogged, type Activity } from '@/api/types';
import { ActivityDetailDrawer } from '@/components/ActivityDetailDrawer';
import { DataTable } from '@/components/DataTable';
import type { Column, SortState } from '@/components/DataTable';
import { StatusBadge } from '@/components/StatusBadge';
import { AssignActivityModal, CompleteActivityModal } from '@/components/modals/ActivityModals';
import { dayLabel, formatDateTime, humanize, isOverdue, time } from '@/lib/format';

interface Props {
  rows: Activity[];
  total?: number;
  page?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  sort?: SortState;
  onSortChange?: (sort: SortState) => void;
  loading?: boolean;
  framed?: boolean;
  fill?: boolean;
  showCustomer?: boolean;
  showAssignee?: boolean;
  emptyMessage?: string;
  emptyHint?: string;
}

export function ActivityTable({
  rows,
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  sort,
  onSortChange,
  loading,
  framed = true,
  fill = false,
  showCustomer = true,
  showAssignee = true,
  emptyMessage = 'No activities found.',
  emptyHint,
}: Props) {
  const [completing, setCompleting] = useState<Activity | null>(null);
  const [assigning, setAssigning] = useState<Activity | null>(null);
  const [viewing, setViewing] = useState<number | null>(null);

  const columns: Column<Activity>[] = [
    {
      key: 'scheduled_at',
      label: 'When',
      sortable: true,
      width: 128,
      render: (row) => {
        const late = row.status === 'SCHEDULED' && isOverdue(row.scheduled_at);
        return (
          <Stack gap={0}>
            <Text fz="sm" fw={600} c={late ? 'red.7' : undefined} className="mono-tight">
              {time(row.scheduled_at)}
            </Text>
            <Text fz="xs" c={late ? 'red.6' : 'dimmed'}>
              {dayLabel(row.scheduled_at)}
            </Text>
          </Stack>
        );
      },
    },
    {
      key: 'what',
      label: 'Activity',
      render: (row) => (
        <Stack gap={2}>
          <Group gap={8} wrap="nowrap">
            {showCustomer && (
              <Text
                fz="sm"
                fw={550}
                component={Link}
                to={`/parties/${row.party_id}`}
                c="navy.7"
                truncate
                maw={180}
              >
                {row.party?.name ?? `#${row.party_id}`}
              </Text>
            )}
            {row.parent_activity_id && (
              <Text fz="xs" c="ink.5">
                follow-up
              </Text>
            )}
            {isFieldLogged(row) && (
              <Tooltip label="Logged by the salesperson from the field app">
                <Badge color="brass" variant="light" size="xs" radius="sm">
                  Field
                </Badge>
              </Tooltip>
            )}
          </Group>
          <Group gap={6} wrap="nowrap">
            <Text fz="sm" c="ink.5" truncate maw={300}>
              {humanize(row.activity_type).toLowerCase()} · {row.subject || row.note || '—'}
            </Text>
            {row.related_inquiry_id && (
              <Text
                fz="xs"
                component={Link}
                to={`/inquiries/${row.related_inquiry_id}`}
                c="navy.7"
                style={{ whiteSpace: 'nowrap' }}
                onClick={(event) => event.stopPropagation()}
              >
                #{row.related_inquiry_id}
              </Text>
            )}
          </Group>
        </Stack>
      ),
    },
    {
      key: 'outcome',
      label: 'Outcome',
      render: (row) =>
        row.outcome_code || row.outcome ? (
          <Stack gap={2} maw={280}>
            {row.outcome_code && <StatusBadge value={row.outcome_code} size="xs" />}
            {row.outcome && (
              <Text fz="xs" c="dimmed" lineClamp={2} className="wrap">
                {row.outcome}
              </Text>
            )}
          </Stack>
        ) : (
          <Text fz="xs" c="dimmed">
            —
          </Text>
        ),
    },
    ...(showAssignee
      ? [
          {
            key: 'assignee',
            label: 'Assigned',
            width: 140,
            render: (row: Activity) =>
              row.assigned_salesperson ? (
                <Group gap={5} wrap="nowrap">
                  <IconUserCheck size={14} opacity={0.5} />
                  <Text fz="sm" truncate>
                    {row.assigned_salesperson.name}
                  </Text>
                </Group>
              ) : (
                <Text fz="xs" c="dimmed">
                  Desk
                </Text>
              ),
          },
        ]
      : []),
    {
      key: 'status',
      label: 'Status',
      width: 122,
      render: (row) => <StatusBadge value={row.status} />,
    },
    {
      key: 'actions',
      label: '',
      width: 76,
      render: (row) =>
        row.status === 'SCHEDULED' || row.status === 'IN_PROGRESS' ? (
          <Group gap={2} wrap="nowrap" onClick={(event) => event.stopPropagation()}>
            <Tooltip label="Record completion">
              <ActionIcon variant="light" color="moss" onClick={() => setCompleting(row)}>
                <IconCircleCheck size={16} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Assign to a salesperson">
              <ActionIcon variant="light" color="ink" onClick={() => setAssigning(row)}>
                <IconUserCheck size={16} />
              </ActionIcon>
            </Tooltip>
          </Group>
        ) : (
          <Text fz="xs" c="dimmed">
            {row.completed_at ? formatDateTime(row.completed_at).split(',')[0] : ''}
          </Text>
        ),
    },
  ];

  return (
    <>
      <DataTable
        columns={columns}
        rows={rows}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={onPageChange}
        onPageSizeChange={onPageSizeChange}
        sort={sort}
        onSortChange={onSortChange}
        loading={loading}
        framed={framed}
        fill={fill}
        onRowClick={(row) => setViewing(row.id)}
        emptyMessage={emptyMessage}
        emptyHint={emptyHint}
      />
      <ActivityDetailDrawer activityId={viewing} onClose={() => setViewing(null)} />
      {completing && (
        <CompleteActivityModal activity={completing} onClose={() => setCompleting(null)} />
      )}
      {assigning && <AssignActivityModal activity={assigning} onClose={() => setAssigning(null)} />}
    </>
  );
}
