/**
 * Record a quotation - or edit one. One modal for all three inquiry types.
 *
 * Supplier and customer: party, product, quantity, location, rate (₹/kg), status.
 * Transport: transporter, quantity, pickup, drop, price (₹), status.
 * A party or location that is not on file yet can be added without leaving.
 */

import {
  Button,
  Group,
  Modal,
  NumberInput,
  SegmentedControl,
  Select,
  Stack,
  Text,
} from '@mantine/core';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { inquiryApi, useApiMutation } from '@/api/hooks';
import type {
  InquiryDetail,
  InquiryStatus,
  InquiryType,
  LocationRef,
  PartyType,
  QuantityUnit,
} from '@/api/types';
import { EntitySelect } from '@/components/EntitySelect';
import { LocationPicker } from '@/components/LocationPicker';
import { PartyPicker } from '@/components/PartyPicker';

const UNITS: QuantityUnit[] = ['MT', 'KG', 'BAG', 'LITRE', 'PIECE'];

const PARTY_TYPE: Record<InquiryType, PartyType> = {
  CUSTOMER: 'CUSTOMER',
  SUPPLIER: 'SUPPLIER',
  TRANSPORT: 'TRANSPORTER',
};

const TITLE: Record<InquiryType, string> = {
  CUSTOMER: 'customer inquiry',
  SUPPLIER: 'supplier inquiry',
  TRANSPORT: 'transport inquiry',
};

function placeName(location: LocationRef | null | undefined): string | null {
  if (!location) return null;
  return [location.label, location.city, location.state].filter(Boolean).join(' - ');
}

/** Pull the editable values out of an existing inquiry, whichever type it is. */
function initialValues(inquiry?: InquiryDetail | null) {
  const supplyOrDemand = inquiry?.customer_detail ?? inquiry?.supplier_detail ?? null;
  const transport = inquiry?.transport_detail ?? null;
  const party =
    inquiry?.customer_detail?.customer ??
    inquiry?.supplier_detail?.supplier ??
    transport?.transporter ??
    null;
  return {
    partyId: party?.id ?? null,
    partyName: party?.name ?? null,
    productId: supplyOrDemand?.product_id ?? null,
    productName: supplyOrDemand?.product.display_name ?? null,
    quantity: Number(supplyOrDemand?.quantity ?? transport?.quantity ?? 0) || ('' as const),
    unit: (supplyOrDemand?.unit ?? transport?.unit ?? 'MT') as QuantityUnit,
    locationId: supplyOrDemand?.location_id ?? null,
    locationName: placeName(supplyOrDemand?.location),
    rate: supplyOrDemand?.rate ? Number(supplyOrDemand.rate) : ('' as const),
    pickupId: transport?.pickup_location_id ?? null,
    pickupName: placeName(transport?.pickup_location),
    dropId: transport?.delivery_location_id ?? null,
    dropName: placeName(transport?.delivery_location),
    price: transport?.price ? Number(transport.price) : ('' as const),
    status: (inquiry?.status ?? 'ACTIVE') as InquiryStatus,
  };
}

const money = (value: number | string) => (value === '' ? null : String(value));

