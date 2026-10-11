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
  IconBox,
  IconBuildingFactory2,
  IconFlask,
  IconLayoutGrid,
  IconSearch,
  IconUsers,
} from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useSearch } from '@/api/hooks';
import type { SearchHit } from '@/api/types';
import { EmptyState } from '@/components/ui';

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

export function GlobalSearch({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const [term, setTerm] = useState('');
  const [debounced] = useDebouncedValue(term, 250);
  const navigate = useNavigate();
  const { data, isFetching } = useSearch(debounced, opened);

  useEffect(() => {
    if (!opened) setTerm('');
  }, [opened]);

  const groups: { title: string; hits: SearchHit[] }[] = data
    ? [
        { title: 'Parties', hits: data.parties },
        { title: 'Products', hits: data.products },
        { title: 'Materials', hits: data.materials },
        { title: 'Grades', hits: data.grades },
        { title: 'Manufacturers', hits: data.manufacturers },
      ].filter((group) => group.hits.length > 0)
    : [];

  const go = (hit: SearchHit) => {
    const route = ROUTES[hit.entity]?.(hit);
    if (route) navigate(route);
    onClose();
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
      <Box p="md" style={{ borderBottom: '1px solid var(--hairline)' }}>
        <TextInput
          data-autofocus
          size="md"
          variant="unstyled"
          placeholder="Search customers, suppliers, products, grades…"
          leftSection={<IconSearch size={17} />}
          rightSection={isFetching ? <Loader size={14} /> : <Kbd size="xs">esc</Kbd>}
          rightSectionWidth={54}
          value={term}
          onChange={(event) => setTerm(event.currentTarget.value)}
        />
      </Box>

      <ScrollArea.Autosize mah={440} p="md">
        {!debounced && (
          <EmptyState
            icon={<IconSearch size={18} />}
            title="Search the whole desk"
            hint="Try K-67 for a grade, Reliance for a manufacturer, or ABC for a party."
            compact
          />
        )}
        {debounced && !groups.length && !isFetching && (
          <EmptyState title={`Nothing found for “${debounced}”`} compact />
        )}

        <Stack gap="lg">
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
              {group.hits.map((hit) => (
                <UnstyledButton
                  key={`${hit.entity}-${hit.id}`}
                  onClick={() => go(hit)}
                  p="xs"
                  className="search-hit"
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
              ))}
            </Stack>
          ))}
        </Stack>
      </ScrollArea.Autosize>
    </Modal>
  );
}
