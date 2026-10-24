import { Badge, Group, Stack, Text, Timeline } from '@mantine/core';
import {
  IconCalendarEvent,
  IconCircleCheck,
  IconCurrencyRupee,
  IconFileText,
  IconGitBranch,
  IconNote,
  IconPhone,
  IconUserPlus,
} from '@tabler/icons-react';
import { Link } from 'react-router-dom';

import type { TimelineEvent } from '@/api/types';
import { EmptyState } from '@/components/ui';
import { formatDateTime, formatRelative } from '@/lib/format';

const ICONS: Record<string, React.ReactNode> = {
  created: <IconFileText size={13} />,
  status: <IconCircleCheck size={13} />,
  response: <IconCurrencyRupee size={13} />,
  child_response: <IconCurrencyRupee size={13} />,
  child_inquiry: <IconGitBranch size={13} />,
  activity: <IconPhone size={13} />,
  note: <IconNote size={13} />,
  inquiry: <IconFileText size={13} />,
  inquiry_closed: <IconCircleCheck size={13} />,
  party_created: <IconUserPlus size={13} />,
};

const COLORS: Record<string, string> = {
  created: 'brand',
  status: 'brand',
  response: 'violet',
  child_response: 'violet',
  child_inquiry: 'grape',
  activity: 'teal',
  note: 'yellow',
  inquiry: 'blue',
  inquiry_closed: 'gray',
  party_created: 'slate',
};

function linkFor(event: TimelineEvent): string | null {
  if (event.ref_type === 'inquiry' && event.ref_id) return `/inquiries/${event.ref_id}`;
  if (event.ref_type === 'party' && event.ref_id) return `/parties/${event.ref_id}`;
  return null;
}

export function EventTimeline({ events }: { events: TimelineEvent[] }) {
  if (!events.length) {
    return <EmptyState title="No history yet" compact />;
  }
  return (
    <Timeline active={events.length} bulletSize={24} lineWidth={2} color="ink">
      {events.map((event, index) => {
        const to = linkFor(event);
        return (
          <Timeline.Item
            key={`${event.at}-${index}`}
            bullet={ICONS[event.kind] ?? <IconCalendarEvent size={13} />}
            color={COLORS[event.kind] ?? 'slate'}
            title={
              <Group gap="xs" wrap="nowrap" align="baseline">
                {to ? (
                  <Text component={Link} to={to} fz="sm" fw={600} c="navy.7">
                    {event.title}
                  </Text>
                ) : (
                  <Text fz="sm" fw={600}>
                    {event.title}
                  </Text>
                )}
                {event.actor && (
                  <Badge size="xs" variant="default">
                    {event.actor}
                  </Badge>
                )}
              </Group>
            }
          >
            <Stack gap={2} mt={2}>
              {event.description && (
                <Text fz="xs" c="ink.6" className="wrap">
                  {event.description}
                </Text>
              )}
              <Text fz="xs" c="dimmed">
                {formatDateTime(event.at)} · {formatRelative(event.at)}
              </Text>
            </Stack>
          </Timeline.Item>
        );
      })}
    </Timeline>
  );
}
