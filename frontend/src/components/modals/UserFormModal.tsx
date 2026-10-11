import {
  Button,
  Group,
  Modal,
  PasswordInput,
  Select,
  Stack,
  Switch,
  TextInput,
} from '@mantine/core';
import { useState } from 'react';

import { api } from '@/api/client';
import { useApiMutation } from '@/api/hooks';
import type { User, UserRole } from '@/api/types';

const ROLE_LABELS: Record<UserRole, string> = {
  ADMIN: 'Admin - full CRM access',
  USER: 'Desk user - full CRM access',
  SALESPERSON: 'Salesperson - field app only',
};

export function UserFormModal({
  record,
  onClose,
  lockedRole,
  title,
}: {
  record: User | null;
  onClose: () => void;
  /** Pre-select and lock the role, e.g. when adding a salesperson. */
  lockedRole?: UserRole;
  title?: string;
}) {
  const [name, setName] = useState(record?.name ?? '');
  const [email, setEmail] = useState(record?.email ?? '');
  const [phone, setPhone] = useState(record?.phone ?? '');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>(record?.role ?? lockedRole ?? 'USER');
  const [active, setActive] = useState((record?.status ?? 'ACTIVE') === 'ACTIVE');

  const save = useApiMutation(
    (body: Record<string, unknown>) =>
      record ? api.patch(`/users/${record.id}`, body) : api.post('/users', body),
    { successMessage: `User ${record ? 'updated' : 'created'}` },
  );

  const submit = async () => {
    await save.mutateAsync(
      record
        ? {
            name,
            role,
            phone: phone.trim() || null,
            status: active ? 'ACTIVE' : 'INACTIVE',
            ...(password ? { password } : {}),
          }
        : { name, email, password, role, phone: phone.trim() || null },
    );
    onClose();
  };

  return (
    <Modal
      opened
      onClose={onClose}
      title={title ?? (record ? record.email : 'New user')}
    >
      <Stack gap="md">
        <TextInput
          label="Name"
          required
          data-autofocus
          value={name}
          onChange={(event) => setName(event.currentTarget.value)}
        />
        {!record && (
          <TextInput
            label="Email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.currentTarget.value)}
          />
        )}
        <TextInput
          label="Phone"
          placeholder="+91 98250 00000"
          value={phone}
          onChange={(event) => setPhone(event.currentTarget.value)}
        />
        <PasswordInput
          label={record ? 'New password (optional)' : 'Password'}
          required={!record}
          value={password}
          onChange={(event) => setPassword(event.currentTarget.value)}
        />
        <Select
          label="Role"
          disabled={Boolean(lockedRole) && !record}
          data={(['ADMIN', 'USER', 'SALESPERSON'] as UserRole[]).map((value) => ({
            value,
            label: ROLE_LABELS[value],
          }))}
          value={role}
          onChange={(value) => value && setRole(value as UserRole)}
          allowDeselect={false}
        />
        {record && (
          <Switch
            label="Active"
            description="Inactive accounts cannot sign in and cannot be assigned new work."
            checked={active}
            onChange={(event) => setActive(event.currentTarget.checked)}
          />
        )}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            loading={save.isPending}
            disabled={!name.trim() || (!record && (!email.trim() || password.length < 6))}
          >
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
