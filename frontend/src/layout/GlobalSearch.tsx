import {
  Badge,
  Box,
  Group,
  Kbd,
  Loader,
  Modal,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  UnstyledButton,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import {
  IconArrowRight,
  IconBox,
  IconBuildingFactory2,
  IconCornerDownLeft,
  IconFlask,
  IconLayoutGrid,
  IconSearch,
  IconSettings,
  IconUsers,
} from '@tabler/icons-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useSearch } from '@/api/hooks';
import type { SearchHit } from '@/api/types';
import { EmptyState } from '@/components/ui';

import { NAV } from './nav';

const ROUTES: Record<string, (hit: SearchHit) => string> = {
  party: (hit) => `/parties/${hit.id}`,
  product: (hit) => `/masters/products?focus=${hit.id}`,
  material: (hit) => `/masters/materials?focus=${hit.id}`,
  grade: (hit) => `/masters/grades?focus=${hit.id}`,
  manufacturer: (hit) => `/masters/manufacturers?focus=${hit.id}`,
};

const GROUP_ICONS: Record<string, React.ReactNode> = {
  Parties: <IconUsers size={14} />,
  Products: <IconBox size={14} />,
  Materials: <IconFlask size={14} />,
  Grades: <IconLayoutGrid size={14} />,
  Manufacturers: <IconBuildingFactory2 size={14} />,
};

/**
 * Every page the application has, flattened out of the nav.
 *
 * Read from the same list the sidebar draws, so a route can never be in one
 * and missing from the other. Settings is added because it lives in the
 * account menu rather than in the nav, and is still somewhere people go.
 */
const DESTINATIONS: { label: string; section: string; to: string; icon: React.ReactNode }[] = [
  ...NAV.flatMap((section) =>
    section.items.map((item) => ({
      label: item.label,
      section: section.label,
      to: item.to,
      icon: item.icon,
    })),
  ),
  { label: 'Settings', section: 'Account', to: '/settings', icon: <IconSettings size={14} /> },
];

/** Loose match: every word typed has to appear somewhere in the entry. */
function matches(term: string, ...fields: string[]): boolean {
  const haystack = fields.join(' ').toLowerCase();
  return term
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => haystack.includes(word));
}

