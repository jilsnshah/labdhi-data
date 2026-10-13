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
  Stack,
  Table,
  Text,
  Tooltip,
} from '@mantine/core';
import {
  IconCheck,
  IconCopy,
  IconGavel,
  IconInfoCircle,
  IconLink,
  IconSend,
  IconTrash,
  IconTrophy,
  IconUserPlus,
} from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { bidApi, useApiMutation, useBid, useBidHistory } from '@/api/hooks';
import type { BidDetail, BidQuote } from '@/api/types';
import { ParticipantPicker } from '@/components/bids/ParticipantPicker';
import { PARTY_TYPE_FOR } from '@/components/modals/BidFormModal';
import { DetailLayout, RailSection } from '@/components/DetailLayout';
import { PartyAvatar } from '@/components/market/Visuals';
import { PageHeader } from '@/components/PageHeader';
import { StatusBadge } from '@/components/StatusBadge';
import { EmptyState, Field } from '@/components/ui';
import { formatDateTime, formatQuantity, humanize } from '@/lib/format';
import { priceUnit } from './BidsPage';

export function BidDetailPage() {
  const { bidId } = useParams();
  const id = Number(bidId);
  const { data: bid, isLoading } = useBid(id);
  const { data: history } = useBidHistory(id);

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
  const quoted = bid.quotes.length;
  const silent = bid.participants.filter((participant) => !participant.quote);

  return (
    <>
      <PageHeader
        eyebrow={`${humanize(bid.bid_type)} bid`}
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
                disabled={!bid.participants.length}
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
          This bid is a draft. Nobody can see it yet - open it to let the invited
          {bid.participants.length ? ` ${bid.participants.length} ` : ' '}
          participants quote.
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
            : 'Closed. Pick the offer you want from the table below.'}
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

            <RailSection label="History">
              <Stack gap={10}>
                {(history ?? []).map((event, index) => (
                  <Box key={index}>
                    <Text fz="sm">{event.summary}</Text>
                    <Text fz="xs" c="ink.5">
                      {formatDateTime(event.at)}
                      {event.actor ? ` · ${event.actor}` : ''}
                    </Text>
                  </Box>
                ))}
                {!history?.length && (
                  <Text fz="sm" c="ink.5">
                    Nothing yet.
                  </Text>
                )}
              </Stack>
            </RailSection>
          </>
        }
      >
        <Card padding={0} mb="lg">
          <Group justify="space-between" px="lg" py="md">
            <div>
              <Text fw={600}>Quotations</Text>
              <Text fz="xs" c="ink.5">
                {quoted} of {bid.participants.length} invited have quoted
                {bid.bid_type === 'CUSTOMER' ? ' · highest leads' : ' · lowest leads'}
              </Text>
            </div>
          </Group>
          {quoted ? (
            <Table className="data-table" verticalSpacing={12} horizontalSpacing="lg" fz="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Participant</Table.Th>
                  <Table.Th style={{ textAlign: 'right' }}>Price</Table.Th>
                  <Table.Th style={{ textAlign: 'right' }}>Quantity</Table.Th>
                  <Table.Th>Notes</Table.Th>
                  <Table.Th>Submitted</Table.Th>
                  {isClosed && <Table.Th />}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {bid.quotes.map((quote, index) => (
                  <Table.Tr key={quote.id}>
                    <Table.Td data-label="Participant" data-card="title">
                      <Group gap={10} wrap="nowrap">
                        <PartyAvatar name={quote.party.name} size={30} />
                        <Stack gap={0}>
                          <Group gap={6}>
                            <Text
                              fz="sm"
                              fw={600}
                              component={Link}
                              to={`/parties/${quote.party.id}`}
                              c="accent.9"
                            >
                              {quote.party.name}
                            </Text>
                            {index === 0 && (
                              <Badge size="xs" variant="light" color="brass">
                                Leading
                              </Badge>
                            )}
                            {quote.is_winner && (
                              <Badge size="xs" color="moss">
                                Winner
                              </Badge>
                            )}
                          </Group>
                          {quote.revision > 1 && (
                            <Text fz="xs" c="ink.5">
                              revised {quote.revision - 1}×
                            </Text>
                          )}
                        </Stack>
                      </Group>
                    </Table.Td>
                    <Table.Td data-label="Price" align="right">
                      <Text fw={700} className="figure">
                        {unit} {quote.price}
                      </Text>
                    </Table.Td>
                    <Table.Td data-label="Quantity" align="right">
                      <Text fz="sm" className="mono-tight">
                        {quote.quantity ? formatQuantity(quote.quantity, bid.unit) : 'Full lot'}
                      </Text>
                    </Table.Td>
                    <Table.Td data-label="Notes">
                      <Text fz="xs" c="ink.6" lineClamp={2}>
                        {quote.notes || '—'}
                      </Text>
                    </Table.Td>
                    <Table.Td data-label="Submitted">
                      <Text fz="xs" c="ink.5">
                        {formatDateTime(quote.submitted_at)}
                      </Text>
                    </Table.Td>
                    {isClosed && (
                      <Table.Td data-label="">
                        {quote.is_winner ? (
                          <Badge color="moss" variant="light">
                            Awarded
                          </Badge>
                        ) : (
                          <Button size="xs" variant="light" onClick={() => setAwarding(quote)}>
                            Award
                          </Button>
                        )}
                      </Table.Td>
                    )}
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          ) : (
            <Box px="lg" pb="lg">
              <EmptyState
                title={isDraft ? 'Not open yet' : 'No quotations yet'}
                hint={
                  isDraft
                    ? 'Open the bid, then share each participant’s link.'
                    : 'Share the links below; offers appear here as they come in.'
                }
                compact
              />
            </Box>
          )}
        </Card>

        <Card padding={0}>
          <Group justify="space-between" px="lg" py="md">
            <div>
              <Text fw={600}>Participants</Text>
              <Text fz="xs" c="ink.5">
                {silent.length ? `${silent.length} yet to quote` : 'everyone invited has quoted'}
              </Text>
            </div>
            {!isClosed && (
              <Button
                size="xs"
                variant="light"
                leftSection={<IconUserPlus size={14} />}
                onClick={() => setInviteOpen(true)}
              >
                Invite more
              </Button>
            )}
          </Group>
          <Stack gap={0}>
            {bid.participants.map((participant) => (
              <Group
                key={participant.id}
                justify="space-between"
                px="lg"
                py="sm"
                wrap="nowrap"
                style={{ borderTop: '1px solid var(--hairline-soft)' }}
              >
                <Group gap={10} wrap="nowrap" style={{ minWidth: 0 }}>
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
                        onClick={() => drop.mutate(participant.id)}
                      >
                        <IconTrash size={16} />
                      </ActionIcon>
                    </Tooltip>
                  )}
                </Group>
              </Group>
            ))}
            {!bid.participants.length && (
              <Box px="lg" pb="lg">
                <EmptyState
                  title="Nobody invited yet"
                  hint="Invite the parties who should quote."
                  compact
                />
              </Box>
            )}
          </Stack>
        </Card>
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
  return (
    <Stack gap="lg">
      <ParticipantPicker
        partyType={PARTY_TYPE_FOR[bid.bid_type]}
        selected={selected}
        onChange={setSelected}
        locked={bid.participants.map((participant) => participant.party.id)}
      />
      <Group justify="flex-end">
        <Button disabled={!selected.length} loading={busy} onClick={() => onInvite(selected)}>
          Invite {selected.length || ''}
        </Button>
      </Group>
    </Stack>
  );
}
