/**
 * One bid: what is on offer, who was asked, what they offered, and the call.
 *
 * The desk sees every name against every number. That is the only place in the
 * system where the whole room is visible - the participants themselves see a
 * single price to beat.
 */

import {
  ActionIcon,
  Alert,
  Badge,
  Box,
  Button,
  Card,
  CopyButton,
  Group,
  Loader,
  Modal,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core';
import {
  IconCheck,
  IconCopy,
  IconGavel,
  IconInfoCircle,
  IconLink,
  IconSearch,
  IconSend,
  IconTrash,
  IconTrophy,
  IconUserPlus,
} from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useListState } from '@/hooks/useListState';

import {
  bidApi,
  useApiMutation,
  useBid,
  useBidHistory,
  useBidParticipants,
  useBidQuotes,
} from '@/api/hooks';
import type { BidDetail, BidParticipant, BidQuote } from '@/api/types';
import { ParticipantPicker } from '@/components/bids/ParticipantPicker';
import { PARTY_TYPE_FOR } from '@/components/modals/BidFormModal';
import { DataTable } from '@/components/DataTable';
import type { Column } from '@/components/DataTable';
import { DetailLayout, RailSection } from '@/components/DetailLayout';
import { PartyAvatar } from '@/components/market/Visuals';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { Field } from '@/components/ui';
import { formatDateTime, formatQuantity } from '@/lib/format';
import { priceUnit } from './BidsPage';

