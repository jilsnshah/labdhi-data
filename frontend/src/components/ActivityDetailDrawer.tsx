/** Admin view of one activity: assignment, brief, completion and follow-ups. */

import {
  Alert,
  Badge,
  Button,
  Card,
  Divider,
  Drawer,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { IconCircleCheck, IconMapPin, IconUserCheck } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useActivity } from '@/api/hooks';
import { isFieldLogged, type Activity } from '@/api/types';
import { StatusBadge } from '@/components/StatusBadge';
import {
  ActivityFormModal,
  AssignActivityModal,
  CompleteActivityModal,
} from '@/components/modals/ActivityModals';
import { Field } from '@/components/ui';
import { formatDateTime, humanize } from '@/lib/format';

export function ActivityDetailDrawer({
  activityId,
  onClose,
}: {
  activityId: number | null;
  onClose: () => void;
}) {
  const { data: activity, isLoading } = useActivity(activityId ?? undefined);
  const [completing, setCompleting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [assigning, setAssigning] = useState(false);

  const open = activityId !== null;
  const isOpenStatus = activity?.status === 'SCHEDULED' || activity?.status === 'IN_PROGRESS';

  return (
    <Drawer
      opened={open}
      onClose={onClose}
      position="right"
      size="lg"
      title={activity ? `Activity #${activity.id}` : 'Activity'}
    >
      {isLoading && (
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      )}
      {activity && (
        <Stack gap="lg">
          <Group gap="xs">
            <Badge variant="default">{humanize(activity.activity_type)}</Badge>
            <StatusBadge value={activity.status} />
            {activity.outcome_code && <StatusBadge value={activity.outcome_code} />}
          </Group>

          <Stack gap="sm">
            <Field
              label="Customer"
              value={
                <Text fz="sm" component={Link} to={`/parties/${activity.party_id}`} c="navy.7">
                  {activity.party?.name}
                </Text>
              }
            />
            <Field
              label="Assigned to"
              value={
                activity.assigned_salesperson ? (
                  <Group gap={6}>
                    <IconUserCheck size={14} />
                    <Text fz="sm">{activity.assigned_salesperson.name}</Text>
                  </Group>
                ) : (
                  <Text fz="sm" c="dimmed">
                    Desk (unassigned)
                  </Text>
                )
              }
            />
            {isFieldLogged(activity) && (
              <Field
                label="Source"
                value={
                  <Badge color="brass" variant="light" size="sm">
                    Logged from the field by {activity.creator?.name ?? 'the salesperson'}
                  </Badge>
                }
              />
            )}
            <Field label="Scheduled" value={formatDateTime(activity.scheduled_at)} />
            {!activity.location && activity.location_snapshot && (
              <Field
                label="Location"
                value={<SnapshotPlace snapshot={activity.location_snapshot} />}
              />
            )}
            {activity.location && (
              <Field
                label="Location"
                value={
                  <Group gap={6} wrap="nowrap">
                    <IconMapPin size={14} />
                    <Text fz="sm">
                      {[activity.location.label, activity.location.city, activity.location.state]
                        .filter(Boolean)
                        .join(', ')}
                    </Text>
                  </Group>
                }
              />
            )}
            {activity.subject && <Field label="Subject" value={activity.subject} />}
            {activity.note && <Field label="Purpose" value={activity.note} />}
            {activity.related_inquiry_id && (
              <Field
                label="Inquiry"
                value={
                  <Text
                    fz="sm"
                    component={Link}
                    to={`/inquiries/${activity.related_inquiry_id}`}
                    c="navy.7"
                  >
                    #{activity.related_inquiry_id}
                  </Text>
                }
              />
            )}
            <Field
              label="Created"
              value={`${formatDateTime(activity.created_at)} by ${activity.creator?.name ?? '-'}`}
            />
            {activity.parent_activity_id && (
              <Field label="Follow-up of" value={`Activity #${activity.parent_activity_id}`} />
            )}
          </Stack>

          {activity.status === 'COMPLETED' && (
            <Alert color="moss" icon={<IconCircleCheck size={16} />}>
              <Text fz="sm" fw={600}>
                {humanize(activity.outcome_code ?? 'COMPLETED')}
              </Text>
              <Text fz="xs" c="dimmed">
                {formatDateTime(activity.completed_at)}
                {activity.completer ? ` by ${activity.completer.name}` : ''}
              </Text>
              {activity.outcome && (
                <Text fz="sm" mt={6}>
                  {activity.outcome}
                </Text>
              )}
            </Alert>
          )}

          <Group gap="xs">
            {isOpenStatus && (
              <>
                <Button size="xs" onClick={() => setCompleting(true)}>
                  Record completion
                </Button>
                <Button size="xs" variant="default" onClick={() => setAssigning(true)}>
                  Reassign
                </Button>
                <Button size="xs" variant="default" onClick={() => setEditing(true)}>
                  Reschedule / edit
                </Button>
              </>
            )}
          </Group>

          <Divider />
          <div>
            <Title order={6} mb="xs">
              Follow-ups ({activity.follow_ups.length})
            </Title>
            {activity.follow_ups.length === 0 ? (
              <Text fz="sm" c="dimmed">
                No follow-up scheduled from this activity.
              </Text>
            ) : (
              <Stack gap="xs">
                {activity.follow_ups.map((item) => (
                  <Card key={item.id} padding="sm" shadow="none" bg="ink.0">
                    <Group justify="space-between" wrap="nowrap">
                      <Stack gap={0}>
                        <Group gap={6}>
                          <Badge size="xs" variant="default">
                            {humanize(item.activity_type)}
                          </Badge>
                          <StatusBadge value={item.status} size="xs" />
                          <Text fz="xs">#{item.id}</Text>
                        </Group>
                        <Text fz="xs" c="dimmed">
                          {item.note || item.subject || '-'}
                        </Text>
                      </Stack>
                      <Stack gap={0} align="flex-end">
                        <Text fz="xs">{formatDateTime(item.scheduled_at)}</Text>
                        <Text fz="xs" c="dimmed">
                          {item.assigned_salesperson?.name ?? 'Desk'}
                        </Text>
                      </Stack>
                    </Group>
                  </Card>
                ))}
              </Stack>
            )}
          </div>

          {completing && (
            <CompleteActivityModal activity={activity} onClose={() => setCompleting(false)} />
          )}
          {editing && <ActivityFormModal record={activity} onClose={() => setEditing(false)} />}
          {assigning && (
            <AssignActivityModal activity={activity} onClose={() => setAssigning(false)} />
          )}
        </Stack>
      )}
    </Drawer>
  );
}

function SnapshotPlace({ snapshot }: { snapshot: NonNullable<Activity['location_snapshot']> }) {
  const pinned = snapshot.latitude && snapshot.longitude;
  return (
    <Group gap={6} wrap="nowrap">
      <IconMapPin size={14} />
      <Text fz="sm">
        {[snapshot.label, snapshot.city].filter(Boolean).join(', ') || 'Pinned spot'}
      </Text>
      {pinned && (
        <Text
          fz="xs"
          component="a"
          href={`https://www.google.com/maps?q=${snapshot.latitude},${snapshot.longitude}`}
          target="_blank"
          rel="noreferrer"
          c="navy.7"
          style={{ whiteSpace: 'nowrap' }}
        >
          Open pin
        </Text>
      )}
    </Group>
  );
}
