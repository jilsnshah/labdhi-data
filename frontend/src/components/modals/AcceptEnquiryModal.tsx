/**
 * Turning a party's own words into an inquiry.
 *
 * What arrived through a portal link is loose by design: a grade they may have
 * typed, a place as a place name, a rate they hope for. An inquiry is not
 * loose - every field points at master data. This modal is where the desk
 * closes that gap, with what the party sent shown above the form so the two
 * can be read against each other.
 *
 * Their quantity, unit and rate are carried in as the starting values. Changing
 * one here changes the inquiry, never the enquiry: their words stay as written.
 */

import { Alert, Button, Group, Modal, NumberInput, Select, Stack, Text } from '@mantine/core';
import { IconInfoCircle } from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { portalEnquiryApi, useApiMutation } from '@/api/hooks';
import type { DeskEnquiry, QuantityUnit } from '@/api/types';
import { EntitySelect } from '@/components/EntitySelect';
import { LocationPicker } from '@/components/LocationPicker';
import { formatDateTime, formatQuantity } from '@/lib/format';

const UNITS: QuantityUnit[] = ['MT', 'KG', 'BAG', 'LITRE', 'PIECE'];

/** Empty stays empty: a rate nobody quoted must not become a zero. */
const money = (value: number | string) =>
  value === '' || value === null ? null : String(value);

export function AcceptEnquiryModal({
  enquiry,
  onClose,
}: {
  enquiry: DeskEnquiry | null;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const isTransport = enquiry?.inquiry_type === 'TRANSPORT';

  const [product, setProduct] = useState<number | null>(null);
  const [location, setLocation] = useState<number | null>(null);
  const [locationName, setLocationName] = useState<string | null>(null);
  const [pickup, setPickup] = useState<number | null>(null);
  const [pickupName, setPickupName] = useState<string | null>(null);
  const [drop, setDrop] = useState<number | null>(null);
  const [dropName, setDropName] = useState<string | null>(null);
  const [quantity, setQuantity] = useState<number | string>('');
  const [unit, setUnit] = useState<QuantityUnit>('MT');
  const [rate, setRate] = useState<number | string>('');

  // Start each one from what the party actually sent.
  useEffect(() => {
    if (!enquiry) return;
    setProduct(enquiry.product?.id ?? null);
    setLocation(null);
    setLocationName(null);
    setPickup(null);
    setPickupName(null);
    setDrop(null);
    setDropName(null);
    setQuantity(enquiry.quantity);
    setUnit(enquiry.unit);
    setRate(enquiry.rate ?? '');
  }, [enquiry]);

  const accept = useApiMutation(
    (body: unknown) => portalEnquiryApi.accept(enquiry?.id ?? 0, body),
    {
      successMessage: 'Inquiry created from the enquiry.',
      invalidate: ['portal-enquiries', 'portal-enquiry-counts', 'inquiries', 'dashboard'],
    },
  );

  if (!enquiry) return null;

  const sameRoute = pickup !== null && drop !== null && pickup === drop;
  const valid = isTransport
    ? pickup !== null && drop !== null && !sameRoute
    : product !== null;

  const submit = async () => {
    const accepted = await accept.mutateAsync({
      product_id: isTransport ? null : product,
      location_id: isTransport ? null : location,
      pickup_location_id: isTransport ? pickup : null,
      delivery_location_id: isTransport ? drop : null,
      quantity: String(quantity),
      unit,
      rate: money(rate),
    });
    onClose();
    if (accepted.inquiry_id) navigate(`/inquiries/${accepted.inquiry_id}`);
  };

  const theirRate = enquiry.rate
    ? `${isTransport ? '₹' : '₹/kg'} ${enquiry.rate}`
    : 'no rate given';
  const theirPlaces = [enquiry.from_place, enquiry.to_place].filter(Boolean).join(' → ');

  return (
    <Modal opened onClose={onClose} title={`Accept enquiry from ${enquiry.party.name}`} size="lg">
      <Stack gap="md">
        <Alert
          variant="light"
          color="brass"
          icon={<IconInfoCircle size={16} />}
          title="What they sent"
        >
          <Text size="sm">
            {enquiry.product?.display_name ?? enquiry.product_text ?? 'No grade named'} ·{' '}
            {formatQuantity(enquiry.quantity, enquiry.unit)}
            {theirPlaces ? ` · ${theirPlaces}` : ''} · {theirRate}
          </Text>
          {enquiry.notes && (
            <Text size="sm" mt={6} fs="italic">
              “{enquiry.notes}”
            </Text>
          )}
          <Text size="xs" c="dimmed" mt={6}>
            Sent {formatDateTime(enquiry.created_at)}
          </Text>
        </Alert>

        {!isTransport && (
          <>
            <EntitySelect
              kind="product"
              label="Product"
              placeholder={
                enquiry.product
                  ? 'They picked this from the list'
                  : 'They typed a name - pick the grade it means'
              }
              value={product}
              onChange={(value) => setProduct(value)}
            />
            <LocationPicker
              label={enquiry.inquiry_type === 'SUPPLIER' ? 'Ships from' : 'Deliver to'}
              value={location}
              initialLabel={locationName}
              onChange={(id, name) => {
                setLocation(id);
                setLocationName(name);
              }}
            />
          </>
        )}

        {isTransport && (
          <>
            <LocationPicker
              label="Pick up from"
              value={pickup}
              initialLabel={pickupName}
              required
              onChange={(id, name) => {
                setPickup(id);
                setPickupName(name);
              }}
            />
            <LocationPicker
              label="Deliver to"
              value={drop}
              initialLabel={dropName}
              required
              error={sameRoute ? 'Pick up and delivery must be different' : undefined}
              onChange={(id, name) => {
                setDrop(id);
                setDropName(name);
              }}
            />
          </>
        )}

        <Group grow align="flex-start">
          <NumberInput
            label="Quantity"
            value={quantity}
            onChange={setQuantity}
            min={0}
            decimalScale={3}
          />
          <Select
            label="Unit"
            data={UNITS}
            value={unit}
            onChange={(value) => setUnit((value as QuantityUnit) ?? 'MT')}
            allowDeselect={false}
          />
          <NumberInput
            label={isTransport ? 'Freight (₹)' : 'Rate (₹/kg)'}
            description="The rate we stand behind"
            value={rate}
            onChange={setRate}
            min={0}
            decimalScale={2}
          />
        </Group>

        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={!valid} loading={accept.isPending} onClick={submit}>
            Create inquiry
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
