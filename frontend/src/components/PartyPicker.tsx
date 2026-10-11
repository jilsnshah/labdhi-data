/**
 * Pick a customer, supplier or transporter - or add one nobody has on file yet.
 *
 * A new party needs only a name and a phone number. It is saved to Master Data
 * as a prospect straight away and selected, so the form carries on as if it had
 * always existed, and the next inquiry can find it too.
 */

import { Anchor, Button, Group, Paper, Stack, Text } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { partyApi, useApiMutation } from '@/api/hooks';
import type { PartyQuickCreate, PartyType } from '@/api/types';
import { EntitySelect } from '@/components/EntitySelect';
import { NewPartyFields } from '@/components/modals/NewPartyFields';
import { humanize } from '@/lib/format';

export function PartyPicker({
  partyType,
  value,
  label,
  onChange,
  disabled,
}: {
  partyType: PartyType;
  value: number | null;
  /** Shown while the picked party is not in the current search results. */
  label?: string | null;
  onChange: (id: number | null, name: string | null) => void;
  disabled?: boolean;
}) {
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState<PartyQuickCreate>({});
  const noun = humanize(partyType);

  const create = useApiMutation(
    (body: { party_type: string; name: string; phone: string }) => partyApi.createProspect(body),
    { successMessage: `${noun} saved as a prospect` },
  );

  const name = (draft.name ?? '').trim();
  const phone = (draft.phone ?? '').trim();

  const save = async () => {
    const party = await create.mutateAsync({ party_type: partyType, name, phone });
    onChange(party.id, party.name);
    setDraft({});
    setAdding(false);
  };

  if (adding) {
    return (
      <Paper withBorder p="sm" radius="md">
        <Stack gap="sm">
          <Text fz="sm" fw={600}>
            New {noun.toLowerCase()}
          </Text>
          <NewPartyFields
            minimal
            partyType={partyType}
            value={draft}
            onChange={setDraft}
            onUseExisting={(id, existingName) => {
              onChange(id, existingName);
              setDraft({});
              setAdding(false);
            }}
          />
          <Group justify="flex-end" gap="xs">
            <Button variant="default" size="xs" onClick={() => setAdding(false)}>
              Cancel
            </Button>
            <Button size="xs" onClick={save} loading={create.isPending} disabled={!name || !phone}>
              Save {noun.toLowerCase()}
            </Button>
          </Group>
        </Stack>
      </Paper>
    );
  }

  return (
    <Stack gap={4}>
      <EntitySelect
        kind="party"
        label={noun}
        required
        filters={{ party_type: partyType }}
        value={value}
        initialLabel={label}
        disabled={disabled}
        onChange={(id) => onChange(id, null)}
      />
      {!disabled && (
        <Anchor component="button" type="button" fz="xs" onClick={() => setAdding(true)}>
          <Group gap={4} component="span">
            <IconPlus size={12} />
            Not in the list? Add a new {noun.toLowerCase()}
          </Group>
        </Anchor>
      )}
    </Stack>
  );
}
