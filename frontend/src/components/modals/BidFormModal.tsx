/**
 * Raising a bid: what is on offer, and who gets asked.
 *
 * It opens as a draft. Nothing is visible to a participant until the desk
 * presses Open on the bid's own page, so a half-written lot never goes out.
 */

import { Button, Group, Modal, NumberInput, Select, Stack, Text, Textarea } from '@mantine/core';
import { DateTimePicker } from '@mantine/dates';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { bidApi, useApiMutation } from '@/api/hooks';
import type { BidType, PartyType, QuantityUnit } from '@/api/types';
import { ParticipantPicker } from '@/components/bids/ParticipantPicker';
import { EntitySelect } from '@/components/EntitySelect';

const UNITS: QuantityUnit[] = ['MT', 'KG', 'BAG', 'LITRE', 'PIECE'];

export const PARTY_TYPE_FOR: Record<BidType, PartyType> = {
  CUSTOMER: 'CUSTOMER',
  SUPPLIER: 'SUPPLIER',
  TRANSPORT: 'TRANSPORTER',
};

const COPY: Record<BidType, { title: string; lead: string; who: string }> = {
  CUSTOMER: {
    title: 'New customer bid',
    lead: 'Material you are selling. Customers quote against each other; the highest price leads.',
    who: 'Customers invited to quote',
  },
  SUPPLIER: {
    title: 'New supplier bid',
    lead: 'Material you want to buy. Suppliers quote against each other; the lowest price leads.',
    who: 'Suppliers invited to quote',
  },
  TRANSPORT: {
    title: 'New transport bid',
    lead: 'A load to move. Transporters quote against each other; the lowest price leads.',
    who: 'Transporters invited to quote',
  },
};

export function BidFormModal({ bidType, onClose }: { bidType: BidType; onClose: () => void }) {
  const navigate = useNavigate();
  const copy = COPY[bidType];
  const isTransport = bidType === 'TRANSPORT';

  const [productId, setProductId] = useState<number | null>(null);
  const [pickupId, setPickupId] = useState<number | null>(null);
  const [deliveryId, setDeliveryId] = useState<number | null>(null);
  const [quantity, setQuantity] = useState<string | number>('');
  const [unit, setUnit] = useState<QuantityUnit>('MT');
  const [specifications, setSpecifications] = useState('');
  const [closesAt, setClosesAt] = useState<string | null>(null);
  const [partyIds, setPartyIds] = useState<number[]>([]);

  const create = useApiMutation((body: unknown) => bidApi.create(body), {
    successMessage: 'Bid saved as a draft',
  });

  const missing = !quantity
    ? 'Enter the quantity'
    : isTransport
      ? !pickupId || !deliveryId
        ? 'Choose where it moves from and to'
        : pickupId === deliveryId
          ? 'Pickup and delivery must differ'
          : null
      : !productId
        ? 'Choose the product'
        : null;

  const submit = () =>
    create.mutate(
      {
        bid_type: bidType,
        product_id: isTransport ? null : productId,
        pickup_location_id: isTransport ? pickupId : null,
        delivery_location_id: isTransport ? deliveryId : null,
        quantity: String(quantity),
        unit,
        specifications: specifications.trim() || null,
        closes_at: closesAt ? new Date(closesAt).toISOString() : null,
        party_ids: partyIds,
      },
      { onSuccess: (bid) => navigate(`/bids/${bid.id}`) },
    );

  return (
    <Modal opened onClose={onClose} title={copy.title} size="xl" centered>
      <Stack gap="lg">
        <Text fz="sm" c="ink.6">
          {copy.lead}
        </Text>

        <Stack gap="sm">
          {isTransport ? (
            <Group grow align="flex-start">
              <div>
                <Text fz="sm" fw={500} mb={4}>
                  Pick up from <span style={{ color: 'var(--mantine-color-rust-6)' }}>*</span>
                </Text>
                <EntitySelect kind="location" value={pickupId} onChange={setPickupId} />
              </div>
              <div>
                <Text fz="sm" fw={500} mb={4}>
                  Deliver to <span style={{ color: 'var(--mantine-color-rust-6)' }}>*</span>
                </Text>
                <EntitySelect kind="location" value={deliveryId} onChange={setDeliveryId} />
              </div>
            </Group>
          ) : (
            <div>
              <Text fz="sm" fw={500} mb={4}>
                Product <span style={{ color: 'var(--mantine-color-rust-6)' }}>*</span>
              </Text>
              <EntitySelect kind="product" value={productId} onChange={setProductId} />
            </div>
          )}

          <Group grow align="flex-end">
            <NumberInput
              label={isTransport ? 'Load' : 'Quantity'}
              required
              min={0}
              decimalScale={3}
              value={quantity}
              onChange={setQuantity}
            />
            <Select
              label="Unit"
              data={UNITS}
              value={unit}
              onChange={(value) => value && setUnit(value as QuantityUnit)}
              allowDeselect={false}
            />
            <DateTimePicker
              label="Closes at (optional)"
              placeholder="No deadline shown"
              value={closesAt}
              onChange={setClosesAt}
              clearable
            />
          </Group>

          <Textarea
            label={isTransport ? 'What is moving' : 'Specifications'}
            placeholder={
              isTransport
                ? 'Packing, loading window, anything the transporter must know.'
                : 'Packing, origin, payment terms - whatever the bidders need.'
            }
            autosize
            minRows={2}
            value={specifications}
            onChange={(event) => setSpecifications(event.currentTarget.value)}
          />
        </Stack>

        <div>
          <Text fz="sm" fw={600} mb={6}>
            {copy.who}
          </Text>
          <ParticipantPicker
            partyType={PARTY_TYPE_FOR[bidType]}
            selected={partyIds}
            onChange={setPartyIds}
          />
        </div>

        <Group justify="space-between">
          <Text fz="xs" c="ink.5">
            {missing ?? 'Saved as a draft. Open it when you are ready to send the links.'}
          </Text>
          <Group gap="sm">
            <Button variant="default" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={submit} loading={create.isPending} disabled={Boolean(missing)}>
              Create draft
            </Button>
          </Group>
        </Group>
      </Stack>
    </Modal>
  );
}
