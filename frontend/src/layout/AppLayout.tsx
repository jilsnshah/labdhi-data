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
  IconChevronRight,
  IconLogout,
  IconPlus,
  IconSearch,
  IconSelector,
  IconSettings,
} from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { FelesCredit } from '@/components/FelesCredit';
import { InquiryFormModal } from '@/components/modals/InquiryFormModal';
import { useAuth } from '@/lib/auth';
import { GlobalSearch } from './GlobalSearch';
import { NAV, trailFor } from './nav';

/**
 * Shell dimensions live here and in `--topbar-h` / `--sidebar-w`; AppShell
 * needs the numbers, the stylesheet needs them for sticky offsets.
 */
const HEADER_H = 48;
const SIDEBAR_W = 236;


/**
 * Groups that start closed.
 *
 * Twenty-three destinations is more than a laptop has room for: at 1280x720
 * the list ran 1031px into 547px of space, so ten of them lived below the
 * fold and the desk scrolled a menu to find a page. Master data is set up
 * once and rarely revisited, and the field-work screens are a day's work on
 * their own rather than something crossed into mid-task, so those two start
 * closed and everything else is in view.
 *
 * None of this hides a destination: the group is one click away, the palette
 * finds it by name, and whichever group the current page belongs to is open
 * whatever this says.
 */
const CLOSED_BY_DEFAULT = ['Field work', 'Master data'];

/** Remembered per browser, so the desk's own arrangement survives a reload. */
const NAV_STATE_KEY = 'labdhi.nav.closed';

function loadClosed(): string[] {
  try {
    const saved = window.localStorage.getItem(NAV_STATE_KEY);
    return saved ? (JSON.parse(saved) as string[]) : CLOSED_BY_DEFAULT;
  } catch {
    return CLOSED_BY_DEFAULT;
  }
}

/**
 * Flat, labelled sections instead of nested accordions: every destination is
 * one click away and the grouping explains the app at a glance.
 */

function initials(name?: string): string {
  if (!name) return '?';
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

/**
 * Where you are, as a trail: the section and the page inside it, read off the
 * same NAV that drew the sidebar. The page heading does not repeat the
 * section, so this is the one place it is named.

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
    <Text className="ticker-time" visibleFrom="lg" mr="xs">
      {date} · {time} IST
    </Text>
  );
}

export function AppLayout() {
  const [mobileOpened, { toggle: toggleMobile, close: closeMobile }] = useDisclosure();
  const [searchOpened, setSearchOpened] = useState(false);
  const [inquiryOpen, setInquiryOpen] = useState(false);
  const location = useLocation();
  const { user, signOut } = useAuth();
  const trail = trailFor(location.pathname);
  const [closed, setClosed] = useState<string[]>(loadClosed);

  useHotkeys([['mod+K', () => setSearchOpened(true)]]);

  const isActive = (to: string) =>
    to === '/' ? location.pathname === '/' : location.pathname === to;

  // The group holding the current page is always open, whatever was saved -
  // the one thing worse than a long menu is one that hides where you are.
  const isOpen = (label: string) => label === trail.section || !closed.includes(label);

  const toggleGroup = (label: string) => {
    if (label === trail.section) return;
    setClosed((current) => {
      const next = current.includes(label)
        ? current.filter((name) => name !== label)
        : [...current, label];
      try {
        window.localStorage.setItem(NAV_STATE_KEY, JSON.stringify(next));
      } catch {
        // A browser refusing storage costs the arrangement, not the nav.
      }
      return next;
    });
  };

  return (
    <AppShell
      layout="alt"
      header={{ height: HEADER_H }}
      navbar={{ width: SIDEBAR_W, breakpoint: 'md', collapsed: { mobile: !mobileOpened } }}
      padding={{ base: 'sm', sm: 'md', lg: 'lg' }}
    >
      <AppShell.Header className="shell-top">
        <Group
          h="100%"
          px={{ base: 'sm', sm: 'md', lg: 'lg' }}
          justify="space-between"
          wrap="nowrap"
        >
          <Group gap="sm" wrap="nowrap">
            <Burger opened={mobileOpened} onClick={toggleMobile} hiddenFrom="md" size="sm" />
            <span className="shell-crumb">
              {trail.section}
              {trail.page && (
                <>
                  <IconChevronRight size={13} />
                  <b>{trail.page}</b>
                </>
              )}
            </span>
            <UnstyledButton
              onClick={() => setSearchOpened(true)}
              className="search-field"
              visibleFrom="sm"
              aria-label="Search parties, products and inquiries"
            >
              <Group gap={6} wrap="nowrap">
                <IconSearch size={14} color="var(--mantine-color-ink-5)" />
                <Text fz="sm" c="ink.5">
                  Search parties, products…
                </Text>
              </Group>
              <Kbd size="xs">⌘K</Kbd>
            </UnstyledButton>
          </Group>

          <Group gap="xs" wrap="nowrap">
            <DeskClock />
            <Tooltip label="Search">
              <ActionIcon
                size="input-sm"
                variant="default"
                hiddenFrom="sm"
                onClick={() => setSearchOpened(true)}
              >
                <IconSearch size={16} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Record an inquiry from anywhere">
              <Button
                variant="default"
                leftSection={<IconPlus size={14} />}
                onClick={() => setInquiryOpen(true)}
                visibleFrom="md"
              >
                New inquiry
              </Button>
            </Tooltip>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar px="sm" pb="sm" className="shell-nav">
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
          <Stack gap={1} pb={2} px={2}>
            {NAV.map((section) => {
              const open = isOpen(section.label);
              const here = section.label === trail.section;
              // A group of one is just a link. Dashboard does not need a
              // heading announcing that it is the Overview section.
              if (section.items.length === 1) {
                const [item] = section.items;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className="nav-link nav-link-solo"
                    data-active={isActive(item.to) || undefined}
                    onClick={closeMobile}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    {item.label}
                  </Link>
                );
              }
              return (
                <Box key={section.label}>
                  <UnstyledButton
                    className="nav-section"
                    data-open={open || undefined}
                    data-here={here || undefined}
                    onClick={() => toggleGroup(section.label)}
                    aria-expanded={open}
                    aria-label={`${section.label}, ${open ? 'collapse' : 'expand'}`}
                  >
                    <span className="nav-section-label">{section.label}</span>
                    {/* The group you are in cannot be shut, so it is not
                        offered a control that would do nothing. */}
                    {!here && <IconChevronRight size={12} className="nav-section-chevron" />}
                    {!open && <span className="nav-section-count">{section.items.length}</span>}
                  </UnstyledButton>
                  {open && (
                    <Stack gap={1}>
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
                  )}
                </Box>
              );
            })}
          </Stack>
        </AppShell.Section>

        <AppShell.Section pt={6}>
          <Menu position="top-start" withinPortal width={220}>
            <Menu.Target>
              <UnstyledButton className="shell-user" w="100%">
                <Avatar
                  radius="sm"
                  size={28}
                  styles={{
                    root: { background: 'var(--brass)' },
                    placeholder: { background: 'transparent', color: '#1a1206' },
                  }}
                >
                  <Text fz={11} fw={700}>
                    {initials(user?.name)}
                  </Text>
                </Avatar>
                <Box style={{ minWidth: 0, flex: 1 }}>
                  <Text fz="sm" fw={600} c="#fff" lh={1.3} truncate>
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
