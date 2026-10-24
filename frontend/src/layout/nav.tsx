/**
 * Where the application can be navigated to, in one place.
 *
 * The sidebar draws this, the breadcrumb reads it, and the command palette
 * searches it. Keeping one list means a route added here appears in all three
 * without anybody remembering to add it twice - and that the palette can never
 * offer a destination the nav does not have.
 */

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
  IconInbox,
  IconLayoutGrid,
  IconMapPin,
  IconNote,
  IconSparkles,
  IconTruck,
  IconUserCheck,
  IconUsers,
} from '@tabler/icons-react';

export interface NavItem {
  label: string;
  to: string;
  icon: React.ReactNode;
}

export 
interface NavSection {
  label: string;
  items: NavItem[];
}

export const NAV: NavSection[] = [
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
      {
        label: 'From parties',
        to: '/inquiries/from-parties',
        icon: <IconInbox size={16} />,
      },
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

/**
 * Where "back" goes from a record.
 *
 * A record is always opened from a list, and the browser's own back button is
 * off in the chrome where nobody looks mid-task. Each detail route therefore
 * names the list it belongs to, so the trail can carry a way out that works
 * even on a link somebody was sent.
 */
export function parentOf(pathname: string): { to: string; label: string } | null {
  if (/^\/parties\/\d+/.test(pathname)) return { to: '/parties/customers', label: 'Relationships' };
  if (/^\/inquiries\/\d+/.test(pathname)) return { to: '/inquiries/customer', label: 'Inquiries' };
  if (/^\/bids\/\d+/.test(pathname)) return { to: '/bids/customer', label: 'Bids' };
  return null;
}

/** Which section and page a path belongs to - for the trail and the nav. */
export function trailFor(pathname: string): { section: string; page?: string } {
  for (const section of NAV) {
    for (const item of section.items) {
      if (item.to === '/' ? pathname === '/' : pathname.startsWith(item.to)) {
        return { section: section.label, page: item.label };
      }
    }
  }
  if (pathname.startsWith('/bids/')) return { section: 'Bids', page: 'Bid' };
  if (pathname.startsWith('/inquiries/')) return { section: 'Inquiries', page: 'Inquiry' };
  if (pathname.startsWith('/parties/')) return { section: 'Relationships', page: 'Party' };
  if (pathname.startsWith('/settings')) return { section: 'Settings' };
  return { section: 'Overview' };
}
