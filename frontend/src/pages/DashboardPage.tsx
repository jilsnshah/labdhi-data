/**
 * The desk's morning screen.
 *
 * A navy hero with the four numbers that set the day, then the market itself:
 * the rate board (where is there a trade?), how rates have moved, the day's
 * calls and visits as a queue you can act on, and the latest inquiries.
 */

import { Box, Button, Group, SegmentedControl, Stack, Text } from '@mantine/core';
import { IconArrowRight, IconCalendarTime, IconPlus } from '@tabler/icons-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { useDashboard, useInquiries, useSalespeopleWorkload } from '@/api/hooks';
import { ActivityTable } from '@/components/ActivityTable';
import { InquiryTable } from '@/components/InquiryTable';
import { RailSection } from '@/components/DetailLayout';
import { RateBoard } from '@/components/market/RateBoard';
import { PartyAvatar, Sparkline, TrendChart } from '@/components/market/Visuals';
import { ActivityFormModal } from '@/components/modals/ActivityModals';
import { InquiryFormModal } from '@/components/modals/InquiryFormModal';
import { EmptyState } from '@/components/ui';
import { useAuth } from '@/lib/auth';
import { dayjs, formatDate, humanize } from '@/lib/format';
import { buildBoard, dailyCounts, fmtRate, fmtTonnes, toQuote } from '@/lib/market';
import type { Quote } from '@/lib/market';

/** The last 200 of each side are plenty for the board and the trend. */
const BOOK = { page_size: 200, sort_by: 'created_at', sort_dir: 'desc' } as const;

