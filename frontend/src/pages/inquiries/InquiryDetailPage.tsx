/**
 * One recorded quotation, read like a trade ticket.
 *
 * The quote itself up top - rate, value, what and where - and beside it the
 * question a trader actually asks: how does this compare with everything else
 * live on the same product? Counterparty and record details below.
 */

import {
  ActionIcon,
  Anchor,
  Box,
  Button,
  Group,
  Loader,
  SimpleGrid,
  Stack,
  Text,
} from '@mantine/core';
import {
  IconArrowLeft,
  IconBox,
  IconLock,
  IconLockOpen,
  IconMapPin,
  IconPencil,
  IconPhone,
  IconScale,
  IconTruck,
  IconUser,
} from '@tabler/icons-react';
import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { inquiryApi, useApiMutation, useInquiries, useInquiry, useParty } from '@/api/hooks';
import type { InquiryStatus, LocationRef } from '@/api/types';
import { MarketMeter, PartyAvatar } from '@/components/market/Visuals';
import { StatusBadge } from '@/components/StatusBadge';
import { InquiryFormModal } from '@/components/modals/InquiryFormModal';
import { EmptyState } from '@/components/ui';
import { formatDateTime, formatMoney, formatQuantity, humanize, quoteValue } from '@/lib/format';
import { fmtRate, toQuote } from '@/lib/market';
import type { Quote } from '@/lib/market';

const TYPE_LABEL = {
  CUSTOMER: 'Customer inquiry',
  SUPPLIER: 'Supplier inquiry',
  TRANSPORT: 'Transport inquiry',
} as const;

function place(location: LocationRef | null | undefined) {
  if (!location) return '—';
  return [location.label, location.area, location.city, location.state].filter(Boolean).join(', ');
}

/** A labelled fact with an icon - the ticket's rows. */
function Fact({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <Group gap="sm" wrap="nowrap" align="flex-start">
      <Box
        w={34}
        h={34}
        style={{
          display: 'grid',
          placeItems: 'center',
          borderRadius: 10,
          background: 'var(--canvas)',
          color: 'var(--mantine-color-ink-6)',
          flexShrink: 0,
        }}
      >
        {icon}
      </Box>
      <Stack gap={0} style={{ minWidth: 0 }}>
        <Text className="block-label">{label}</Text>
        <Box fz="sm" c="ink.9" fw={500} mt={2}>
          {children}
        </Box>
      </Stack>
    </Group>
  );
}

