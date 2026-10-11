import {
  ActionIcon,
  AppShell,
  Avatar,
  Box,
  Burger,
  Group,
  Kbd,
  Menu,
  ScrollArea,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
  UnstyledButton,
} from '@mantine/core';
import { useDisclosure, useHotkeys } from '@mantine/hooks';
import {
  IconBox,
  IconBuildingFactory2,
  IconBuildingWarehouse,
  IconCalendarMonth,
  IconCalendarTime,
  IconChartBar,
  IconChevronDown,
  IconClipboardList,
  IconFlask,
  IconHistory,
  IconLayoutGrid,
  IconLogout,
  IconMapPin,
  IconNote,
  IconSearch,
  IconSettings,
  IconSparkles,
  IconTruck,
  IconUserCheck,
  IconUsers,
} from '@tabler/icons-react';
import { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '@/lib/auth';
import { GlobalSearch } from './GlobalSearch';

interface NavItem {
  label: string;
  to: string;
  icon: React.ReactNode;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

/**
 * Flat, labelled sections instead of nested accordions: every destination is
 * one click away and the grouping explains the app at a glance.
 */
const NAV: NavSection[] = [
  {
    label: 'Overview',
    items: [{ label: 'Dashboard', to: '/', icon: <IconChartBar size={16} /> }],
  },
  {
    label: 'Relationships',
    items: [
      { label: 'Customers', to: '/parties/customers', icon: <IconUsers size={16} /> },
      { label: 'Suppliers', to: '/parties/suppliers', icon: <IconBuildingWarehouse size={16} /> },
      { label: 'Transporters', to: '/parties/transporters', icon: <IconTruck size={16} /> },
      { label: 'Notes', to: '/notes', icon: <IconNote size={16} /> },
    ],
  },
  {
    label: 'Inquiries',
    items: [
      { label: 'Customer inquiries', to: '/inquiries/customer', icon: <IconClipboardList size={16} /> },
      { label: 'Supplier inquiries', to: '/inquiries/supplier', icon: <IconBuildingWarehouse size={16} /> },
      { label: 'Transport', to: '/inquiries/transport', icon: <IconTruck size={16} /> },
    ],
  },
  {
    label: 'Field work',
    items: [
      { label: 'Today', to: '/activities/today', icon: <IconCalendarTime size={16} /> },
      { label: 'Upcoming', to: '/activities/upcoming', icon: <IconCalendarMonth size={16} /> },
      { label: 'History', to: '/activities/history', icon: <IconHistory size={16} /> },
      { label: 'Calendar', to: '/activities/calendar', icon: <IconCalendarMonth size={16} /> },
      { label: 'Salespeople', to: '/activities/salespeople', icon: <IconUserCheck size={16} /> },
    ],
  },
  {
    label: 'Master data',
    items: [
      { label: 'Products', to: '/masters/products', icon: <IconBox size={16} /> },
      { label: 'Materials', to: '/masters/materials', icon: <IconFlask size={16} /> },
      { label: 'Grades', to: '/masters/grades', icon: <IconLayoutGrid size={16} /> },
      { label: 'Manufacturers', to: '/masters/manufacturers', icon: <IconBuildingFactory2 size={16} /> },
      { label: 'Applications', to: '/masters/applications', icon: <IconSparkles size={16} /> },
      { label: 'Locations', to: '/masters/locations', icon: <IconMapPin size={16} /> },
    ],
  },
];

function initials(name?: string): string {
  if (!name) return '?';
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

export function AppLayout() {
  const [mobileOpened, { toggle: toggleMobile, close: closeMobile }] = useDisclosure();
  const [searchOpened, setSearchOpened] = useState(false);
  const location = useLocation();
  const { user, signOut } = useAuth();

  useHotkeys([['mod+K', () => setSearchOpened(true)]]);

  return (
    <AppShell
      header={{ height: 58 }}
      navbar={{ width: 244, breakpoint: 'sm', collapsed: { mobile: !mobileOpened } }}
      padding="lg"
    >
      <AppShell.Header
        style={{ borderBottom: '1px solid var(--hairline)', background: 'var(--surface)' }}
      >
        <Group h="100%" px="lg" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <Burger opened={mobileOpened} onClick={toggleMobile} hiddenFrom="sm" size="sm" />
            <Link to="/" style={{ textDecoration: 'none' }} onClick={closeMobile}>
              <Group gap={10} wrap="nowrap">
                <ThemeIcon variant="filled" radius="sm" size={28} color="ink.9">
                  <IconBuildingWarehouse size={16} />
                </ThemeIcon>
                <Text fw={600} fz="md" c="ink.9" visibleFrom="xs" style={{ letterSpacing: '-0.01em' }}>
                  Trader CRM
                </Text>
              </Group>
            </Link>
          </Group>

          <Group gap="sm" wrap="nowrap">
            <UnstyledButton
              onClick={() => setSearchOpened(true)}
              px="sm"
              py={7}
              style={{
                border: '1px solid var(--hairline)',
                borderRadius: 6,
                background: 'var(--surface)',
                minWidth: 230,
              }}
              visibleFrom="sm"
            >
              <Group gap="xs" wrap="nowrap" justify="space-between">
                <Group gap={6} wrap="nowrap">
                  <IconSearch size={14} color="var(--mantine-color-ink-5)" />
                  <Text fz="sm" c="ink.5">
                    Search
                  </Text>
                </Group>
                <Kbd size="xs">⌘K</Kbd>
              </Group>
            </UnstyledButton>
            <Tooltip label="Search">
              <ActionIcon
                size="lg"
                variant="default"
                hiddenFrom="sm"
                onClick={() => setSearchOpened(true)}
              >
                <IconSearch size={17} />
              </ActionIcon>
            </Tooltip>

            <Menu position="bottom-end" withinPortal shadow="md" width={210}>
              <Menu.Target>
                <UnstyledButton>
                  <Group gap={8} wrap="nowrap">
                    <Avatar color="ink.2" radius="xl" size={28}>
                      <Text fz={11} fw={600} c="ink.8">
                        {initials(user?.name)}
                      </Text>
                    </Avatar>
                    <Box visibleFrom="sm">
                      <Text fz="sm" fw={550} lh={1.25} c="ink.9">
                        {user?.name}
                      </Text>
                      <Text fz="xs" c="ink.5" tt="capitalize">
                        {user?.role.toLowerCase()}
                      </Text>
                    </Box>
                    <IconChevronDown size={14} color="var(--mantine-color-ink-4)" />
                  </Group>
                </UnstyledButton>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>{user?.email}</Menu.Label>
                <Menu.Item leftSection={<IconSettings size={15} />} component={Link} to="/settings">
                  Settings
                </Menu.Item>
                <Menu.Divider />
                <Menu.Item color="rust" leftSection={<IconLogout size={15} />} onClick={signOut}>
                  Sign out
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar
        p="md"
        style={{ borderRight: '1px solid var(--hairline)', background: 'var(--surface)' }}
      >
        <AppShell.Section grow component={ScrollArea} type="scroll">
          <Stack gap={2} pb="md">
            {NAV.map((section) => (
              <Box key={section.label}>
                <Text className="nav-section-label">{section.label}</Text>
                <Stack gap={1}>
                  {section.items.map((item) => (
                    <Link
                      key={item.to}
                      to={item.to}
                      className="nav-link"
                      data-active={location.pathname === item.to || undefined}
                      onClick={closeMobile}
                    >
                      <span className="nav-icon">{item.icon}</span>
                      {item.label}
                    </Link>
                  ))}
                </Stack>
              </Box>
            ))}
          </Stack>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main className="app-main">
        <Box className="page">
          <Outlet />
        </Box>
      </AppShell.Main>

      <GlobalSearch opened={searchOpened} onClose={() => setSearchOpened(false)} />
    </AppShell>
  );
}
