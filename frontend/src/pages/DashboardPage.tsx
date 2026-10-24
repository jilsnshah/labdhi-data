/**
 * The desk's operating screen.
 *
 * Four figures that set the day, then the market itself: the rate board (where
 * is there a trade?), how rates have moved, the day's calls and visits as a
 * queue you can act on, and the latest inquiries. The board is the point of
 * the screen, so it sits directly under the figures and inside the first fold
 * of a 900px-tall laptop.
 *
 * Note on the fourth figure: the API counts today's open activities and
 * overdue ones separately - an overdue activity was scheduled *before* today
 * and is not in today's number. They are shown as a figure plus a flagged
 * hint rather than added together.
 */

import { Box, Button, Group, SegmentedControl, Stack, Text } from '@mantine/core';
import {
  IconArrowRight,
  IconArrowsExchange,
  IconCalendarTime,
  IconClipboardList,
  IconPackageExport,
  IconPlus,
} from '@tabler/icons-react';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { useDashboard, useInquiries, useSalespeopleWorkload } from '@/api/hooks';
import { ActivityTable } from '@/components/ActivityTable';
import { InquiryTable } from '@/components/InquiryTable';
import { RailSection } from '@/components/DetailLayout';
import { RateBoard } from '@/components/market/RateBoard';
import { PartyAvatar, TrendChart } from '@/components/market/Visuals';
import { ActivityFormModal } from '@/components/modals/ActivityModals';
import { InquiryFormModal } from '@/components/modals/InquiryFormModal';
import { EmptyState, KpiTile } from '@/components/ui';
import { dayjs, formatDate, humanize } from '@/lib/format';
import { buildBoard, dailyCounts, fmtRate, fmtTonnes, toQuote } from '@/lib/market';
import type { Quote } from '@/lib/market';

/** The last 200 of each side are plenty for the board and the trend. */
const BOOK = { page_size: 200, sort_by: 'created_at', sort_dir: 'desc' } as const;

