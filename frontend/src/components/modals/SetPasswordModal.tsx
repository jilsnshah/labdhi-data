/**
 * Giving a user a password the admin can read out.
 *
 * Existing passwords cannot be shown: they are stored as one-way hashes, so
 * nobody - not the database, not this screen - can recover what someone typed.
 * What the desk actually needs is to put a known password on an account and
 * pass it on, which is what this does. It is shown once, here, and then it is
 * a hash like any other.
 */

import { Alert, Button, CopyButton, Group, Modal, Stack, Text, TextInput } from '@mantine/core';
import { IconCheck, IconCopy, IconInfoCircle, IconRefresh } from '@tabler/icons-react';
import { useState } from 'react';

import { api } from '@/api/client';
import { useApiMutation } from '@/api/hooks';
import type { User } from '@/api/types';

/** Readable at a glance and over the phone: no l/1/O/0 to mishear. */
function generatePassword(): string {
  const letters = 'abcdefghjkmnpqrstuvwxyz';
  const capitals = 'ABCDEFGHJKMNPQRSTUVWXYZ';
  const digits = '23456789';
  const pool = letters + capitals + digits;
  const bytes = crypto.getRandomValues(new Uint32Array(10));
  const body = Array.from(bytes, (value) => pool[value % pool.length]).join('');
  // Guarantee one of each kind, wherever the draw landed.
  return `${capitals[bytes[0] % capitals.length]}${body}${digits[bytes[1] % digits.length]}`;
}

export function SetPasswordModal({ user, onClose }: { user: User; onClose: () => void }) {
  const [password, setPassword] = useState(generatePassword);
  const [saved, setSaved] = useState<string | null>(null);

  const save = useApiMutation(
    (value: string) => api.patch(`/users/${user.id}`, { password: value }),
    {
      successMessage: 'Password set',
    },
  );

  return (
    <Modal opened onClose={onClose} title={`Password for ${user.name}`} centered>
      <Stack gap="md">
        {saved ? (
          <>
            <Alert color="moss" icon={<IconCheck size={16} />}>
              Set. Give this to {user.name} - it cannot be shown again.
            </Alert>
            <Group gap="xs" wrap="nowrap">
              <TextInput flex={1} readOnly value={saved} styles={{ input: { fontWeight: 600 } }} />
              <CopyButton value={saved}>
                {({ copied, copy }) => (
                  <Button
                    variant={copied ? 'light' : 'default'}
                    leftSection={copied ? <IconCheck size={15} /> : <IconCopy size={15} />}
                    onClick={copy}
                  >
                    {copied ? 'Copied' : 'Copy'}
                  </Button>
                )}
              </CopyButton>
            </Group>
            <Text fz="xs" c="ink.5">
              They sign in with {user.email} and can change it themselves afterwards.
            </Text>
            <Group justify="flex-end">
              <Button onClick={onClose}>Done</Button>
            </Group>
          </>
        ) : (
          <>
            <Alert color="amber" icon={<IconInfoCircle size={16} />} p="xs">
              <Text fz="xs">
                An existing password cannot be looked up - it is stored as a one-way hash, so nobody
                can read it back. Set a new one instead and pass it on.
              </Text>
            </Alert>
            <TextInput
              label="New password"
              description="At least 6 characters"
              value={password}
              onChange={(event) => setPassword(event.currentTarget.value)}
              rightSection={
                <Button
                  variant="subtle"
                  size="compact-xs"
                  px={6}
                  onClick={() => setPassword(generatePassword())}
                  aria-label="Generate another"
                >
                  <IconRefresh size={14} />
                </Button>
              }
              rightSectionWidth={40}
            />
            <Group justify="flex-end" gap="sm">
              <Button variant="default" onClick={onClose}>
                Cancel
              </Button>
              <Button
                loading={save.isPending}
                disabled={password.trim().length < 6}
                onClick={() =>
                  save.mutate(password.trim(), { onSuccess: () => setSaved(password.trim()) })
                }
              >
                Set password
              </Button>
            </Group>
          </>
        )}
      </Stack>
    </Modal>
  );
}
