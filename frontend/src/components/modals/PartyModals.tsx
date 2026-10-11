/** Create/edit a party and manage its location and product links. */

import {
  Alert,
  Button,
  Divider,
  Group,
  Modal,
  SegmentedControl,
  Select,
  Stack,
  Switch,
  Text,
  Textarea,
  TextInput,
} from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useState } from 'react';

import { partyApi, useApiMutation, useApplications, useDuplicateCheck } from '@/api/hooks';
import type {
  LocationType,
  PartyDetail,
  PartyLocation,
  PartyProduct,
  PartyProductRelationship,
  PartyType,
} from '@/api/types';
import { EntityMultiSelect, EntitySelect } from '@/components/EntitySelect';
import { humanize } from '@/lib/format';

const LOCATION_TYPES: LocationType[] = [
  'HEAD_OFFICE',
  'FACTORY',
  'WAREHOUSE',
  'DELIVERY_LOCATION',
  'OTHER',
];

const RELATIONSHIPS: Record<PartyType, PartyProductRelationship[]> = {
  CUSTOMER: ['PURCHASES', 'INTERESTED_IN'],
  SUPPLIER: ['SUPPLIES'],
  TRANSPORTER: [],
};

export function PartyFormModal({
  onClose,
  partyType,
  record,
}: {
  onClose: () => void;
  partyType: PartyType;
  record?: PartyDetail | null;
}) {
  const [form, setForm] = useState({
    name: record?.name ?? '',
    contact_person: record?.contact_person ?? '',
    phone: record?.phone ?? '',
    email: record?.email ?? '',
    gst_number: record?.gst_number ?? '',
    notes: record?.notes ?? '',
  });
  const [active, setActive] = useState((record?.status ?? 'ACTIVE') === 'ACTIVE');
  const [city, setCity] = useState('');
  const [locationLabel, setLocationLabel] = useState('');
  const [locationType, setLocationType] = useState<LocationType>(
    partyType === 'CUSTOMER' ? 'FACTORY' : 'HEAD_OFFICE',
  );
  const [productIds, setProductIds] = useState<number[]>([]);

  const save = useApiMutation(
    (body: Record<string, unknown>) =>
      record ? partyApi.patch(record.id, body) : partyApi.create(body),
    { successMessage: `${humanize(partyType)} ${record ? 'updated' : 'created'}` },
  );

  const submit = async () => {
    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      contact_person: form.contact_person.trim() || null,
      phone: form.phone.trim() || null,
      email: form.email.trim() || null,
      gst_number: form.gst_number.trim() || null,
      notes: form.notes.trim() || null,
    };
    if (record) {
      await save.mutateAsync({ ...payload, status: active ? 'ACTIVE' : 'INACTIVE' });
    } else {
      await save.mutateAsync({
        ...payload,
        party_type: partyType,
        locations: city.trim()
          ? [
              {
                location: { label: locationLabel.trim() || null, city: city.trim() },
                location_type: locationType,
                is_primary: true,
              },
            ]
          : [],
        products: productIds.map((id) => ({ product_id: id })),
      });
    }
    onClose();
  };

  const set = (key: keyof typeof form, value: string) =>
    setForm((current) => ({ ...current, [key]: value }));

  return (
    <Modal
      opened
      onClose={onClose}
      size="lg"
      title={record ? `${record.name}` : `New ${partyType.toLowerCase()}`}
    >
      <Stack gap="md">
        <TextInput
          label="Name"
          required
          data-autofocus
          value={form.name}
          onChange={(event) => set('name', event.currentTarget.value)}
        />
        <Group grow>
          <TextInput
            label="Contact person"
            value={form.contact_person}
            onChange={(event) => set('contact_person', event.currentTarget.value)}
          />
          <TextInput
            label="Phone"
            value={form.phone}
            onChange={(event) => set('phone', event.currentTarget.value)}
          />
        </Group>
        <Group grow>
          <TextInput
            label="Email"
            type="email"
            value={form.email}
            onChange={(event) => set('email', event.currentTarget.value)}
          />
          <TextInput
            label="GST number"
            value={form.gst_number}
            onChange={(event) => set('gst_number', event.currentTarget.value.toUpperCase())}
          />
        </Group>

        {!record && (
          <>
            <Divider
              label="First location (optional)"
              labelPosition="left"
              styles={{ label: { fontSize: 11, fontWeight: 700, letterSpacing: '0.06em' } }}
              mt="xs"
            />
            <Group grow>
              <TextInput
                label="Label"
                placeholder="e.g. Rajkot Factory"
                value={locationLabel}
                onChange={(event) => setLocationLabel(event.currentTarget.value)}
              />
              <TextInput
                label="City"
                value={city}
                onChange={(event) => setCity(event.currentTarget.value)}
              />
              <Select
                label="Type"
                data={LOCATION_TYPES.map((value) => ({ value, label: humanize(value) }))}
                value={locationType}
                onChange={(value) => value && setLocationType(value as LocationType)}
                allowDeselect={false}
              />
            </Group>
            {RELATIONSHIPS[partyType].length > 0 && (
              <ProductPicker
                partyType={partyType}
                value={productIds}
                onChange={setProductIds}
              />
            )}
          </>
        )}

        <Textarea
          label="Notes"
          autosize
          minRows={2}
          value={form.notes}
          onChange={(event) => set('notes', event.currentTarget.value)}
        />
        {record && (
          <Switch
            label="Active"
            description="Inactive parties keep their history but cannot start new business records."
            checked={active}
            onChange={(event) => setActive(event.currentTarget.checked)}
          />
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={save.isPending} disabled={!form.name.trim()}>
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function ProductPicker({
  partyType,
  value,
  onChange,
}: {
  partyType: PartyType;
  value: number[];
  onChange: (value: number[]) => void;
}) {
  return (
    <EntityMultiSelect
      kind="product"
      label="Products"
      description={
        partyType === 'SUPPLIER'
          ? 'What this supplier can supply.'
          : 'What this customer buys or is interested in.'
      }
      value={value}
      onChange={onChange}
    />
  );
}

export function PartyLocationModal({
  party,
  record,
  onClose,
}: {
  party: PartyDetail;
  record?: PartyLocation | null;
  onClose: () => void;
}) {
  const [mode, setMode] = useState<'EXISTING' | 'NEW'>('EXISTING');
  const [locationId, setLocationId] = useState<number | null>(record?.location_id ?? null);
  const [locationType, setLocationType] = useState<LocationType>(
    record?.location_type ?? 'WAREHOUSE',
  );
  const [isPrimary, setIsPrimary] = useState(record?.is_primary ?? false);
  const [form, setForm] = useState({ label: '', city: '', state: '', pincode: '', line1: '' });

  const save = useApiMutation(
    (body: Record<string, unknown>) =>
      record
        ? partyApi.updateLocation(party.id, record.id, body)
        : partyApi.addLocation(party.id, body),
    { successMessage: record ? 'Location updated' : 'Location linked' },
  );

  const submit = async () => {
    if (record) {
      await save.mutateAsync({ location_type: locationType, is_primary: isPrimary });
    } else {
      await save.mutateAsync({
        location_type: locationType,
        is_primary: isPrimary,
        ...(mode === 'EXISTING'
          ? { location_id: locationId }
          : {
              location: {
                label: form.label.trim() || null,
                city: form.city.trim(),
                state: form.state.trim() || null,
                pincode: form.pincode.trim() || null,
                address_line_1: form.line1.trim() || null,
              },
            }),
      });
    }
    onClose();
  };

  const valid = record
    ? true
    : mode === 'EXISTING'
      ? locationId !== null
      : form.city.trim().length > 0;

  return (
    <Modal opened onClose={onClose} title={record ? 'Edit location link' : `Add location`}>
      <Stack gap="md">
        {!record && (
          <SegmentedControl
            fullWidth
            value={mode}
            onChange={(value) => setMode(value as 'EXISTING' | 'NEW')}
            data={[
              { value: 'EXISTING', label: 'Existing location' },
              { value: 'NEW', label: 'New address' },
            ]}
          />
        )}
        {!record && mode === 'EXISTING' && (
          <EntitySelect
            kind="location"
            label="Location"
            required
            value={locationId}
            onChange={setLocationId}
          />
        )}
        {!record && mode === 'NEW' && (
          <>
            <TextInput
              label="Label"
              value={form.label}
              onChange={(event) => setForm({ ...form, label: event.currentTarget.value })}
            />
            <TextInput
              label="Address"
              value={form.line1}
              onChange={(event) => setForm({ ...form, line1: event.currentTarget.value })}
            />
            <Group grow>
              <TextInput
                label="City"
                required
                value={form.city}
                onChange={(event) => setForm({ ...form, city: event.currentTarget.value })}
              />
              <TextInput
                label="State"
                value={form.state}
                onChange={(event) => setForm({ ...form, state: event.currentTarget.value })}
              />
              <TextInput
                label="Pincode"
                value={form.pincode}
                onChange={(event) => setForm({ ...form, pincode: event.currentTarget.value })}
              />
            </Group>
          </>
        )}
        <Select
          label="Location type"
          data={LOCATION_TYPES.map((value) => ({ value, label: humanize(value) }))}
          value={locationType}
          onChange={(value) => value && setLocationType(value as LocationType)}
          allowDeselect={false}
        />
        <Switch
          label="Primary location"
          checked={isPrimary}
          onChange={(event) => setIsPrimary(event.currentTarget.checked)}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={save.isPending} disabled={!valid}>
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function PartyProductModal({
  party,
  record,
  onClose,
}: {
  party: PartyDetail;
  record?: PartyProduct | null;
  onClose: () => void;
}) {
  const options = RELATIONSHIPS[party.party_type];
  const [productId, setProductId] = useState<number | null>(record?.product_id ?? null);
  const [relationship, setRelationship] = useState<PartyProductRelationship>(
    record?.relationship_type ?? options[0],
  );
  const [notes, setNotes] = useState(record?.notes ?? '');
  const [active, setActive] = useState(record?.active ?? true);

  const save = useApiMutation(
    (body: Record<string, unknown>) =>
      record
        ? partyApi.updateProduct(party.id, record.id, body)
        : partyApi.addProduct(party.id, body),
    { successMessage: record ? 'Product link updated' : 'Product linked' },
  );

  const submit = async () => {
    await save.mutateAsync(
      record
        ? { relationship_type: relationship, notes: notes.trim() || null, active }
        : {
            product_id: productId,
            relationship_type: relationship,
            notes: notes.trim() || null,
          },
    );
    onClose();
  };

  return (
    <Modal opened onClose={onClose} title={record ? 'Edit product link' : 'Link a product'}>
      <Stack gap="md">
        {!record && (
          <EntitySelect
            kind="product"
            label="Product"
            required
            value={productId}
            onChange={setProductId}
          />
        )}
        <Select
          label="Relationship"
          data={options.map((value) => ({ value, label: humanize(value) }))}
          value={relationship}
          onChange={(value) => value && setRelationship(value as PartyProductRelationship)}
          allowDeselect={false}
        />
        <Textarea
          label="Notes"
          autosize
          minRows={2}
          placeholder="e.g. Regular 100 MT/month"
          value={notes}
          onChange={(event) => setNotes(event.currentTarget.value)}
        />
        {record && (
          <Switch
            label="Active link"
            checked={active}
            onChange={(event) => setActive(event.currentTarget.checked)}
          />
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={save.isPending} disabled={!record && !productId}>
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function MergePartyModal({
  party,
  onClose,
}: {
  party: PartyDetail;
  onClose: () => void;
}) {
  const [loserId, setLoserId] = useState<number | null>(null);
  const [note, setNote] = useState('');
  const { data: suggestions } = useDuplicateCheck({
    party_type: party.party_type,
    name: party.name,
    phone: party.phone ?? undefined,
    exclude_id: party.id,
  });

  const merge = useApiMutation(
    (value: number) => partyApi.merge(party.id, value, note.trim() || null),
    { successMessage: 'Duplicate merged' },
  );

  return (
    <Modal opened onClose={onClose} title={`Merge a duplicate into ${party.name}`} size="lg">
      <Stack gap="md">
        <Alert color="amber" icon={<IconAlertTriangle size={16} />} p="xs">
          <Text fz="xs">
            Every inquiry, activity and note moves to <b>{party.name}</b>. The duplicate is kept
            as a merged record so old links still work, but it can no longer be used for new
            business. This cannot be undone from the UI.
          </Text>
        </Alert>

        {suggestions && suggestions.candidates.length > 0 && (
          <div>
            <Text fz="xs" fw={700} tt="uppercase" c="dimmed" mb={4}>
              Likely duplicates
            </Text>
            <Stack gap={4}>
              {suggestions.candidates.map((candidate) => (
                <Button
                  key={candidate.id}
                  variant={loserId === candidate.id ? 'light' : 'default'}
                  size="xs"
                  justify="space-between"
                  onClick={() => setLoserId(candidate.id)}
                  rightSection={
                    <Text fz="xs" c="dimmed">
                      {candidate.stage === 'PROSPECT' ? 'prospect' : 'known'} ·{' '}
                      {candidate.phone ?? candidate.city ?? `#${candidate.id}`}
                    </Text>
                  }
                >
                  {candidate.name}
                </Button>
              ))}
            </Stack>
          </div>
        )}

        <EntitySelect
          kind="party"
          label="Duplicate to merge away"
          required
          includeInactive
          filters={{ party_type: party.party_type }}
          value={loserId}
          onChange={setLoserId}
          description="Pick the record that should disappear."
        />
        <Textarea
          label="Note (optional)"
          autosize
          minRows={2}
          placeholder="Same shop, entered twice during a phone enquiry."
          value={note}
          onChange={(event) => setNote(event.currentTarget.value)}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button
            color="amber"
            loading={merge.isPending}
            disabled={!loserId || loserId === party.id}
            onClick={async () => {
              await merge.mutateAsync(loserId!);
              onClose();
            }}
          >
            Merge
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

export function PartyApplicationModal({
  party,
  onClose,
}: {
  party: PartyDetail;
  onClose: () => void;
}) {
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [notes, setNotes] = useState('');
  const { data: applications } = useApplications({ page_size: 100 });

  const save = useApiMutation(
    (body: Record<string, unknown>) => partyApi.addApplication(party.id, body),
    { successMessage: 'End-use linked' },
  );

  // Already-linked end-uses would only fail the uniqueness check on submit.
  const linked = new Set(party.applications.map((link) => link.application_id));
  const options = (applications?.items ?? [])
    .filter((application) => !linked.has(application.id))
    .map((application) => ({ value: String(application.id), label: application.name }));

  const submit = async () => {
    await save.mutateAsync({
      application_id: Number(applicationId),
      notes: notes.trim() || null,
    });
    onClose();
  };

  return (
    <Modal opened onClose={onClose} title="Add an end-use">
      <Stack gap="md">
        <Text fz="sm" c="ink.6">
          What line of business is {party.name} in? This is separate from what they have traded
          with you — it is how they turn up in a search when they have no history yet.
        </Text>
        <Select
          label="End-use"
          placeholder={options.length ? 'Pick an application' : 'All end-uses already linked'}
          data={options}
          value={applicationId}
          onChange={setApplicationId}
          searchable
          disabled={options.length === 0}
          required
        />
        <Textarea
          label="Notes"
          autosize
          minRows={2}
          placeholder="e.g. Two extrusion lines, mostly agri pipe"
          value={notes}
          onChange={(event) => setNotes(event.currentTarget.value)}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={save.isPending} disabled={!applicationId}>
            Link end-use
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