export function BidDetailPage() {
  const { bidId } = useParams();
  const id = Number(bidId);
  const { data: bid, isLoading, dataUpdatedAt } = useBid(id);
  const { data: history } = useBidHistory(id, bid?.status === 'OPEN');

  const [inviteOpen, setInviteOpen] = useState(false);
  const [closeMode, setCloseMode] = useState<'keep' | 'none' | null>(null);
  const [awarding, setAwarding] = useState<BidQuote | null>(null);

  const publish = useApiMutation(() => bidApi.publish(id), { successMessage: 'Bid opened' });
  const close = useApiMutation((withoutWinner: boolean) => bidApi.close(id, withoutWinner), {
    successMessage: 'Bid closed',
  });
  const award = useApiMutation((quoteId: number) => bidApi.award(id, quoteId), {
    successMessage: 'Winner recorded',
  });
  const invite = useApiMutation((partyIds: number[]) => bidApi.addParticipants(id, partyIds), {
    successMessage: 'Participants invited',
  });
  const drop = useApiMutation(
    (participantId: number) => bidApi.removeParticipant(id, participantId),
    {
      successMessage: 'Participant removed',
    },
  );

  if (isLoading || !bid) {
    return (
      <Group justify="center" py="xl">
        <Loader />
      </Group>
    );
  }

  const isDraft = bid.status === 'DRAFT';
  const isOpen = bid.status === 'OPEN';
  const isClosed = bid.status === 'CLOSED';
  const unit = priceUnit(bid.bid_type);

  return (
    <>
      <PageHeader
        title={bid.title ?? `Bid #${bid.id}`}
        subtitle={
          <Group gap={8}>
            <StatusBadge value={bid.status} />
            <Text fz="sm" c="ink.5">
              #{bid.id} · raised by {bid.creator?.name ?? '—'} · {formatDateTime(bid.created_at)}
            </Text>
          </Group>
        }
        actions={
          <Group gap="sm">
            {isDraft && (
              <Button
                leftSection={<IconSend size={15} />}
                onClick={() => publish.mutate(undefined)}
                loading={publish.isPending}
                disabled={bid.participant_count === 0}
              >
                Open the bid
              </Button>
            )}
            {isOpen && (
              <>
                <Button variant="default" onClick={() => setCloseMode('none')}>
                  Close without winner
                </Button>
                <Button leftSection={<IconGavel size={15} />} onClick={() => setCloseMode('keep')}>
                  Close bid
                </Button>
              </>
            )}
          </Group>
        }
      />

      {isDraft && (
        <Alert color="amber" icon={<IconInfoCircle size={16} />} mb="md">
          This bid is a draft. Nobody can see it yet - open it to let the
          {bid.participant_count ? ` ${bid.participant_count} ` : ' '}
          invited participants quote.
        </Alert>
      )}
      {isClosed && bid.winner && (
        <Alert color="moss" icon={<IconTrophy size={16} />} mb="md">
          Awarded to <b>{bid.winner.party.name}</b> at {unit} {bid.winner.price}
          {bid.awarded_at ? ` · ${formatDateTime(bid.awarded_at)}` : ''}
        </Alert>
      )}
      {isClosed && !bid.winner && (
        <Alert color={bid.no_winner ? 'gray' : 'amber'} icon={<IconInfoCircle size={16} />} mb="md">
          {bid.no_winner
            ? 'Closed without a winner. The quotations below are kept for the record.'
            : 'Closed. Choose the offer you want with the Award button beside it - any offer, not ' +
              'necessarily the best number. Leaving it unawarded is fine too.'}
        </Alert>
      )}

      <DetailLayout
        rail={
          <>
            <RailSection label="The lot">
              <Stack gap="xs">
                {bid.product && <Field label="Product" value={bid.product.display_name} />}
                {bid.pickup_location && (
                  <Field
                    label="From"
                    value={[bid.pickup_location.area, bid.pickup_location.city]
                      .filter(Boolean)
                      .join(', ')}
                  />
                )}
                {bid.delivery_location && (
                  <Field
                    label="To"
                    value={[bid.delivery_location.area, bid.delivery_location.city]
                      .filter(Boolean)
                      .join(', ')}
                  />
                )}
                <Field label="Quantity" value={formatQuantity(bid.quantity, bid.unit)} />
                <Field
                  label="Closes"
                  value={bid.closes_at ? formatDateTime(bid.closes_at) : 'No deadline shown'}
                />
                <Field
                  label="Best so far"
                  value={
                    bid.best_price ? (
                      <Text fw={700} className="figure">
                        {unit} {bid.best_price}
                      </Text>
                    ) : (
                      '—'
                    )
                  }
                />
                {bid.specifications && <Field label="Notes" value={bid.specifications} />}
              </Stack>
            </RailSection>

            <RailSection
              label="History"
              action={
                history?.total ? (
                  <Text fz="xs" c="ink.5">
                    latest of {history.total}
                  </Text>
                ) : undefined
              }
            >
              <Stack gap={10}>
                {(history?.items ?? []).map((event, index) => (
                  <Box key={index}>
                    <Text fz="sm">{event.summary}</Text>
                    <Text fz="xs" c="ink.5">
                      {formatDateTime(event.at)}
                      {event.actor ? ` · ${event.actor}` : ''}
                    </Text>
                  </Box>
                ))}
                {!history?.items.length && (
                  <Text fz="sm" c="ink.5">
                    Nothing yet.
                  </Text>
                )}
              </Stack>
            </RailSection>
          </>
        }
      >
        <QuotesPanel bid={bid} live={isOpen} updatedAt={dataUpdatedAt} onAward={setAwarding} />

        <ParticipantsPanel
          bid={bid}
          live={isOpen}
          onInvite={() => setInviteOpen(true)}
          onRemove={(participantId) => drop.mutate(participantId)}
          removing={drop.isPending}
        />
      </DetailLayout>

      <Modal
        opened={inviteOpen}
        onClose={() => setInviteOpen(false)}
        title="Invite more participants"
        size="xl"
        centered
      >
        <InviteMore
          bid={bid}
          busy={invite.isPending}
          onInvite={(ids) => invite.mutate(ids, { onSuccess: () => setInviteOpen(false) })}
        />
      </Modal>

      <Modal
        opened={closeMode !== null}
        onClose={() => setCloseMode(null)}
        title={closeMode === 'none' ? 'Close without a winner' : 'Close the bid'}
        centered
      >
        <Stack gap="md">
          <Text fz="sm">
            {closeMode === 'none'
              ? 'Quotations stop and nobody is chosen. Every offer is kept for the record.'
              : 'Quotations stop. You can pick the winner afterwards, from the table.'}
          </Text>
          <Text fz="xs" c="ink.5">
            Participants are not notified either way.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCloseMode(null)}>
              Cancel
            </Button>
            <Button
              loading={close.isPending}
              onClick={() =>
                close.mutate(closeMode === 'none', { onSuccess: () => setCloseMode(null) })
              }
            >
              {closeMode === 'none' ? 'Close without winner' : 'Close bid'}
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={awarding !== null}
        onClose={() => setAwarding(null)}
        title="Award this bid"
        centered
      >
        <Stack gap="md">
          <Text fz="sm">
            Award to <b>{awarding?.party.name}</b> at {unit} {awarding?.price}?
          </Text>
          <Text fz="xs" c="ink.5">
            Recorded on this page. Nothing is sent to the participants.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setAwarding(null)}>
              Cancel
            </Button>
            <Button
              leftSection={<IconTrophy size={15} />}
              loading={award.isPending}
              onClick={() =>
                awarding && award.mutate(awarding.id, { onSuccess: () => setAwarding(null) })
              }
            >
              Award
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}