export function DashboardPage() {
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
  const overdue = counts?.overdue_activities ?? 0;

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

  return (
    <Stack gap="md">
      {/* -------------------------------------------------------------- header */}
      <Group className="page-head" justify="space-between" align="flex-start" gap="md">
        <div>
          <h1 className="page-title">Trading desk</h1>
          <div className="page-subtitle">
            {dayjs().format('dddd, D MMMM YYYY')}
            {bestSpread
              ? ` · widest live spread ${fmtRate(bestSpread.spread ?? 0)}/kg on ${bestSpread.productName}`
              : ' · no two-sided market yet'}
          </div>
        </div>
        <Group gap="xs">
          <Button
            variant="default"
            leftSection={<IconCalendarTime size={14} />}
            onClick={() => setActivityOpen(true)}
          >
            Schedule activity
          </Button>
          <Button leftSection={<IconPlus size={14} />} onClick={() => setInquiryOpen(true)}>
            New inquiry
          </Button>
        </Group>
      </Group>

      {/* ---------------------------------------------------------------- KPIs */}
      <div className="kpi-row">
        <KpiTile
          to="/inquiries/customer"
          label="Live demand"
          value={counts?.open_customer_inquiries ?? '—'}
          hint={`${fmtTonnes(demandTonnes)} wanted`}
          icon={<IconClipboardList size={14} />}
          accent="var(--demand)"
          spark={dailyCounts((demandRows?.items ?? []).map((r) => r.created_at))}
        />
        <KpiTile
          to="/inquiries/supplier"
          label="Live supply"
          value={counts?.open_supplier_inquiries ?? '—'}
          hint={`${fmtTonnes(supplyTonnes)} on offer`}
          icon={<IconPackageExport size={14} />}
          accent="var(--supply)"
          spark={dailyCounts((supplyRows?.items ?? []).map((r) => r.created_at))}
        />
        <KpiTile
          label="Best spread"
          value={bestSpread ? `${fmtRate(bestSpread.spread ?? 0)}` : '—'}
          hint={bestSpread ? `${bestSpread.productName} · per kg` : 'No two-sided market yet'}
          icon={<IconArrowsExchange size={14} />}
          accent="var(--brass)"
        />
        <KpiTile
          to="/activities/today"
          label="Today's activities"
          value={counts?.todays_activities ?? '—'}
          hint={overdue > 0 ? `${overdue} overdue from earlier days` : 'nothing overdue'}
          icon={<IconCalendarTime size={14} />}
          tone={overdue > 0 ? 'negative' : undefined}
          accent={overdue > 0 ? 'var(--negative)' : 'var(--border-strong)'}
        />
      </div>

      <div className="dash-grid">
        <Stack gap="md">
          {/* ------------------------------------------------------- rate board */}
          <section className="panel">
            <div className="panel-head">
              <div className="panel-title">Rate board</div>
              <Text fz="xs" c="ink.5">
                Cheapest live offer against best live demand, per product · ₹/kg
              </Text>
            </div>
            <RateBoard lines={board} limit={8} />
          </section>

          {/* ------------------------------------------------------ today's work */}
          <section className="panel">
            <div className="panel-head">
              <Group gap="xs" wrap="nowrap">
                <div className="panel-title">Today's queue</div>
                {overdue > 0 && (
                  <Text fz="xs" fw={600} c="rust.8">
                    {overdue} overdue
                  </Text>
                )}
              </Group>
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

          {/* ------------------------------------------------------------ trend */}
          {trendOptions.length > 0 && (
            <section className="panel">
              <div className="panel-head">
                <div className="panel-title">Rate history</div>
                <Group gap="md" wrap="nowrap">
                  <span className="side-tag" data-side="supply">
                    Supply
                  </span>
                  <span className="side-tag" data-side="demand">
                    Demand
                  </span>
                </Group>
              </div>
              {/* Product names are long; on a narrow screen the switcher
                  scrolls rather than stretching the card. */}
              <Box px="md" pt="sm" className="scroll-x">
                <SegmentedControl
                  value={activeTrend ?? undefined}
                  onChange={setTrendProduct}
                  data={trendOptions}
                />
              </Box>
              <Box px="sm" pb="sm" pt="xs">
                <TrendChart quotes={trendQuotes} />
              </Box>
            </section>
          )}

          {/* --------------------------------------------------- recent inquiries */}
          <section className="panel">
            <div className="panel-head">
              <div className="panel-title">Recent inquiries</div>
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
                  <Stack key={person.id} gap={4}>
                    <Group justify="space-between" wrap="nowrap">
                      <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                        <PartyAvatar name={person.name} size={22} />
                        <Text fz="sm" fw={500} c="ink.9" truncate>
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
                    <Box h={3} style={{ background: 'var(--border-soft)' }}>
                      <Box
                        h={3}
                        w={`${done}%`}
                        style={{ background: 'var(--mantine-color-ink-7)' }}
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
                <Group key={inquiry.id} gap="xs" wrap="nowrap" align="flex-start">
                  <PartyAvatar name={inquiry.party_name} size={24} />
                  <Stack gap={0} style={{ minWidth: 0, flex: 1 }}>
                    <Group justify="space-between" wrap="nowrap">
                      <Text
                        fz="sm"
                        fw={500}
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
                <Text fz="xs" fw={600} c="ink.7">
                  {counts.prospects} prospects
                </Text>
              ) : undefined
            }
          >
            {data?.recent_customers.length ? (
              data.recent_customers.slice(0, 5).map((party) => (
                <Group key={party.id} gap="xs" wrap="nowrap">
                  <PartyAvatar name={party.name} size={24} />
                  <Text
                    fz="sm"
                    component={Link}
                    to={`/parties/${party.id}`}
                    c="ink.9"
                    fw={500}
                    truncate
                    style={{ flex: 1 }}
                  >
                    {party.name}
                  </Text>
                  <Text fz="xs" c={party.stage === 'PROSPECT' ? 'amber.9' : 'ink.5'}>
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
