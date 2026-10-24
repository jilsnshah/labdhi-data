import { Alert, Box, Button, Group, PasswordInput, Stack, Text, TextInput } from '@mantine/core';
import { IconArrowRight, IconInfoCircle } from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { FelesCredit } from '@/components/FelesCredit';
import { BRAND } from '@/lib/brand';
import { useAuth } from '@/lib/auth';

/** Decorative board for the brand panel - illustrative rows, not live data. */
const BOARD = [
  { product: 'PVC K-67', buy: '90.80', sell: '93.00', spread: '+2.20' },
  { product: 'LLDPE Film', buy: '98.40', sell: '101.25', spread: '+2.85' },
  { product: 'HDPE MFI 0.3', buy: '103.50', sell: '106.00', spread: '+2.50' },
  { product: 'PP Raffia', buy: '95.10', sell: '96.40', spread: '+1.30' },
];

export function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  // Demo credentials are prefilled only on a local dev server.
  const [email, setEmail] = useState(import.meta.env.DEV ? 'admin@tradercrm.in' : '');
  const [password, setPassword] = useState(import.meta.env.DEV ? 'admin123' : '');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // The server sleeps when the desk has been quiet and takes about a minute to
  // wake; without a word the first sign-in of the day looks broken.
  const [waking, setWaking] = useState(false);

  useEffect(() => {
    if (!loading) {
      setWaking(false);
      return;
    }
    const timer = window.setTimeout(() => setWaking(true), 6000);
    return () => window.clearTimeout(timer);
  }, [loading]);

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
    <div className="login">
      <section className="login-brand">
        <div className="login-brand-top">
          <span className="shell-mark">{BRAND.mark}</span>
          <div>
            <div className="shell-wordmark">{BRAND.name}</div>
            {BRAND.tagline && <div className="shell-sub">{BRAND.tagline}</div>}
          </div>
        </div>

        <div>
          <h1 className="login-headline">Every offer, every bid, on one desk.</h1>
          <p className="login-lede">
            Supplier quotes, customer demand and transport rates in one place — with the spread
            between them always in view.
          </p>

          <div className="login-board" aria-hidden>
            <div className="login-board-row login-board-head">
              <span>Product</span>
              <span>Buy</span>
              <span>Sell</span>
              <span>Spread</span>
            </div>
            {BOARD.map((row) => (
              <div className="login-board-row" key={row.product}>
                <span>{row.product}</span>
                <span className="buy">₹{row.buy}</span>
                <span className="sell">₹{row.sell}</span>
                <span className="spread">{row.spread}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="login-foot">Rates in ₹/kg · illustrative</div>
      </section>

      <section className="login-form-side">
        <Box w={380} maw="100%">
          <div className="page-eyebrow">Trade desk</div>
          <h2 className="page-title" style={{ fontSize: '1.375rem' }}>
            Sign in
          </h2>
          <Text c="ink.5" fz="sm" mt={4} mb="lg">
            Use your desk account to open today's book.
          </Text>
          <form onSubmit={submit}>
            <Stack gap="md">
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
              <Button
                type="submit"
                loading={loading}
                fullWidth
                size="md"
                mt={6}
                rightSection={<IconArrowRight size={17} />}
              >
                {waking ? 'Waking the server…' : 'Sign in'}
              </Button>
              {waking && (
                <Text fz="xs" c="ink.5" ta="center">
                  The server wakes up after a quiet spell. This can take a minute.
                </Text>
              )}
            </Stack>
          </form>
          <Group justify="center" mt="xl" mb="xs">
            <FelesCredit size="md" />
          </Group>
          <Text fz="xs" c="ink.4" mt="sm">
            {import.meta.env.DEV && 'Demo: admin@tradercrm.in / admin123 · '}
            Field staff sign in on the phone app.
          </Text>
        </Box>
      </section>
    </div>
  );
}