/**
 * The offers, a page at a time.
 *
 * A bid can hold a hundred participants, so this never asks for all of them:
 * it pages, searches by name and sorts, and the award button lives in its own
 * column so the desk can act on any row it can see.
 */
function QuotesPanel({
  bid,
  live,
  updatedAt,
  onAward,
}: {
  bid: BidDetail;
  live: boolean;
  updatedAt: number;
  onAward: (quote: BidQuote) => void;
}) {
  const list = useListState<Record<string, never>>({}, { sortBy: 'price', sortDir: 'desc' }, 10);
  const { data, isFetching } = useBidQuotes(bid.id, list.params, live);
  const unit = priceUnit(bid.bid_type);
  const isClosed = bid.status === 'CLOSED';
  const awaiting = isClosed && !bid.winner && !bid.no_winner && bid.quote_count > 0;

  const columns: Column<BidQuote>[] = [
    {
      key: 'participant',
      label: 'Participant',
      cardTitle: true,
      render: (quote) => (
        <Group gap={10} wrap="nowrap">
          <PartyAvatar name={quote.party.name} size={30} />
          <Stack gap={0} style={{ minWidth: 0 }}>
            <Group gap={6} wrap="nowrap">
              <Text
                fz="sm"
                fw={600}
                component={Link}
                to={`/parties/${quote.party.id}`}
                c="navy.7"
                truncate
              >
                {quote.party.name}
              </Text>
              {quote.price === bid.best_price && (
                <Badge size="xs" variant="light" color="brass">
                  Leading
                </Badge>
              )}
            </Group>
            <Text fz="xs" c="ink.5">
              {formatDateTime(quote.submitted_at)}
              {quote.revision > 1 ? ` · revised ${quote.revision - 1}×` : ''}
            </Text>
          </Stack>
        </Group>
      ),
    },
    {
      key: 'price',
      label: 'Price',
      align: 'right',
      sortable: true,
      render: (quote) => (
        <Text fw={700} className="figure">
          {unit} {quote.price}
        </Text>
      ),
    },
    {
      key: 'quantity',
      label: 'Quantity',
      align: 'right',
      render: (quote) => (
        <Text fz="sm" className="mono-tight">
          {quote.quantity ? formatQuantity(quote.quantity, bid.unit) : 'Full lot'}
        </Text>
      ),
    },
    {
      key: 'notes',
      label: 'Notes',
      render: (quote) => (
        <Text fz="xs" c="ink.6" lineClamp={2}>
          {quote.notes || '—'}
        </Text>
      ),
    },
    ...(isClosed
      ? [
          {
            key: 'decision',
            label: 'Decision',
            width: 128,
            render: (quote: BidQuote) =>
              quote.is_winner ? (
                <Badge color="moss" variant="filled" leftSection={<IconTrophy size={12} />}>
                  Winner
                </Badge>
              ) : (
                <Button
                  size="xs"
                  variant="filled"
                  leftSection={<IconTrophy size={13} />}
                  onClick={() => onAward(quote)}
                >
                  Award
                </Button>
              ),
          },
        ]
      : []),
  ];

  return (
    <Card padding={0} mb="lg">
      <Group justify="space-between" px="lg" py="md" gap="sm" wrap="wrap">
        <div>
          <Text fw={600}>Quotations</Text>
          <Text fz="xs" c="ink.5">
            {bid.quote_count} of {bid.participant_count} invited have quoted
            {bid.bid_type === 'CUSTOMER' ? ' · highest leads' : ' · lowest leads'}
            {awaiting ? ' · award one below' : ''}
          </Text>
        </div>
        <Group gap="sm" wrap="nowrap">
          <TextInput
            w={200}
            size="xs"
            placeholder="Find a participant"
            leftSection={<IconSearch size={14} />}
            value={list.q}
            onChange={(event) => list.setQ(event.currentTarget.value)}
          />
          {live && <LiveDot updatedAt={updatedAt} />}
        </Group>
      </Group>
      <DataTable
        framed={false}
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
        rowHighlight={(quote) => quote.is_winner || quote.price === bid.best_price}
        emptyMessage={bid.status === 'DRAFT' ? 'Not open yet' : 'No quotations yet'}
        emptyHint={
          bid.status === 'DRAFT'
            ? 'Open the bid, then share each participant’s link.'
            : 'Share the links below; offers appear here as they come in.'
        }
      />
    </Card>
  );
}

