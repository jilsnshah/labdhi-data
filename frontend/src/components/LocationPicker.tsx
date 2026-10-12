/**
 * Pick any Master Data location - or add a new one without leaving the form.
 *
 * Locations are independent of parties: the list is never filtered by the
 * customer, supplier or transporter on the same form. A location added here is
 * saved to Master Data and selected, so later inquiries can reuse it.
 */

import { Anchor, Button, Group, Paper, Stack, Text, TextInput } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';
import { useState } from 'react';

import { locationApi, useApiMutation } from '@/api/hooks';
import { AreaInput } from '@/components/AreaInput';
import { EntitySelect } from '@/components/EntitySelect';

const EMPTY = { label: '', area: '', city: '', state: '' };

export function LocationPicker({
  label,
  value,
  initialLabel,
  onChange,
  required,
  error,
}: {
  label: string;
  value: number | null;
  /** Shown while the picked location is not in the current search results. */
  initialLabel?: string | null;
  onChange: (id: number | null, name: string | null) => void;
  required?: boolean;
  error?: string | null;
}) {
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState(EMPTY);

  const create = useApiMutation((body: unknown) => locationApi.create(body), {
    successMessage: 'Location saved to Master Data',
  });

  const save = async () => {
    const location = await create.mutateAsync({
      label: draft.label.trim() || null,
      area: draft.area.trim() || null,
      city: draft.city.trim(),
      state: draft.state.trim() || null,
    });
    onChange(
      location.id,
      [location.label, location.area, location.city, location.state].filter(Boolean).join(' - '),
    );
    setDraft(EMPTY);
    setAdding(false);
  };

  if (adding) {
    return (
      <Paper withBorder p="sm" radius="md">
        <Stack gap="sm">
          <Text fz="sm" fw={600}>
            New location for “{label.toLowerCase()}”
          </Text>
          <TextInput
            label="Name"
            placeholder="e.g. Shapar factory gate"
            data-autofocus
            value={draft.label}
            onChange={(event) => setDraft({ ...draft, label: event.currentTarget.value })}
          />
          <Group grow>
            <AreaInput
              value={draft.area}
              onChange={(value) => setDraft({ ...draft, area: value })}
            />
            <TextInput
              label="City"
              required
              value={draft.city}
              onChange={(event) => setDraft({ ...draft, city: event.currentTarget.value })}
            />
            <TextInput
              label="State"
              value={draft.state}
              onChange={(event) => setDraft({ ...draft, state: event.currentTarget.value })}
            />
          </Group>
          <Group justify="flex-end" gap="xs">
            <Button variant="default" size="xs" onClick={() => setAdding(false)}>
              Cancel
            </Button>
            <Button
              size="xs"
              onClick={save}
              loading={create.isPending}
              disabled={!draft.city.trim()}
            >
              Save location
            </Button>
          </Group>
        </Stack>
      </Paper>
    );
  }

  return (
    <Stack gap={4}>
      <EntitySelect
        kind="location"
        label={label}
        required={required}
        error={error}
        value={value}
        initialLabel={initialLabel}
        onChange={(id) => onChange(id, null)}
      />
      <Anchor component="button" type="button" fz="xs" onClick={() => setAdding(true)}>
        <Group gap={4} component="span">
          <IconPlus size={12} />
          Add a new location
        </Group>
      </Anchor>
    </Stack>
  );
}
