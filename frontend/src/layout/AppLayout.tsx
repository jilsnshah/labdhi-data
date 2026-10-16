import {
  ActionIcon,
  AppShell,
  Avatar,
  Box,
  Burger,
  Button,
  Group,
  Kbd,
  Menu,
  ScrollArea,
  Stack,
  Text,
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
  IconClipboardList,
  IconFlask,
  IconGavel,
  IconHistory,
  IconLayoutGrid,
  IconLogout,
  IconMapPin,
  IconNote,
  IconPlus,
  IconSearch,
  IconSelector,
  IconSettings,
  IconSparkles,
  IconTruck,
  IconUserCheck,
  IconUsers,
} from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { FelesCredit } from '@/components/FelesCredit';
import { InquiryFormModal } from '@/components/modals/InquiryFormModal';
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
      {
        label: 'Customer inquiries',
        to: '/inquiries/customer',
        icon: <IconClipboardList size={16} />,
      },
      {
        label: 'Supplier inquiries',
        to: '/inquiries/supplier',
        icon: <IconBuildingWarehouse size={16} />,
      },
      { label: 'Transport', to: '/inquiries/transport', icon: <IconTruck size={16} /> },
    ],
  },
  {
    label: 'Bids',
    items: [
      { label: 'Customer bids', to: '/bids/customer', icon: <IconGavel size={16} /> },
      { label: 'Supplier bids', to: '/bids/supplier', icon: <IconBuildingWarehouse size={16} /> },
      { label: 'Transport bids', to: '/bids/transport', icon: <IconTruck size={16} /> },
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
      {
        label: 'Manufacturers',
        to: '/masters/manufacturers',
        icon: <IconBuildingFactory2 size={16} />,
      },
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

/** Section title for the top bar, from the current route. */
function sectionFor(pathname: string): string {
  for (const section of NAV) {
    for (const item of section.items) {
      if (item.to !== '/' && pathname.startsWith(item.to)) return section.label;
    }
  }
  if (pathname.startsWith('/bids')) return 'Bids';
  if (pathname.startsWith('/inquiries/')) return 'Inquiries';
  if (pathname.startsWith('/parties/')) return 'Relationships';
  if (pathname.startsWith('/settings')) return 'Settings';
  return 'Overview';
}

/** IST clock - the desk runs on Indian market hours. */
function DeskClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(id);
  }, []);
  const time = now.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Kolkata',
  });
  const date = now.toLocaleDateString('en-IN', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    timeZone: 'Asia/Kolkata',
  });
  return (
    <Group gap={8} wrap="nowrap" visibleFrom="md">
      <Box
        w={7}
        h={7}
        style={{
          borderRadius: 99,
          background: 'var(--mantine-color-moss-6)',
          boxShadow: '0 0 0 3px rgba(63,161,116,0.18)',
        }}
      />
      <Text className="ticker-time">
        {date.toUpperCase()} · {time} IST
      </Text>
    </Group>
  );
}

export function AppLayout() {
  const [mobileOpened, { toggle: toggleMobile, close: closeMobile }] = useDisclosure();
  const [searchOpened, setSearchOpened] = useState(false);
  const [inquiryOpen, setInquiryOpen] = useState(false);
  const location = useLocation();
  const { user, signOut } = useAuth();

  useHotkeys([['mod+K', () => setSearchOpened(true)]]);

  const isActive = (to: string) =>
    to === '/' ? location.pathname === '/' : location.pathname === to;

  return (
    <AppShell
      layout="alt"
      header={{ height: 64 }}
      navbar={{ width: 256, breakpoint: 'md', collapsed: { mobile: !mobileOpened } }}
      padding={{ base: 'sm', sm: 'lg', lg: 'xl' }}
    >
      <AppShell.Header className="shell-top">
        <Group
          h="100%"
          px={{ base: 'sm', sm: 'lg', lg: 'xl' }}
          justify="space-between"
          wrap="nowrap"
        >
          <Group gap="md" wrap="nowrap">
            <Burger opened={mobileOpened} onClick={toggleMobile} hiddenFrom="md" size="sm" />
            <Text fz="sm" fw={600} c="ink.8">
              {sectionFor(location.pathname)}
            </Text>
            <DeskClock />
          </Group>

          <Group gap="sm" wrap="nowrap">
            <UnstyledButton
              onClick={() => setSearchOpened(true)}
              className="search-pill"
              visibleFrom="sm"
            >
              <Group gap={8} wrap="nowrap">
                <IconSearch size={15} color="var(--mantine-color-ink-5)" />
                <Text fz="sm" c="ink.5">
                  Search parties, products…
                </Text>
              </Group>
              <Kbd size="xs">⌘K</Kbd>
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
            <Button
              leftSection={<IconPlus size={15} />}
              radius="xl"
              onClick={() => setInquiryOpen(true)}
              visibleFrom="md"
            >
              New inquiry
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md" className="shell-nav">
        <AppShell.Section>
          <Link to="/" className="shell-brand" onClick={closeMobile}>
            <span className="shell-mark">L</span>
            <Box>
              <div className="shell-wordmark">Labdhi</div>
              <div className="shell-sub">Polymer trading</div>
            </Box>
          </Link>
        </AppShell.Section>

        <AppShell.Section grow component={ScrollArea} type="scroll" scrollbarSize={6}>
          <Stack gap={2} pb="md" px={4}>
            {NAV.map((section) => (
              <Box key={section.label}>
                <Text className="nav-section-label">{section.label}</Text>
                <Stack gap={2}>
                  {section.items.map((item) => (
                    <Link
                      key={item.to}
                      to={item.to}
                      className="nav-link"
                      data-active={isActive(item.to) || undefined}
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

        <AppShell.Section pt="sm">
          <Menu position="top-start" withinPortal width={220}>
            <Menu.Target>
              <UnstyledButton className="shell-user" w="100%">
                <Avatar
                  radius="md"
                  size={34}
                  styles={{
                    root: { background: 'linear-gradient(145deg,#e2bd6b,#b8862a)' },
                    placeholder: { background: 'transparent', color: '#1a1206' },
                  }}
                >
                  <Text fz={12} fw={700}>
                    {initials(user?.name)}
                  </Text>
                </Avatar>
                <Box style={{ minWidth: 0, flex: 1 }}>
                  <Text fz="sm" fw={600} c="#fff" lh={1.25} truncate>
                    {user?.name}
                  </Text>
                  <Text fz="xs" c="var(--shell-muted)" tt="capitalize">
                    {user?.role.toLowerCase()}
                  </Text>
                </Box>
                <IconSelector size={15} color="var(--shell-muted)" />
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
          <div className="shell-credit">
            <FelesCredit tone="dark" />
          </div>
        </AppShell.Section>
      </AppShell.Navbar>

      <AppShell.Main className="app-main">
        <Box className="page" key={location.pathname}>
          <Outlet />
        </Box>
      </AppShell.Main>

      <GlobalSearch opened={searchOpened} onClose={() => setSearchOpened(false)} />
      {inquiryOpen && (
        <InquiryFormModal opened onClose={() => setInquiryOpen(false)} defaultType="CUSTOMER" />
      )}
    </AppShell>
  );
}
