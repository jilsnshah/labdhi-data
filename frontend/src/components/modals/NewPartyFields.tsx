/**
 * Inline "I don't have this party yet" form.
 *
 * Three fields are enough to start working (name, phone, city); everything else
 * can be filled in later from the party page. As the trader types, we warn about
 * parties that already look like this one and offer to use them instead.
 */

import { Alert, Anchor, Group, Stack, Text, TextInput } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconAlertTriangle, IconUserPlus } from '@tabler/icons-react';

import { useDuplicateCheck } from '@/api/hooks';
import type { DuplicateCandidate, PartyQuickCreate, PartyType } from '@/api/types';
import { humanize } from '@/lib/format';

const REASON_LABEL: Record<DuplicateCandidate['match_reason'], string> = {
  exact_gst: 'same GST',
  exact_phone: 'same phone',
  similar_name: 'similar name',
};

export function NewPartyFields({
  partyType,
  value,
  onChange,
  onUseExisting,
  minimal = false,
}: {
  partyType: PartyType;
  value: PartyQuickCreate;
  onChange: (value: PartyQuickCreate) => void;
  /** Called when the trader picks a suggested existing party instead. */
  onUseExisting?: (id: number, name: string) => void;
  /** Name and phone only, without the explanatory banner - used by inquiry forms. */
  minimal?: boolean;
}) {
  const [debouncedName] = useDebouncedValue(value.name ?? '', 350);
  const [debouncedPhone] = useDebouncedValue(value.phone ?? '', 350);
  const { data } = useDuplicateCheck({
    party_type: partyType,
    name: debouncedName || undefined,
    phone: debouncedPhone || undefined,
    gst_number: value.gst_number || undefined,
  });

  const set = (patch: Partial<PartyQuickCreate>) => onChange({ ...value, ...patch });
  const label = humanize(partyType).toLowerCase();

  return (
    <Stack gap="sm">
      {!minimal && (
        <Alert color="ink" p="xs" icon={<IconUserPlus size={16} />}>
          <Text fz="xs">
            A new {label} will be created as a <b>prospect</b> and saved together with this record.
            Name or phone is enough - the rest can follow later.
          </Text>
        </Alert>
      )}

      <Group grow>
        <TextInput
          label={`${humanize(partyType)} name`}
          placeholder="Patel Traders"
          data-autofocus
          required={minimal}
          value={value.name ?? ''}
          onChange={(event) => set({ name: event.currentTarget.value })}
        />
        <TextInput
          label="Phone"
          placeholder="+91 98250 00000"
          required={minimal}
          value={value.phone ?? ''}
          onChange={(event) => set({ phone: event.currentTarget.value })}
        />
      </Group>
      {!minimal && (
        <Group grow>
          <TextInput
            label="Contact person"
            value={value.contact_person ?? ''}
            onChange={(event) => set({ contact_person: event.currentTarget.value })}
          />
          <TextInput
            label="City"
            description="Becomes the primary location"
            value={value.city ?? ''}
            onChange={(event) => set({ city: event.currentTarget.value })}
          />
          <TextInput
            label="GST number"
            value={value.gst_number ?? ''}
            onChange={(event) => set({ gst_number: event.currentTarget.value.toUpperCase() })}
          />
        </Group>
      )}

      {data && data.candidates.length > 0 && (
        <Alert
          color={data.has_exact_match ? 'orange' : 'yellow'}
          icon={<IconAlertTriangle size={16} />}
          p="xs"
        >
          <Text fz="xs" fw={600}>
            {data.has_exact_match ? 'This looks like an existing party' : 'Possible duplicates'}
          </Text>
          <Stack gap={2} mt={4}>
            {data.candidates.map((candidate) => (
              <Group key={candidate.id} gap={6} wrap="nowrap">
                {onUseExisting ? (
                  <Anchor
                    fz="xs"
                    fw={600}
                    onClick={() => onUseExisting(candidate.id, candidate.name)}
                  >
                    Use “{candidate.name}”
                  </Anchor>
                ) : (
                  <Text fz="xs" fw={600}>
                    {candidate.name}
                  </Text>
                )}
                <Text fz="xs" c="dimmed">
                  {[
                    REASON_LABEL[candidate.match_reason],
                    candidate.city,
                    candidate.phone,
                    candidate.stage === 'PROSPECT' ? 'prospect' : null,
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </Text>
              </Group>
            ))}
          </Stack>
        </Alert>
      )}
    </Stack>
  );
}

/** True when the inline form has enough to create a party. */
export function canCreateParty(value: PartyQuickCreate): boolean {
  return Boolean((value.name ?? '').trim() || (value.phone ?? '').trim());
}

/** Strip empty strings so the API sees nulls, not blanks. */
export function cleanQuickCreate(value: PartyQuickCreate, partyType: PartyType): PartyQuickCreate {
  const trim = (input?: string | null) => {
    const cleaned = (input ?? '').trim();
    return cleaned.length > 0 ? cleaned : null;
  };
  return {
    name: trim(value.name),
    phone: trim(value.phone),
    contact_person: trim(value.contact_person),
    gst_number: trim(value.gst_number),
    city: trim(value.city),
    notes: trim(value.notes),
    party_type: partyType,
  };
}