export function InquiryFormModal({
  opened,
  onClose,
  inquiry,
  defaultType = 'CUSTOMER',
  lockType = false,
  partyId,
  partyLabel,
  navigateOnCreate = true,
}: {
  opened: boolean;
  onClose: () => void;
  /** Present when editing; the type is then fixed. */
  inquiry?: InquiryDetail | null;
  defaultType?: InquiryType;
  lockType?: boolean;
  /** Pre-select (and lock) the party, e.g. when opened from a party page. */
  partyId?: number;
  partyLabel?: string;
  navigateOnCreate?: boolean;
}) {
  const navigate = useNavigate();
  const editing = Boolean(inquiry);
  const start = initialValues(inquiry);

  const [type, setType] = useState<InquiryType>(inquiry?.inquiry_type ?? defaultType);
  const [party, setParty] = useState<number | null>(partyId ?? start.partyId);
  const [partyName, setPartyName] = useState<string | null>(partyLabel ?? start.partyName);
  const [product, setProduct] = useState<number | null>(start.productId);
  const [quantity, setQuantity] = useState<number | string>(start.quantity);
  const [unit, setUnit] = useState<QuantityUnit>(start.unit);
  const [location, setLocation] = useState<number | null>(start.locationId);
  const [locationName, setLocationName] = useState<string | null>(start.locationName);
  const [rate, setRate] = useState<number | string>(start.rate);
  const [pickup, setPickup] = useState<number | null>(start.pickupId);
  const [pickupName, setPickupName] = useState<string | null>(start.pickupName);
  const [drop, setDrop] = useState<number | null>(start.dropId);
  const [dropName, setDropName] = useState<string | null>(start.dropName);
  const [price, setPrice] = useState<number | string>(start.price);
  const [status, setStatus] = useState<InquiryStatus>(start.status);

  const isTransport = type === 'TRANSPORT';

  const save = useApiMutation(
    (body: unknown) => (inquiry ? inquiryApi.patch(inquiry.id, body) : inquiryApi.create(body)),
    { successMessage: editing ? 'Inquiry updated' : 'Inquiry recorded' },
  );

  const submit = async () => {
    const qty = { quantity: String(quantity), unit };
    let body: Record<string, unknown>;
    if (inquiry) {
      body = isTransport
        ? {
            status,
            party_id: party,
            ...qty,
            pickup_location_id: pickup,
            delivery_location_id: drop,
            price: money(price),
          }
        : {
            status,
            party_id: party,
            product_id: product,
            ...qty,
            location_id: location,
            rate: money(rate),
          };
    } else if (type === 'TRANSPORT') {
      body = {
        inquiry_type: type,
        status,
        transport: {
          transporter_id: party,
          ...qty,
          pickup_location_id: pickup,
          delivery_location_id: drop,
          price: money(price),
        },
      };
    } else {
      const block = {
        product_id: product,
        ...qty,
        location_id: location,
        rate: money(rate),
      };
      body =
        type === 'CUSTOMER'
          ? { inquiry_type: type, status, customer: { customer_id: party, ...block } }
          : { inquiry_type: type, status, supplier: { supplier_id: party, ...block } };
    }
    const saved = await save.mutateAsync(body);
    onClose();
    if (!editing && navigateOnCreate) navigate(`/inquiries/${saved.id}`);
  };

  const sameRoute = pickup !== null && drop !== null && pickup === drop;
  const valid =
    party !== null &&
    Number(quantity) > 0 &&
    (isTransport ? pickup !== null && drop !== null && !sameRoute : product !== null);

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={editing ? `Edit ${TITLE[type]} #${inquiry?.id}` : `New ${TITLE[type]}`}
      size="lg"
    >
      <Stack gap="md">
        {!editing && !lockType && (
          <SegmentedControl
            fullWidth
            value={type}
            onChange={(value) => {
              setType(value as InquiryType);
              setParty(null);
              setPartyName(null);
            }}
            data={[
              { label: 'Customer', value: 'CUSTOMER' },
              { label: 'Supplier', value: 'SUPPLIER' },
              { label: 'Transport', value: 'TRANSPORT' },
            ]}
          />
        )}

        <PartyPicker
          key={type}
          partyType={PARTY_TYPE[type]}
          value={party}
          label={partyName}
          disabled={Boolean(partyId)}
          onChange={(id, name) => {
            setParty(id);
            if (name) setPartyName(name);
          }}
        />

        {!isTransport && (
          <EntitySelect
            kind="product"
            label="Product"
            required
            value={product}
            initialLabel={start.productName}
            onChange={setProduct}
          />
        )}

        <Group grow align="flex-start">
          <NumberInput
            label="Quantity"
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
          {isTransport ? (
            <NumberInput
              label="Price (₹)"
              min={0}
              decimalScale={2}
              thousandSeparator=","
              prefix="₹"
              value={price}
              onChange={setPrice}
            />
          ) : (
            <NumberInput
              label="Rate (₹/kg)"
              min={0}
              decimalScale={2}
              prefix="₹"
              suffix="/kg"
              value={rate}
              onChange={setRate}
            />
          )}
        </Group>

        {isTransport ? (
          <>
            <LocationPicker
              label="Pickup location"
              required
              value={pickup}
              initialLabel={pickupName}
              onChange={(id, name) => {
                setPickup(id);
                if (name) setPickupName(name);
              }}
            />
            <LocationPicker
              label="Drop location"
              required
              value={drop}
              initialLabel={dropName}
              error={sameRoute ? 'Pick a different place from the pickup' : null}
              onChange={(id, name) => {
                setDrop(id);
                if (name) setDropName(name);
              }}
            />
          </>
        ) : (
          <LocationPicker
            label="Location"
            value={location}
            initialLabel={locationName}
            onChange={(id, name) => {
              setLocation(id);
              if (name) setLocationName(name);
            }}
          />
        )}

        <Stack gap={4}>
          <Text fz="sm" fw={500}>
            Status
          </Text>
          <SegmentedControl
            value={status}
            onChange={(value) => setStatus(value as InquiryStatus)}
            data={[
              { label: 'Active', value: 'ACTIVE' },
              { label: 'Closed', value: 'CLOSED' },
            ]}
          />
        </Stack>

        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={save.isPending} disabled={!valid}>
            {editing ? 'Save changes' : 'Save inquiry'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
