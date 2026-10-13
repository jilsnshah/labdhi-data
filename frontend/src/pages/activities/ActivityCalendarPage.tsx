/** Who is where, and when - a week at a time, so double bookings are visible. */

import { Box, Group, SegmentedControl, Stack, Text } from '@mantine/core';
import { DatePickerInput } from '@mantine/dates';
import { IconChevronLeft, IconChevronRight, IconMapPin } from '@tabler/icons-react';
import { ActionIcon, Button } from '@mantine/core';
import { useMemo, useState } from 'react';

import { useActivityCalendar } from '@/api/hooks';
import type { Activity } from '@/api/types';
import { ActivityDetailDrawer } from '@/components/ActivityDetailDrawer';
import { EntitySelect } from '@/components/EntitySelect';
import { PageHeader } from '@/components/PageHeader';
import { STATUS_TONES } from '@/theme';
import { dayjs, humanize } from '@/lib/format';

type Span = '1' | '7';

export function ActivityCalendarPage() {
  const [anchor, setAnchor] = useState<string | null>(dayjs().format('YYYY-MM-DD'));
  // A seven-column week is unreadable on a phone; start on the day instead.
  const [span, setSpan] = useState<Span>(() =>
    typeof window !== 'undefined' && window.innerWidth <= 760 ? '1' : '7',
  );
  const [salespersonId, setSalespersonId] = useState<number | null>(null);
  const [viewing, setViewing] = useState<number | null>(null);

  const from = anchor ?? dayjs().format('YYYY-MM-DD');
  const days = Number(span);
  const to = dayjs(from)
    .add(days - 1, 'day')
    .format('YYYY-MM-DD');
  const { data } = useActivityCalendar(from, to, salespersonId);

  const columns = useMemo(() => {
    const buckets = new Map<string, Activity[]>();
    for (let index = 0; index < days; index += 1) {
      buckets.set(dayjs(from).add(index, 'day').format('YYYY-MM-DD'), []);
    }
    (data ?? []).forEach((activity) => {
      if (!activity.scheduled_at) return;
      const key = dayjs(activity.scheduled_at).format('YYYY-MM-DD');
      buckets.get(key)?.push(activity);
    });
    return Array.from(buckets.entries());
  }, [data, from, days]);

  const shift = (direction: 1 | -1) =>
    setAnchor(
      dayjs(from)
        .add(direction * days, 'day')
        .format('YYYY-MM-DD'),
    );

  return (
    <div className="page-fill">
      <PageHeader
        eyebrow="Field work"
        title="Schedule"
        subtitle="Spot a double booking before you assign the next visit."
        actions={
          <Group gap="xs" wrap="wrap">
            <ActionIcon variant="default" size={34} onClick={() => shift(-1)} aria-label="Previous">
              <IconChevronLeft size={16} />
            </ActionIcon>
            <Button variant="default" onClick={() => setAnchor(dayjs().format('YYYY-MM-DD'))}>
              Today
            </Button>
            <ActionIcon variant="default" size={34} onClick={() => shift(1)} aria-label="Next">
              <IconChevronRight size={16} />
            </ActionIcon>
            <DatePickerInput
              w={150}
              valueFormat="DD MMM YYYY"
              value={anchor}
              onChange={setAnchor}
            />
            <SegmentedControl
              value={span}
              onChange={(value) => setSpan(value as Span)}
              data={[
                { value: '1', label: 'Day' },
                { value: '7', label: 'Week' },
              ]}
            />
            <Box w={190} maw="100%">
              <EntitySelect
                kind="user"
                placeholder="All salespeople"
                filters={{ role: 'SALESPERSON' }}
                value={salespersonId}
                onChange={setSalespersonId}
              />
            </Box>
          </Group>
        }
      />

      <div className="week-board" data-span={span}>
        {columns.map(([day, activities]) => {
          const isToday = dayjs(day).isSame(dayjs(), 'day');
          return (
            <div key={day} className="week-day" data-today={isToday || undefined}>
              <div className="week-day-head">
                <Group justify="space-between" wrap="nowrap">
                  <Stack gap={0}>
                    <Text fz="xs" c="ink.5" tt="uppercase" style={{ letterSpacing: '0.06em' }}>
                      {dayjs(day).format('ddd')}
                    </Text>
                    <Text fz="md" fw={isToday ? 600 : 500} c="ink.9">
                      {dayjs(day).format('D MMM')}
                    </Text>
                  </Stack>
                  {activities.length > 0 && (
                    <Text fz="xs" c="ink.5" className="mono-tight">
                      {activities.length}
                    </Text>
                  )}
                </Group>
              </div>

              <div className="week-events">
                {activities.length === 0 ? (
                  <Text fz="xs" c="ink.4" ta="center" py="md">
                    —
                  </Text>
                ) : (
                  activities.map((activity) => (
                    <button
                      key={activity.id}
                      type="button"
                      className="week-event"
                      data-tone={STATUS_TONES[activity.status] ?? 'neutral'}
                      onClick={() => setViewing(activity.id)}
                    >
                      <Group justify="space-between" wrap="nowrap" gap="xs">
                        <Text fz="xs" fw={600} c="ink.8" className="mono-tight">
                          {dayjs(activity.scheduled_at).format('HH:mm')}
                        </Text>
                        <Text fz="xs" c="ink.5" truncate>
                          {activity.assigned_salesperson?.name.split(' ')[0] ?? 'Desk'}
                        </Text>
                      </Group>
                      <Text fz="sm" fw={500} c="ink.9" truncate>
                        {activity.party?.name}
                      </Text>
                      <Group gap={4} wrap="nowrap">
                        <Text fz="xs" c="ink.5" truncate>
                          {humanize(activity.activity_type).toLowerCase()}
                        </Text>
                        {activity.location && (
                          <>
                            <IconMapPin size={11} opacity={0.45} />
                            <Text fz="xs" c="ink.5" truncate>
                              {activity.location.city}
                            </Text>
                          </>
                        )}
                      </Group>
                    </button>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      <ActivityDetailDrawer activityId={viewing} onClose={() => setViewing(null)} />
    </div>
  );
}