/** Everyone invited, a page at a time, with who has answered and who has not. */
function ParticipantsPanel({
  bid,
  live,
  onInvite,
  onRemove,
  removing,
}: {
  bid: BidDetail;
  live: boolean;
  onInvite: () => void;
  onRemove: (participantId: number) => void;
  removing: boolean;
}) {
  const [answered, setAnswered] = useState<string>('ALL');
  const list = useListState<{ quoted?: boolean }>({}, { sortBy: 'name', sortDir: 'asc' }, 10);
  const { data, isFetching } = useBidParticipants(
    bid.id,
    { ...list.params, quoted: answered === 'ALL' ? undefined : answered === 'QUOTED' },
    live,
  );
  const unit = priceUnit(bid.bid_type);
  const isClosed = bid.status === 'CLOSED';
  const silent = bid.participant_count - bid.quote_count;

  const columns: Column<BidParticipant>[] = [
    {
      key: 'party',
      label: 'Participant',
      cardTitle: true,
      render: (participant) => (
        <Group gap={10} wrap="nowrap">
          <PartyAvatar name={participant.party.name} size={30} />
          <Box style={{ minWidth: 0 }}>
            <Text fz="sm" fw={550} truncate>
              {participant.party.name}
            </Text>
            <Text fz="xs" c="ink.5">
              {participant.quote
                ? `Quoted ${unit} ${participant.quote.price}`
                : participant.last_opened_at
                  ? `Opened ${formatDateTime(participant.last_opened_at)}, no offer`
                  : 'Not opened yet'}
            </Text>
          </Box>
        </Group>
      ),
    },
    {
      key: 'links',
      label: 'Link',
      width: 150,
      render: (participant) => (
        <Group gap={4} wrap="nowrap">
          <CopyButton value={participant.bid_link}>
            {({ copied, copy }) => (
              <Tooltip label={copied ? 'Copied' : 'Copy this bid’s link'}>
                <ActionIcon variant="subtle" onClick={copy} aria-label="Copy bid link">
                  {copied ? <IconCheck size={16} /> : <IconCopy size={16} />}
                </ActionIcon>
              </Tooltip>
            )}
          </CopyButton>
          <CopyButton value={participant.portal_link}>
            {({ copied, copy }) => (
              <Tooltip label={copied ? 'Copied' : 'Copy their permanent portal link'}>
                <ActionIcon variant="subtle" onClick={copy} aria-label="Copy portal link">
                  {copied ? <IconCheck size={16} /> : <IconLink size={16} />}
                </ActionIcon>
              </Tooltip>
            )}
          </CopyButton>
          {!isClosed && !participant.quote && (
            <Tooltip label="Remove from this bid">
              <ActionIcon
                variant="subtle"
                color="rust"
                aria-label="Remove participant"
                loading={removing}
                onClick={() => onRemove(participant.id)}
              >
                <IconTrash size={16} />
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
      ),
    },
  ];

  return (
    <Card padding={0}>
      <Group justify="space-between" px="lg" py="md" gap="sm" wrap="wrap">
        <div>
          <Text fw={600}>Participants</Text>
          <Text fz="xs" c="ink.5">
            {bid.participant_count} invited
            {silent > 0 ? ` · ${silent} yet to quote` : ' · everyone has quoted'}
          </Text>
        </div>
        <Group gap="sm" wrap="nowrap">
          <TextInput
            w={180}
            size="xs"
            placeholder="Find a participant"
            leftSection={<IconSearch size={14} />}
            value={list.q}
            onChange={(event) => list.setQ(event.currentTarget.value)}
          />
          <SegmentedControl
            size="xs"
            value={answered}
            onChange={setAnswered}
            data={[
              { value: 'ALL', label: 'All' },
              { value: 'QUOTED', label: 'Quoted' },
              { value: 'SILENT', label: 'Yet to' },
            ]}
          />
          {!isClosed && (
            <Button
              size="xs"
              variant="light"
              leftSection={<IconUserPlus size={14} />}
              onClick={onInvite}
            >
              Invite more
            </Button>
          )}
        </Group>
      </Group>
      <DataTable
        framed={false}
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
        emptyMessage="Nobody invited yet"
        emptyHint="Invite the parties who should quote."
      />
    </Card>
  );
}

/** "This is moving on its own" - with the time of the last change. */
function LiveDot({ updatedAt }: { updatedAt: number }) {
  const [, tick] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => tick((value) => value + 1), 15_000);
    return () => window.clearInterval(timer);
  }, []);
  const seconds = Math.max(0, Math.round((Date.now() - updatedAt) / 1000));
  return (
    <Group gap={6} wrap="nowrap">
      <span className="live-dot" />
      <Text fz="xs" c="ink.5">
        Live · checked {seconds < 20 ? 'just now' : `${Math.round(seconds / 60) || 1} min ago`}
      </Text>
    </Group>
  );
}

function InviteMore({
  bid,
  busy,
  onInvite,
}: {
  bid: BidDetail;
  busy: boolean;
  onInvite: (ids: number[]) => void;
}) {
  const [selected, setSelected] = useState<number[]>([]);
  // Only to tick the ones already in: the server ignores a repeat invitation
  // anyway, so this is a courtesy rather than the rule.
  const { data: invited } = useBidParticipants(bid.id, { page_size: 500 });

  return (
    <Stack gap="lg">
      <ParticipantPicker
        partyType={PARTY_TYPE_FOR[bid.bid_type]}
        selected={selected}
        onChange={setSelected}
        locked={(invited?.items ?? []).map((participant) => participant.party.id)}
      />
      <Group justify="flex-end">
        <Button disabled={!selected.length} loading={busy} onClick={() => onInvite(selected)}>
          Invite {selected.length || ''}
        </Button>
      </Group>
    </Stack>
  );
}