export function GlobalSearch({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const [term, setTerm] = useState('');
  const [debounced] = useDebouncedValue(term, 250);
  const navigate = useNavigate();
  const { data, isFetching } = useSearch(debounced, opened);

  useEffect(() => {
    if (!opened) setTerm('');
  }, [opened]);

  // Pages first and without waiting for the server: a palette that cannot
  // answer "take me to transport bids" instantly is not worth opening.
  const pages = useMemo(
    () =>
      term.trim()
        ? DESTINATIONS.filter((page) => matches(term, page.label, page.section))
        : DESTINATIONS,
    [term],
  );

  const groups: { title: string; hits: SearchHit[] }[] = data
    ? [
        { title: 'Parties', hits: data.parties },
        { title: 'Products', hits: data.products },
        { title: 'Materials', hits: data.materials },
        { title: 'Grades', hits: data.grades },
        { title: 'Manufacturers', hits: data.manufacturers },
      ].filter((group) => group.hits.length > 0)
    : [];

  const go = (to: string) => {
    navigate(to);
    onClose();
  };

  const goToHit = (hit: SearchHit) => {
    const route = ROUTES[hit.entity]?.(hit);
    if (route) go(route);
  };

  /* ------------------------------------------------------------------ keys */
  /* One flat list of everything selectable, in the order it is drawn, so the
     arrow keys walk the screen rather than some internal structure. */
  const walk: (() => void)[] = [
    ...pages.map((page) => () => go(page.to)),
    ...groups.flatMap((group) => group.hits.map((hit) => () => goToHit(hit))),
  ];
  const [cursor, setCursor] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCursor(0);
  }, [term, data]);

  useEffect(() => {
    if (!opened) return;
    const row = listRef.current?.querySelector('[data-cursor="true"]');
    row?.scrollIntoView({ block: 'nearest' });
  }, [cursor, opened]);

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (!walk.length) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setCursor((at) => (at + 1) % walk.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setCursor((at) => (at - 1 + walk.length) % walk.length);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      walk[cursor]?.();
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="lg"
      padding={0}
      withCloseButton={false}
      radius="lg"
    >
      <Box p="md" style={{ borderBottom: '1px solid var(--hairline)' }} onKeyDown={onKeyDown}>
        <TextInput
          data-autofocus
          size="md"
          variant="unstyled"
          placeholder="Go to a page, or search parties, products, grades…"
          leftSection={<IconSearch size={17} />}
          rightSection={isFetching ? <Loader size={14} /> : <Kbd size="xs">esc</Kbd>}
          rightSectionWidth={54}
          value={term}
          onChange={(event) => setTerm(event.currentTarget.value)}
        />
      </Box>

      <ScrollArea.Autosize mah={440} p="md" viewportRef={listRef}>
        {debounced && !groups.length && !pages.length && !isFetching && (
          <EmptyState title={`Nothing found for “${debounced}”`} compact />
        )}

        <Stack gap="lg">
          {pages.length > 0 && (
            <Stack gap={4}>
              <Group gap={6} px={6}>
                <ThemeIcon size={18} radius="sm" variant="light" color="ink">
                  <IconArrowRight size={14} />
                </ThemeIcon>
                <Text fz={11} tt="uppercase" fw={700} c="dimmed" style={{ letterSpacing: '0.07em' }}>
                  Go to
                </Text>
              </Group>
              {pages.map((page, index) => (
                <UnstyledButton
                  key={page.to}
                  onClick={() => go(page.to)}
                  onMouseEnter={() => setCursor(index)}
                  p="xs"
                  className="search-hit"
                  data-cursor={cursor === index || undefined}
                >
                  <Group justify="space-between" wrap="nowrap">
                    <Group gap={10} wrap="nowrap">
                      <span className="search-hit-icon">{page.icon}</span>
                      <Text fz="sm" fw={550}>
                        {page.label}
                      </Text>
                    </Group>
                    <Text fz="xs" c="dimmed">
                      {page.section}
                    </Text>
                  </Group>
                </UnstyledButton>
              ))}
            </Stack>
          )}
          {groups.map((group) => (
            <Stack key={group.title} gap={4}>
              <Group gap={6} px={6}>
                <ThemeIcon size={18} radius="sm" variant="light" color="ink">
                  {GROUP_ICONS[group.title]}
                </ThemeIcon>
                <Text fz={11} tt="uppercase" fw={700} c="dimmed" style={{ letterSpacing: '0.07em' }}>
                  {group.title}
                </Text>
              </Group>
              {group.hits.map((hit) => {
                const index =
                  pages.length +
                  groups
                    .slice(0, groups.indexOf(group))
                    .reduce((total, earlier) => total + earlier.hits.length, 0) +
                  group.hits.indexOf(hit);
                return (
                <UnstyledButton
                  key={`${hit.entity}-${hit.id}`}
                  onClick={() => goToHit(hit)}
                  onMouseEnter={() => setCursor(index)}
                  p="xs"
                  className="search-hit"
                  data-cursor={cursor === index || undefined}
                >
                  <Group justify="space-between" wrap="nowrap">
                    <Stack gap={0} style={{ minWidth: 0 }}>
                      <Text fz="sm" fw={550} truncate>
                        {hit.label}
                      </Text>
                      {hit.sublabel && (
                        <Text fz="xs" c="dimmed" truncate>
                          {hit.sublabel}
                        </Text>
                      )}
                    </Stack>
                    {hit.status === 'INACTIVE' && (
                      <Badge size="xs" variant="default">
                        Inactive
                      </Badge>
                    )}
                  </Group>
                </UnstyledButton>
                );
              })}
            </Stack>
          ))}
        </Stack>
      </ScrollArea.Autosize>

      <Group
        gap="md"
        px="md"
        py={8}
        style={{ borderTop: '1px solid var(--hairline)' }}
        justify="flex-start"
      >
        <Group gap={5}>
          <Kbd size="xs">↑</Kbd>
          <Kbd size="xs">↓</Kbd>
          <Text fz="xs" c="dimmed">
            move
          </Text>
        </Group>
        <Group gap={5}>
          <Kbd size="xs">
            <IconCornerDownLeft size={10} />
          </Kbd>
          <Text fz="xs" c="dimmed">
            open
          </Text>
        </Group>
      </Group>
    </Modal>
  );
}
