/**
 * The desk's morning screen.
 *
 * One strip of figures, the day's work as a real queue you can act on, and a
 * sticky rail of context. Everything that matters sits above the fold.
 */

import { Box, Button, Group, Stack, Text } from '@mantine/core';
import { IconArrowRight, IconCalendarTime, IconPlus } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useDashboard, useSalespeopleWorkload } from '@/api/hooks';
import { ActivityTable } from '@/components/ActivityTable';
import { InquiryTable } from '@/components/InquiryTable';
import { RailSection } from '@/components/DetailLayout';
import { ActivityFormModal } from '@/components/modals/ActivityModals';
import { InquiryFormModal } from '@/components/modals/InquiryFormModal';
import { EmptyState } from '@/components/ui';
import { dayjs, formatDate, humanize } from '@/lib/format';

export function DashboardPage() {
  const { data } = useDashboard();
  const { data: team } = useSalespeopleWorkload();
  const [inquiryOpen, setInquiryOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);

  const counts = data?.counts;

  return (
    <>
      <Group justify="space-between" align="flex-end" wrap="wrap" gap="md" mb="lg">
        <Stack gap={2}>
          <Text fz={20} fw={600} c="ink.9" lh={1.25}>
            Trade desk
          </Text>
          <Text fz="sm" c="ink.5">
            {dayjs().format('dddd, D MMMM YYYY')}
          </Text>
        </Stack>
        <Group gap="xs">
          <Button
            variant="default"
            leftSection={<IconCalendarTime size={15} />}
            onClick={() => setActivityOpen(true)}
          >
            Schedule activity
          </Button>
          <Button leftSection={<IconPlus size={15} />} onClick={() => setInquiryOpen(true)}>
            New inquiry
          </Button>
        </Group>
      </Group>

      <Box className="stat-strip" mb="lg">
        <Figure
          label="Active customer inquiries"
          value={counts?.open_customer_inquiries}
          hint="what customers want"
          to="/inquiries/customer"
        />
        <Figure
          label="Active supplier quotes"
          value={counts?.open_supplier_inquiries}
          hint={`plus ${counts?.open_transport_inquiries ?? 0} active transport quotes`}
          to="/inquiries/supplier"
        />
        <Figure
          label="Due today"
          value={counts?.todays_activities}
          hint="calls, messages and visits"
          to="/activities/today"
        />
        <Figure
          label="Overdue"
          value={counts?.overdue_activities}
          hint="past due, still open"
          to="/activities/upcoming"
          alert
        />
      </Box>

      <div className="dash-grid">
        <Stack gap="xl">
          <Box>
            <Group justify="space-between" align="center" mb="sm">
              <Text className="block-label">Today's queue</Text>
              <Button
                component={Link}
                to="/activities/today"
                size="compact-sm"
                variant="subtle"
                rightSection={<IconArrowRight size={13} />}
              >
                All activities
              </Button>
            </Group>
            <ActivityTable
              rows={data?.todays_activities ?? []}
              emptyMessage="Nothing scheduled for today"
              emptyHint="Schedule a call or a visit and it appears here with its actions."
            />
          </Box>

          <Box>
            <Group justify="space-between" align="center" mb="sm">
              <Text className="block-label">Recent inquiries</Text>
              <Button
                component={Link}
                to="/inquiries/customer"
                size="compact-sm"
                variant="subtle"
                rightSection={<IconArrowRight size={13} />}
              >
                All inquiries
              </Button>
            </Group>
            <InquiryTable
              rows={data?.recent_inquiries ?? []}
              showType
              showLocation={false}
              emptyMessage="No inquiries yet"
            />
          </Box>
        </Stack>

        <aside className="side-rail">
          <RailSection
            label="Field team"
            action={
              <Button
                component={Link}
                to="/activities/salespeople"
                size="compact-xs"
                variant="subtle"
              >
                Manage
              </Button>
            }
          >
            {team?.length ? (
              team.map((person) => (
                <Group key={person.id} justify="space-between" wrap="nowrap">
                  <Text fz="sm" fw={550} c="ink.9" truncate>
                    {person.name}
                  </Text>
                  <Group gap="sm" wrap="nowrap">
                    <Text fz="sm" c={person.today_pending ? 'ink.8' : 'ink.4'}>
                      {person.today_pending
                        ? `${person.today_pending} to do`
                        : 'clear today'}
                    </Text>
                    {person.overdue > 0 && (
                      <Text fz="sm" fw={550} c="rust.8">
                        {person.overdue} late
                      </Text>
                    )}
                  </Group>
                </Group>
              ))
            ) : (
              <Text fz="sm" c="ink.5">
                No salesperson accounts yet.
              </Text>
            )}
          </RailSection>

          <RailSection
            label="Recently closed"
            action={
              counts?.upcoming_followups ? (
                <Text fz="xs" c="ink.5">
                  {counts.upcoming_followups} follow-ups due
                </Text>
              ) : undefined
            }
          >
            {data?.recently_closed_inquiries.length ? (
              data.recently_closed_inquiries.slice(0, 6).map((inquiry) => (
                <Stack key={inquiry.id} gap={2}>
                  <Group justify="space-between" wrap="nowrap">
                    <Text
                      fz="sm"
                      fw={550}
                      component={Link}
                      to={`/inquiries/${inquiry.id}`}
                      c="ink.9"
                      truncate
                    >
                      #{inquiry.id} · {inquiry.party_name}
                    </Text>
                    <Text fz="xs" c="ink.5" style={{ whiteSpace: 'nowrap' }}>
                      {formatDate(inquiry.closed_at)}
                    </Text>
                  </Group>
                  <Text fz="xs" c="ink.5" truncate>
                    {humanize(inquiry.inquiry_type)}
                    {inquiry.product_name ? ` · ${inquiry.product_name}` : ''}
                  </Text>
                </Stack>
              ))
            ) : (
              <Text fz="sm" c="ink.5">
                Nothing closed yet.
              </Text>
            )}
          </RailSection>

          <RailSection
            label="New customers"
            action={
              counts?.prospects ? (
                <Text fz="xs" c="amber.9">
                  {counts.prospects} prospects
                </Text>
              ) : undefined
            }
          >
            {data?.recent_customers.length ? (
              data.recent_customers.slice(0, 5).map((party) => (
                <Group key={party.id} justify="space-between" wrap="nowrap">
                  <Text
                    fz="sm"
                    component={Link}
                    to={`/parties/${party.id}`}
                    c="ink.9"
                    fw={550}
                    truncate
                  >
                    {party.name}
                  </Text>
                  <Text fz="xs" c="ink.5" style={{ whiteSpace: 'nowrap' }}>
                    {party.stage === 'PROSPECT' ? 'Prospect' : humanize(party.party_type)}
                  </Text>
                </Group>
              ))
            ) : (
              <EmptyState title="No customers yet" compact />
            )}
          </RailSection>
        </aside>
      </div>

      {inquiryOpen && (
        <InquiryFormModal opened onClose={() => setInquiryOpen(false)} defaultType="CUSTOMER" />
      )}
      {activityOpen && <ActivityFormModal onClose={() => setActivityOpen(false)} />}
    </>
  );
}

function Figure({
  label,
  value,
  hint,
  to,
  alert = false,
}: {
  label: string;
  value?: number;
  hint: string;
  to: string;
  alert?: boolean;
}) {
  return (
    <Link to={to}>
      <Text fz="sm" c="ink.6">
        {label}
      </Text>
      <Text
        className="stat-value mono-tight"
        fz={30}
        fw={600}
        lh={1.15}
        mt={6}
        c={alert && (value ?? 0) > 0 ? 'rust.8' : 'ink.9'}
      >
        {value ?? '—'}
      </Text>
      <Text fz="sm" c="ink.5" mt={2} lineClamp={1}>
        {hint}
      </Text>
    </Link>
  );
}