export function InquiryDetailPage() {
  const { inquiryId } = useParams();
  const id = Number(inquiryId);
  const navigate = useNavigate();
  const { data: inquiry, isLoading, isError } = useInquiry(id);
  const [editOpen, setEditOpen] = useState(false);

  const partyRef =
    inquiry?.customer_detail?.customer ??
    inquiry?.supplier_detail?.supplier ??
    inquiry?.transport_detail?.transporter;
  // The inquiry carries only a party reference; the full record adds the phone.
  const { data: party } = useParty(partyRef?.id);

  const quote = inquiry?.customer_detail ?? inquiry?.supplier_detail ?? null;
  const productId = quote?.product_id;
  // Everything live on the same product, both sides, for the market panel.
  const { data: peers } = useInquiries(
    productId ? { product_id: productId, status: 'ACTIVE', page_size: 200 } : { page_size: 1 },
  );
  const market = useMemo(() => {
    if (!productId) return [];
    const list = (peers?.items ?? []).map(toQuote).filter((q): q is Quote => q !== null);
    // Make sure this quote is on the meter even when it is closed.
    if (inquiry && quote?.rate && !list.some((q) => q.id === inquiry.id)) {
      list.push({
        id: inquiry.id,
        side: inquiry.supplier_detail ? 'supply' : 'demand',
        productId,
        productName: quote.product.display_name,
        partyName: partyRef?.name ?? '',
        partyId: partyRef?.id ?? null,
        rate: Number(quote.rate),
        tonnes: null,
        createdAt: inquiry.created_at,
        active: inquiry.status === 'ACTIVE',
        location: null,
      });
    }
    return list;
  }, [peers, productId, inquiry, quote, partyRef]);

  const setStatus = useApiMutation((status: InquiryStatus) => inquiryApi.patch(id, { status }), {
    successMessage: 'Status updated',
  });

  if (isLoading) {
    return (
      <Group justify="center" py="xl">
        <Loader />
      </Group>
    );
  }
  if (isError || !inquiry) {
    return <EmptyState title="Inquiry not found" hint={`There is no inquiry #${id}.`} />;
  }

  const transport = inquiry.transport_detail;
  const isSupply = Boolean(inquiry.supplier_detail);
  const quantity = quote?.quantity ?? transport?.quantity;
  const unit = quote?.unit ?? transport?.unit;
  const closed = inquiry.status === 'CLOSED';
  const value = quote ? quoteValue(quote.quantity, quote.unit, quote.rate) : null;
  const rate = quote?.rate ? Number(quote.rate) : null;

  const supplyQuotes = market.filter((q) => q.side === 'supply' && q.active);
  const demandQuotes = market.filter((q) => q.side === 'demand' && q.active);
  const bestBuy = supplyQuotes.length ? Math.min(...supplyQuotes.map((q) => q.rate)) : null;
  const bestSell = demandQuotes.length ? Math.max(...demandQuotes.map((q) => q.rate)) : null;
  const ownSide = isSupply ? supplyQuotes : demandQuotes;
  const rank =
    rate === null
      ? null
      : 1 +
        ownSide.filter((q) => q.id !== inquiry.id && (isSupply ? q.rate < rate : q.rate > rate))
          .length;

  return (
    <Stack gap="md">
      {/* ------------------------------------------------------------- header */}
      <section className="record-head">
        <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
          <ActionIcon
            variant="default"
            size="input-sm"
            onClick={() => navigate(-1)}
            aria-label="Back"
          >
            <IconArrowLeft size={16} />
          </ActionIcon>
          <PartyAvatar name={partyRef?.name} size={32} />
          <Stack gap={2} style={{ minWidth: 0 }}>
            <Group gap="xs" wrap="nowrap">
              <Text className="record-title" truncate>
                {partyRef?.name}
              </Text>
              <StatusBadge value={inquiry.status} />
            </Group>
            <span
              className="side-tag"
              data-side={transport ? undefined : isSupply ? 'supply' : 'demand'}
              style={transport ? { color: 'var(--mantine-color-ink-6)' } : undefined}
            >
              {TYPE_LABEL[inquiry.inquiry_type]} · #{inquiry.id}
            </span>
          </Stack>
        </Group>
        <Group gap="xs" wrap="nowrap">
          <Button
            variant="default"
            leftSection={closed ? <IconLockOpen size={14} /> : <IconLock size={14} />}
            loading={setStatus.isPending}
            onClick={() => setStatus.mutate(closed ? 'ACTIVE' : 'CLOSED')}
          >
            {closed ? 'Reopen' : 'Close inquiry'}
          </Button>
          <Button leftSection={<IconPencil size={14} />} onClick={() => setEditOpen(true)}>
            Edit
          </Button>
        </Group>
      </section>

      {/* --------------------------------------------------------------- ticket */}
      <section className="panel">
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" p="md">
          <Stack gap={4}>
            <Text className="kpi-label">{transport ? 'Quoted freight' : 'Quoted rate'}</Text>
            <Group gap={8} align="baseline">
              <Text className="display-figure" fz={34} c="ink.9">
                {transport
                  ? transport.price
                    ? formatMoney(transport.price)
                    : '—'
                  : rate !== null
                    ? fmtRate(rate)
                    : '—'}
              </Text>
              {!transport && rate !== null && (
                <Text fz="sm" c="ink.5">
                  per kg
                </Text>
              )}
            </Group>
            <Text c="ink.5" fz="sm">
              {transport
                ? `for ${formatQuantity(quantity, unit)}, ${transport.pickup_location.city} → ${transport.delivery_location.city}`
                : value !== null
                  ? `≈ ${formatMoney(value)} for ${formatQuantity(quote?.quantity, quote?.unit)} of ${quote?.product.display_name}`
                  : rate === null
                    ? 'No rate recorded yet — edit to add one.'
                    : `${formatQuantity(quote?.quantity, quote?.unit)} of ${quote?.product.display_name}`}
            </Text>
          </Stack>

          {/* Market position: only meaningful for priced product quotes. */}
          {!transport && (
            <Box
              p="sm"
              style={{
                background: 'var(--surface-raised)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              <Group justify="space-between" mb={4}>
                <Text className="block-label">Market position</Text>
                <Group gap="sm">
                  <span className="side-tag" data-side="supply">
                    Offers
                  </span>
                  <span className="side-tag" data-side="demand">
                    Bids
                  </span>
                </Group>
              </Group>
              {market.length > 1 ? (
                <>
                  <MarketMeter quotes={market} highlightId={inquiry.id} height={70} />
                  <Group justify="space-between" mt="md" wrap="nowrap" gap="md">
                    <Stack gap={0}>
                      <Text fz="xs" c="ink.5">
                        {isSupply ? 'Rank among offers' : 'Rank among bids'}
                      </Text>
                      <Text fw={600} className="figure">
                        {rank !== null ? `${rank} of ${ownSide.length || 1}` : '—'}
                      </Text>
                    </Stack>
                    <Stack gap={0}>
                      <Text fz="xs" c="ink.5">
                        Best buy
                      </Text>
                      <Text fw={600} c="teal.9" className="figure">
                        {bestBuy !== null ? fmtRate(bestBuy) : '—'}
                      </Text>
                    </Stack>
                    <Stack gap={0}>
                      <Text fz="xs" c="ink.5">
                        Best sell
                      </Text>
                      <Text fw={600} c="navy.7" className="figure">
                        {bestSell !== null ? fmtRate(bestSell) : '—'}
                      </Text>
                    </Stack>
                    <Stack gap={0} align="flex-end">
                      <Text fz="xs" c="ink.5">
                        Spread
                      </Text>
                      <Text
                        fw={600}
                        className="figure"
                        c={
                          bestBuy !== null && bestSell !== null
                            ? bestSell >= bestBuy
                              ? 'moss.8'
                              : 'rust.8'
                            : 'ink.5'
                        }
                      >
                        {bestBuy !== null && bestSell !== null
                          ? `${bestSell >= bestBuy ? '+' : '−'}${fmtRate(Math.abs(bestSell - bestBuy))}`
                          : '—'}
                      </Text>
                    </Stack>
                  </Group>
                </>
              ) : (
                <Text fz="sm" c="ink.5" py="md">
                  This is the only live quote on {quote?.product.display_name}. Record more offers
                  and bids to see where it sits.
                </Text>
              )}
            </Box>
          )}
          {transport && (
            <Box
              p="sm"
              style={{
                background: 'var(--surface-raised)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              <Text className="block-label" mb="sm">
                Route
              </Text>
              <Group wrap="nowrap" gap="md" align="center">
                <Stack gap={0} style={{ flex: 1, minWidth: 0 }}>
                  <Text fz="xs" c="ink.5">
                    Pickup
                  </Text>
                  <Text fw={600} c="ink.9" truncate>
                    {transport.pickup_location.city}
                  </Text>
                  <Text fz="xs" c="ink.5" truncate>
                    {place(transport.pickup_location)}
                  </Text>
                </Stack>
                <Box style={{ flex: 1, position: 'relative', height: 30 }}>
                  <Box
                    pos="absolute"
                    left={0}
                    right={0}
                    top={14}
                    h={2}
                    style={{ background: 'var(--border-strong)' }}
                  />
                  <Box
                    pos="absolute"
                    left="50%"
                    top={2}
                    style={{
                      transform: 'translateX(-50%)',
                      background: 'var(--surface-raised)',
                      padding: '0 6px',
                      color: 'var(--mantine-color-ink-6)',
                    }}
                  >
                    <IconTruck size={22} />
                  </Box>
                </Box>
                <Stack gap={0} style={{ flex: 1, minWidth: 0 }} align="flex-end">
                  <Text fz="xs" c="ink.5">
                    Drop
                  </Text>
                  <Text fw={600} c="ink.9" truncate>
                    {transport.delivery_location.city}
                  </Text>
                  <Text fz="xs" c="ink.5" truncate ta="right">
                    {place(transport.delivery_location)}
                  </Text>
                </Stack>
              </Group>
            </Box>
          )}
        </SimpleGrid>
      </section>

      {/* -------------------------------------------------------------- details */}
      <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg">
        <section className="panel" style={{ gridColumn: 'span 2' }}>
          <div className="panel-head">
            <div className="panel-title">Quotation details</div>
          </div>
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md" p="md">
            {quote && (
              <Fact icon={<IconBox size={17} />} label="Product">
                {quote.product.display_name}
              </Fact>
            )}
            <Fact icon={<IconScale size={17} />} label="Quantity">
              {formatQuantity(quantity, unit)}
            </Fact>
            {quote && (
              <Fact icon={<IconMapPin size={17} />} label="Location">
                {place(quote.location)}
              </Fact>
            )}
            {transport && (
              <>
                <Fact icon={<IconMapPin size={17} />} label="Pickup">
                  {place(transport.pickup_location)}
                </Fact>
                <Fact icon={<IconMapPin size={17} />} label="Drop">
                  {place(transport.delivery_location)}
                </Fact>
              </>
            )}
            <Fact icon={<IconUser size={17} />} label="Recorded">
              {formatDateTime(inquiry.created_at)} · {inquiry.creator?.name ?? '—'}
            </Fact>
            {closed && (
              <Fact icon={<IconLock size={17} />} label="Closed">
                {formatDateTime(inquiry.closed_at)} · {inquiry.closer?.name ?? '—'}
              </Fact>
            )}
          </SimpleGrid>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div className="panel-title">Counterparty</div>
            <Text fz="xs" c="ink.5">
              {humanize(partyRef?.party_type)}
            </Text>
          </div>
          <Stack gap="sm" p="md">
            <Group gap="sm" wrap="nowrap">
              <PartyAvatar name={partyRef?.name} size={32} />
              <Stack gap={0} style={{ minWidth: 0 }}>
                {partyRef && (
                  <Anchor
                    component={Link}
                    to={`/parties/${partyRef.id}`}
                    fw={600}
                    c="ink.9"
                    truncate
                  >
                    {partyRef.name}
                  </Anchor>
                )}
                <Text fz="xs" c={partyRef?.stage === 'PROSPECT' ? 'amber.9' : 'ink.5'} fw={600}>
                  {partyRef?.stage === 'PROSPECT' ? 'Prospect' : 'Verified party'}
                </Text>
              </Stack>
            </Group>
            <Fact icon={<IconUser size={17} />} label="Contact">
              {party?.contact_person ?? '—'}
            </Fact>
            <Fact icon={<IconPhone size={17} />} label="Phone">
              {party?.phone ? (
                <Anchor href={`tel:${party.phone.replace(/\s+/g, '')}`} c="ink.9" fw={500}>
                  {party.phone}
                </Anchor>
              ) : (
                '—'
              )}
            </Fact>
          </Stack>
        </section>
      </SimpleGrid>

      {editOpen && <InquiryFormModal opened inquiry={inquiry} onClose={() => setEditOpen(false)} />}
    </Stack>
  );
}