function greeting(): string {
  const hour = dayjs().hour();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export function DashboardPage() {
  const { user } = useAuth();
  const { data } = useDashboard();
  const { data: team } = useSalespeopleWorkload();
  const { data: supplyRows } = useInquiries({ ...BOOK, inquiry_type: 'SUPPLIER' });
  const { data: demandRows } = useInquiries({ ...BOOK, inquiry_type: 'CUSTOMER' });
  const [inquiryOpen, setInquiryOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [trendProduct, setTrendProduct] = useState<string | null>(null);

  const counts = data?.counts;

  const quotes = useMemo(
    () =>
      [...(supplyRows?.items ?? []), ...(demandRows?.items ?? [])]
        .map(toQuote)
        .filter((q): q is Quote => q !== null),
    [supplyRows, demandRows],
  );
  const board = useMemo(() => buildBoard(quotes), [quotes]);
  const live = quotes.filter((q) => q.active);
  const supplyTonnes = live
    .filter((q) => q.side === 'supply')
    .reduce((t, q) => t + (q.tonnes ?? 0), 0);
  const demandTonnes = live
    .filter((q) => q.side === 'demand')
    .reduce((t, q) => t + (q.tonnes ?? 0), 0);
  const bestSpread = board.find((line) => line.spread !== null && line.spread > 0) ?? null;

  // Products with enough history to draw a line.
  const trendOptions = useMemo(() => {
    const byProduct = new Map<number, { name: string; count: number }>();
    for (const quote of quotes) {
      const entry = byProduct.get(quote.productId) ?? { name: quote.productName, count: 0 };
      entry.count += 1;
      byProduct.set(quote.productId, entry);
    }
    return [...byProduct.entries()]
      .filter(([, entry]) => entry.count >= 2)
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 4)
      .map(([id, entry]) => ({ value: String(id), label: entry.name }));
  }, [quotes]);
  const activeTrend = trendProduct ?? trendOptions[0]?.value ?? null;
  const trendQuotes = quotes.filter((q) => String(q.productId) === activeTrend);

  const firstName = user?.name || 'there';

  return (
    <Stack gap="xl" className="reveal">
      {/* ---------------------------------------------------------------- hero */}
      <section className="hero">
        <Group justify="space-between" align="flex-start" wrap="wrap" gap="lg">
          <Box>
            <Text
              fz={11}
              fw={600}
              c="#c9b07a"
              tt="uppercase"
              style={{ letterSpacing: '0.18em' }}
            >
              {dayjs().format('dddd, D MMMM YYYY')}
            </Text>
            <div className="hero-greeting" style={{ marginTop: 8 }}>
              {greeting()}, <em>{firstName}</em>.
            </div>
            <Text c="#aab4c7" fz="sm" mt={8} maw={600}>
              {bestSpread
                ? `Widest live spread is ${bestSpread.productName} at ${fmtRate(bestSpread.spread ?? 0)}/kg — buy from ${bestSpread.bestBuy?.partyName}, sell to ${bestSpread.bestSell?.partyName}.`
                : 'Record supplier offers and customer demand with rates to see where the trades are.'}
            </Text>
          </Box>
          <Group gap="xs">
            <Button
              variant="white"
              color="dark"
              radius="xl"
              leftSection={<IconCalendarTime size={15} />}
              onClick={() => setActivityOpen(true)}
            >
              Schedule activity
            </Button>
            <Button
              radius="xl"
              leftSection={<IconPlus size={15} />}
              onClick={() => setInquiryOpen(true)}
              styles={{
                root: {
                  background: 'linear-gradient(145deg,#e2bd6b,#b8862a)',
                  color: '#1a1206',
                },
              }}
            >
              New inquiry
            </Button>
          </Group>
        </Group>

        <div className="hero-kpis">
          <HeroKpi
            to="/inquiries/customer"
            label="Live demand"
            value={counts?.open_customer_inquiries}
            hint={`${fmtTonnes(demandTonnes)} wanted`}
            spark={dailyCounts((demandRows?.items ?? []).map((r) => r.created_at))}
            color="#8ea2de"
          />
          <HeroKpi
            to="/inquiries/supplier"
            label="Live supply"
            value={counts?.open_supplier_inquiries}
            hint={`${fmtTonnes(supplyTonnes)} on offer`}
            spark={dailyCounts((supplyRows?.items ?? []).map((r) => r.created_at))}
            color="#85c9ba"
          />
          <HeroKpi
            to="/inquiries/supplier"
            label="Best spread"
            value={bestSpread ? fmtRate(bestSpread.spread ?? 0) : '—'}
            hint={bestSpread ? `${bestSpread.productName} · per kg` : 'No two-sided market yet'}
          />
          <HeroKpi
            to="/activities/today"
            label="Today's agenda"
            value={counts?.todays_activities}
            hint={
              counts?.overdue_activities
                ? `${counts.overdue_activities} overdue · calls & visits`
                : 'calls, messages and visits'
            }
            alert={(counts?.overdue_activities ?? 0) > 0}
          />
        </div>
      </section>

      <div className="dash-grid">
        <Stack gap="xl">
          {/* ------------------------------------------------------- rate board */}
          <section className="panel">
            <div className="panel-head">
              <Box>
                <div className="block-label">Market</div>
                <div className="panel-title">Rate board</div>
              </Box>
              <Text fz="xs" c="ink.5" maw={320} ta="right">
                Cheapest live offer against the best live demand, per product. Rates in ₹/kg.
              </Text>
            </div>
            <RateBoard lines={board} limit={8} />
          </section>

          {/* ------------------------------------------------------------ trend */}
          {trendOptions.length > 0 && (
            <section className="panel">
              <div className="panel-head">
                <Box>
                  <div className="block-label">Rate history</div>
                  <div className="panel-title">How quotes have moved</div>
                </Box>
                <Group gap="md" wrap="nowrap">
                  <span className="side-tag" data-side="supply">
                    Supply
                  </span>
                  <span className="side-tag" data-side="demand">
                    Demand
                  </span>
                </Group>
              </div>
              <Box px="lg" pt="md">
                <SegmentedControl
                  size="xs"
                  value={activeTrend ?? undefined}
                  onChange={setTrendProduct}
                  data={trendOptions}
                />
              </Box>
              <Box px="md" pb="md" pt="xs">
                <TrendChart quotes={trendQuotes} />
              </Box>
            </section>
          )}

          {/* ------------------------------------------------------ today's work */}
          <section className="panel">
            <div className="panel-head">
              <Box>
                <div className="block-label">Field work</div>
                <div className="panel-title">Today's queue</div>
              </Box>
              <Button
                component={Link}
                to="/activities/today"
                size="compact-sm"
                variant="subtle"
                rightSection={<IconArrowRight size={13} />}
              >
                All activities
              </Button>
            </div>
            <ActivityTable
              rows={data?.todays_activities ?? []}
              framed={false}
              emptyMessage="Nothing scheduled for today"
              emptyHint="Schedule a call or a visit and it appears here with its actions."
            />
          </section>

          {/* --------------------------------------------------- recent inquiries */}
          <section className="panel">
            <div className="panel-head">
              <Box>
                <div className="block-label">Latest</div>
                <div className="panel-title">Recent inquiries</div>
              </Box>
              <Button
                component={Link}
                to="/inquiries/customer"
                size="compact-sm"
                variant="subtle"
                rightSection={<IconArrowRight size={13} />}
              >
                All inquiries
              </Button>
            </div>
            <InquiryTable
              rows={data?.recent_inquiries ?? []}
              showType
              showLocation={false}
              framed={false}
              emptyMessage="No inquiries yet"
            />
          </section>
        </Stack>

        {/* --------------------------------------------------------------- rail */}
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
              team.map((person) => {
                const done = person.today_total
                  ? Math.round((person.today_completed / person.today_total) * 100)
                  : 100;
                return (
                  <Stack key={person.id} gap={6}>
                    <Group justify="space-between" wrap="nowrap">
                      <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
                        <PartyAvatar name={person.name} size={28} />
                        <Text fz="sm" fw={600} c="ink.9" truncate>
                          {person.name}
                        </Text>
                      </Group>
                      <Group gap={8} wrap="nowrap">
                        <Text fz="xs" c={person.today_pending ? 'ink.7' : 'ink.4'}>
                          {person.today_pending ? `${person.today_pending} to do` : 'clear'}
                        </Text>
                        {person.overdue > 0 && (
                          <Text fz="xs" fw={600} c="rust.8">
                            {person.overdue} late
                          </Text>
                        )}
                      </Group>
                    </Group>
                    <Box h={4} style={{ background: 'var(--hairline-soft)', borderRadius: 4 }}>
                      <Box
                        h={4}
                        w={`${done}%`}
                        style={{ background: 'var(--brass)', borderRadius: 4 }}
                      />
                    </Box>
                  </Stack>
                );
              })
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
                <Group key={inquiry.id} gap="sm" wrap="nowrap" align="flex-start">
                  <PartyAvatar name={inquiry.party_name} size={30} />
                  <Stack gap={1} style={{ minWidth: 0, flex: 1 }}>
                    <Group justify="space-between" wrap="nowrap">
                      <Text
                        fz="sm"
                        fw={600}
                        component={Link}
                        to={`/inquiries/${inquiry.id}`}
                        c="ink.9"
                        truncate
                      >
                        {inquiry.party_name}
                      </Text>
                      <Text fz="xs" c="ink.5" style={{ whiteSpace: 'nowrap' }}>
                        {formatDate(inquiry.closed_at)}
                      </Text>
                    </Group>
                    <Text fz="xs" c="ink.5" truncate>
                      #{inquiry.id} · {humanize(inquiry.inquiry_type)}
                      {inquiry.product_name ? ` · ${inquiry.product_name}` : ''}
                    </Text>
                  </Stack>
                </Group>
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
                <Text fz="xs" fw={600} c="brass.8">
                  {counts.prospects} prospects
                </Text>
              ) : undefined
            }
          >
            {data?.recent_customers.length ? (
              data.recent_customers.slice(0, 5).map((party) => (
                <Group key={party.id} gap="sm" wrap="nowrap">
                  <PartyAvatar name={party.name} size={30} />
                  <Text
                    fz="sm"
                    component={Link}
                    to={`/parties/${party.id}`}
                    c="ink.9"
                    fw={600}
                    truncate
                    style={{ flex: 1 }}
                  >
                    {party.name}
                  </Text>
                  <Text fz="xs" c={party.stage === 'PROSPECT' ? 'brass.8' : 'ink.5'}>
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
    </Stack>
  );
}

function HeroKpi({
  label,
  value,
  hint,
  to,
  spark,
  color,
  alert = false,
}: {
  label: string;
  value?: number | string;
  hint: string;
  to: string;
  spark?: number[];
  color?: string;
  alert?: boolean;
}) {
  return (
    <Link to={to} className="hero-kpi">
      <div className="hero-kpi-label">{label}</div>
      <Group justify="space-between" align="flex-end" wrap="nowrap" gap="xs">
        <div className="hero-kpi-value" style={alert ? { color: '#f0a49d' } : undefined}>
          {value ?? '—'}
        </div>
        {spark && spark.some(Boolean) && (
          <Box mb={6}>
            <Sparkline values={spark} width={84} height={30} color={color} />
          </Box>
        )}
      </Group>
      <div className="hero-kpi-hint">{hint}</div>
    </Link>
  );
}
