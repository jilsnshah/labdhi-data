import { Button, Group, Modal, Stack, Textarea } from '@mantine/core';
import { useState } from 'react';

import { noteApi, useApiMutation } from '@/api/hooks';
import type { Note } from '@/api/types';
import { EntitySelect } from '@/components/EntitySelect';

export function NoteFormModal({
  onClose,
  partyId,
  partyLabel,
  record,
}: {
  onClose: () => void;
  partyId?: number;
  partyLabel?: string;
  record?: Note | null;
}) {
  const [party, setParty] = useState<number | null>(partyId ?? record?.party_id ?? null);
  const [text, setText] = useState(record?.note ?? '');

  const save = useApiMutation(
    (body: Record<string, unknown>) =>
      record ? noteApi.patch(record.id, body) : noteApi.create(body),
    { successMessage: record ? 'Note updated' : 'Note added' },
  );

  const submit = async () => {
    await save.mutateAsync(
      record ? { note: text.trim() } : { party_id: party, note: text.trim() },
    );
    onClose();
  };

  return (
    <Modal opened onClose={onClose} title={record ? `Note #${record.id}` : 'New note'}>
      <Stack gap="md">
        {!record && (
          <EntitySelect
            kind="party"
            label="Party"
            required
            value={party}
            onChange={setParty}
            initialLabel={partyLabel}
            disabled={Boolean(partyId)}
            includeInactive
          />
        )}
        <Textarea
          label="Note"
          required
          data-autofocus
          autosize
          minRows={4}
          placeholder="Customer is expanding a second factory. Requirement should increase from November."
          value={text}
          onChange={(event) => setText(event.currentTarget.value)}
        />
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            loading={save.isPending}
            disabled={!text.trim() || (!record && !party)}
          >
            Save note
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
