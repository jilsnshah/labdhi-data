/**
 * Create/edit modal shared by the simple name+description masters
 * (materials, grades, manufacturers, applications).
 */

import { Button, Group, Modal, Stack, Switch, Textarea, TextInput } from '@mantine/core';
import { useState } from 'react';

import { api } from '@/api/client';
import { useApiMutation } from '@/api/hooks';
import { EntitySelect } from '@/components/EntitySelect';

export interface MasterRecord {
  id: number;
  name: string;
  description: string | null;
  status: 'ACTIVE' | 'INACTIVE';
  code?: string | null;
  material_id?: number;
  material?: { id: number; name: string };
}

export function MasterFormModal({
  opened,
  onClose,
  record,
  path,
  entityLabel,
  withCode = false,
  withMaterial = false,
  defaultMaterialId,
}: {
  opened: boolean;
  onClose: () => void;
  record: MasterRecord | null;
  path: string;
  entityLabel: string;
  withCode?: boolean;
  withMaterial?: boolean;
  defaultMaterialId?: number | null;
}) {
  const [name, setName] = useState(record?.name ?? '');
  const [code, setCode] = useState(record?.code ?? '');
  const [description, setDescription] = useState(record?.description ?? '');
  const [materialId, setMaterialId] = useState<number | null>(
    record?.material_id ?? defaultMaterialId ?? null,
  );
  const [active, setActive] = useState((record?.status ?? 'ACTIVE') === 'ACTIVE');

  const save = useApiMutation(
    (body: Record<string, unknown>) =>
      record ? api.patch(`${path}/${record.id}`, body) : api.post(path, body),
    { successMessage: `${entityLabel} ${record ? 'updated' : 'created'}` },
  );

  const submit = async () => {
    await save.mutateAsync({
      name: name.trim(),
      description: description.trim() || null,
      ...(withCode ? { code: code.trim() || null } : {}),
      ...(withMaterial ? { material_id: materialId } : {}),
      ...(record ? { status: active ? 'ACTIVE' : 'INACTIVE' } : {}),
    });
    onClose();
  };

  const valid = name.trim().length > 0 && (!withMaterial || materialId !== null);

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={record ? `${entityLabel} #${record.id}` : `New ${entityLabel.toLowerCase()}`}
    >
      <Stack gap="md">
        {withMaterial && (
          <EntitySelect
            kind="material"
            label="Material"
            required
            value={materialId}
            onChange={setMaterialId}
            initialLabel={record?.material?.name}
            disabled={Boolean(record)}
            description={record ? 'Material cannot be changed once products exist.' : undefined}
          />
        )}
        <TextInput
          label="Name"
          required
          data-autofocus
          value={name}
          onChange={(event) => setName(event.currentTarget.value)}
        />
        {withCode && (
          <TextInput
            label="Code"
            placeholder="Short code, e.g. RIL"
            value={code}
            onChange={(event) => setCode(event.currentTarget.value)}
          />
        )}
        <Textarea
          label="Description"
          autosize
          minRows={2}
          value={description}
          onChange={(event) => setDescription(event.currentTarget.value)}
        />
        {record && (
          <Switch
            label="Active"
            description="Inactive records stay in history but cannot be used for new business records."
            checked={active}
            onChange={(event) => setActive(event.currentTarget.checked)}
          />
        )}
        <Group justify="flex-end" mt="sm">
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
