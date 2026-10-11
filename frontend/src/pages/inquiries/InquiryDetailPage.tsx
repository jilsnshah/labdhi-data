/**
 * One recorded quotation. Everything about it fits on a single card: the rate,
 * what and where, and who quoted it - with Edit and a one-click status switch.
 */

import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Loader,
  SimpleGrid,
  Stack,
  Text,
} from '@mantine/core';
import { IconArrowLeft, IconLock, IconLockOpen, IconPencil } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { inquiryApi, useApiMutation, useInquiry, useParty } from '@/api/hooks';
import type { InquiryStatus, LocationRef } from '@/api/types';
import { RailHighlight, RailSection } from '@/components/DetailLayout';
import { StatusBadge } from '@/components/StatusBadge';
import { InquiryFormModal } from '@/components/modals/InquiryFormModal';
import { EmptyState, Field } from '@/components/ui';
import {
  formatDateTime,
  formatMoney,
  formatQuantity,
  formatRate,
  humanize,
  quoteValue,
} from '@/lib/format';

const TYPE_LABEL = {
  CUSTOMER: 'Customer inquiry',
  SUPPLIER: 'Supplier inquiry',
  TRANSPORT: 'Transport inquiry',
} as const;

function place(location: LocationRef | null | undefined) {
  if (!location) return '—';
  return [location.label, location.city, location.state].filter(Boolean).join(', ');
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

  const quote = inquiry.customer_detail ?? inquiry.supplier_detail;
  const transport = inquiry.transport_detail;
  const quantity = quote?.quantity ?? transport?.quantity;
  const unit = quote?.unit ?? transport?.unit;
  const closed = inquiry.status === 'CLOSED';
  const value = quote ? quoteValue(quote.quantity, quote.unit, quote.rate) : null;

  return (
    <div className="page">
      <Group justify="space-between" align="flex-start" mb="lg" wrap="nowrap">
        <Group gap="sm" align="flex-start" wrap="nowrap">
          <ActionIcon variant="default" size={34} onClick={() => navigate(-1)} aria-label="Back">
            <IconArrowLeft size={16} />
          </ActionIcon>
          <Stack gap={2}>
            <Group gap="sm">
              <Text fz={22} fw={600} lh={1.2}>
                #{inquiry.id} {partyRef?.name}
              </Text>
              <StatusBadge value={inquiry.status} />
            </Group>
            <Text fz="sm" c="ink.5">
              {TYPE_LABEL[inquiry.inquiry_type]}
              {quote ? ` · ${quote.product.display_name}` : ''}
              {quantity ? ` · ${formatQuantity(quantity, unit)}` : ''}
            </Text>
          </Stack>
        </Group>
        <Group gap="xs" wrap="nowrap">
          <Button
            variant="default"
            leftSection={closed ? <IconLockOpen size={15} /> : <IconLock size={15} />}
            loading={setStatus.isPending}
            onClick={() => setStatus.mutate(closed ? 'ACTIVE' : 'CLOSED')}
          >
            {closed ? 'Reopen' : 'Close inquiry'}
          </Button>
          <Button leftSection={<IconPencil size={15} />} onClick={() => setEditOpen(true)}>
            Edit
          </Button>
        </Group>
      </Group>

      <Card withBorder padding={0} radius="md" maw={980}>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing={0}>
          <Stack gap={0} style={{ borderRight: '1px solid var(--hairline)' }}>
            {transport ? (
              <RailHighlight
                label="Quoted price"
                value={transport.price ? formatMoney(transport.price) : '—'}
                caption={transport.price ? 'for the trip' : 'No price recorded yet'}
              />
            ) : (
              <RailHighlight
                label="Quoted rate"
                value={quote?.rate ? formatRate(quote.rate) : '—'}
                caption={
                  value !== null
                    ? `≈ ${formatMoney(value)} for ${formatQuantity(quote?.quantity, quote?.unit)}`
                    : quote?.rate
                      ? undefined
                      : 'No rate recorded yet'
                }
              />
            )}
            <RailSection label="Quotation">
              {quote && <Field label="Product" value={quote.product.display_name} />}
              <Field label="Quantity" value={formatQuantity(quantity, unit)} />
              {quote && <Field label="Location" value={place(quote.location)} />}
              {transport && (
                <>
                  <Field label="Pickup" value={place(transport.pickup_location)} />
                  <Field label="Drop" value={place(transport.delivery_location)} />
                </>
              )}
              <Field label="Status" value={humanize(inquiry.status)} />
            </RailSection>
          </Stack>

          <Stack gap={0}>
            <RailSection label={humanize(partyRef?.party_type)}>
              {partyRef && (
                <Group gap="xs">
                  <Anchor component={Link} to={`/parties/${partyRef.id}`} fw={600} c="ink.9">
                    {partyRef.name}
                  </Anchor>
                  {partyRef.stage === 'PROSPECT' && (
                    <Badge size="xs" variant="light" color="amber">
                      Prospect
                    </Badge>
                  )}
                </Group>
              )}
              <Field label="Contact" value={party?.contact_person ?? '—'} width={96} />
              <Field
                label="Phone"
                width={96}
                value={
                  party?.phone ? (
                    <Anchor href={`tel:${party.phone.replace(/\s+/g, '')}`} fz="sm" c="ink.9">
                      {party.phone}
                    </Anchor>
                  ) : (
                    '—'
                  )
                }
              />
            </RailSection>
            <RailSection label="Record">
              <Field
                label="Recorded"
                width={96}
                value={`${formatDateTime(inquiry.created_at)} by ${inquiry.creator?.name ?? '—'}`}
              />
              {closed && (
                <Field
                  label="Closed"
                  width={96}
                  value={`${formatDateTime(inquiry.closed_at)} by ${inquiry.closer?.name ?? '—'}`}
                />
              )}
              <Field label="Updated" width={96} value={formatDateTime(inquiry.updated_at)} />
            </RailSection>
          </Stack>
        </SimpleGrid>
      </Card>

      {editOpen && <InquiryFormModal opened inquiry={inquiry} onClose={() => setEditOpen(false)} />}
    </div>
  );
}
