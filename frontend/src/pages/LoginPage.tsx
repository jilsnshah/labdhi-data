import {
  Alert,
  Box,
  Button,
  Card,
  Center,
  Group,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core';
import { IconBuildingWarehouse, IconInfoCircle } from '@tabler/icons-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { useAuth } from '@/lib/auth';

export function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@tradercrm.in');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await signIn(email, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Center h="100vh" p="lg" bg="var(--surface)">
      <Stack gap="lg" w={400} maw="100%">
        <Group gap="sm" justify="center">
          <ThemeIcon size={40} radius="md" color="ink">
            <IconBuildingWarehouse size={22} />
          </ThemeIcon>
          <Box>
            <Title order={3} fz={20} lh={1.2}>
              Trader CRM
            </Title>
            <Text fz="xs" c="dimmed">
              Inquiries, relationships and field work
            </Text>
          </Box>
        </Group>

        <Card padding="xl" shadow="md">
          <form onSubmit={submit}>
            <Stack gap="md">
              <Box>
                <Title order={5} fz="md">
                  Sign in
                </Title>
                <Text fz="xs" c="dimmed">
                  Use your trade desk account.
                </Text>
              </Box>
              <TextInput
                label="Email"
                type="email"
                size="md"
                required
                value={email}
                onChange={(event) => setEmail(event.currentTarget.value)}
              />
              <PasswordInput
                label="Password"
                size="md"
                required
                value={password}
                onChange={(event) => setPassword(event.currentTarget.value)}
              />
              {error && (
                <Alert color="rust" icon={<IconInfoCircle size={16} />} p="xs">
                  <Text fz="xs">{error}</Text>
                </Alert>
              )}
              <Button type="submit" loading={loading} fullWidth size="md" mt={4}>
                Sign in
              </Button>
            </Stack>
          </form>
        </Card>

        <Text fz="xs" c="dimmed" ta="center">
          Demo: admin@tradercrm.in / admin123 · field app users sign in on the phone
        </Text>
      </Stack>
    </Center>
  );
}
