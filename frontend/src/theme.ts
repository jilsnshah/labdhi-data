import { createTheme, type MantineColorsTuple } from '@mantine/core';

/**
 * House style: a modern trading platform. Neutral, dense, and quiet.
 *
 * The screen is almost entirely greys - a cool near-white page, white
 * instruments, hairline borders - because on a desk that reads rates all day
 * the data has to be the only thing with colour in it. Gold is the house mark
 * and is spent carefully: the active row in the nav, a brand moment, nothing
 * that repeats. Primary actions are near-black, which is both the brand and
 * the one weight nothing else competes with.
 *
 * Colour means something or it is not used. Emerald is the supply side and
 * what is good, amber is waiting, rose is wrong. Each appears as a small dot
 * or a figure, never as a filled panel, so a column of statuses stays calm.
 *
 * An earlier version of this was ivory and brass with serif headings. It read
 * as a boutique rather than as software, which is the opposite of what a desk
 * wants: traders trust instruments, not stationery.
 *
 * Type: one grotesk for everything, and a tabular mono for every rate so
 * columns of prices line up like a board.
 */

/** The whole interface. Cool neutral grey, from page to near-black. */
const ink: MantineColorsTuple = [
  '#f8f9fb',
  '#f1f3f6',
  '#e4e7ec',
  '#cdd3dc',
  '#a4adbb',
  '#7a8595',
  '#596273',
  '#3d4553',
  '#242a35',
  '#11151d',
];

/** The house mark, and the demand side of the market. Spent, not spread. */
const accent: MantineColorsTuple = [
  '#fdf8ed',
  '#f9eed4',
  '#f1daa6',
  '#e7c473',
  '#dcaf4a',
  '#d2a033',
  '#bd8d26',
  '#9a711c',
  '#7a5917',
  '#5c4311',
];

/** Kept as the name the app already uses for the house mark. */
const brass: MantineColorsTuple = accent;

/** Supply side of the market, and anything working as it should. */
const moss: MantineColorsTuple = [
  '#ecfdf3',
  '#d2f6e0',
  '#a7ebc5',
  '#6edaa5',
  '#3fc389',
  '#1fa974',
  '#12885d',
  '#0d6c4b',
  '#0b563d',
  '#084733',
];

/** Waiting on somebody: follow-up required, overdue, not yet decided. */
const amber: MantineColorsTuple = [
  '#fffaeb',
  '#fef0c7',
  '#fedf89',
  '#fec84b',
  '#fdb022',
  '#f79009',
  '#dc6803',
  '#b54708',
  '#93370d',
  '#7a2e0e',
];

/** Wrong: below cost, lost, cancelled, failed. */
const rust: MantineColorsTuple = [
  '#fef3f2',
  '#fee4e2',
  '#fecdca',
  '#fda29b',
  '#f97066',
  '#f04438',
  '#d92d20',
  '#b42318',
  '#912018',
  '#7a271a',
];

/** The name the market visuals use for the supply side. */
const teal: MantineColorsTuple = moss;

export const FONT_SANS =
  '"Instrument Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
/** Titles and headline figures. The same family, held tighter and heavier. */
export const FONT_DISPLAY = FONT_SANS;
export const FONT_MONO =
  '"IBM Plex Mono", ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace';

export const theme = createTheme({
  primaryColor: 'ink',
  primaryShade: { light: 9, dark: 8 },
  colors: { ink, accent, brass, teal, amber, rust, moss, slate: ink, brand: accent },
  white: '#ffffff',
  black: '#121010',
  defaultRadius: 'md',

  fontFamily: FONT_SANS,
  fontFamilyMonospace: FONT_MONO,

  /* A step smaller across the board. A desk screen is read, not presented. */
  fontSizes: {
    xs: '0.75rem',
    sm: '0.8125rem',
    md: '0.875rem',
    lg: '1rem',
    xl: '1.125rem',
  },
  lineHeights: { xs: '1.4', sm: '1.45', md: '1.5', lg: '1.5', xl: '1.4' },
  headings: {
    fontFamily: FONT_DISPLAY,
    fontWeight: '600',
    sizes: {
      h1: { fontSize: '1.625rem', lineHeight: '1.25' },
      h2: { fontSize: '1.25rem', lineHeight: '1.3' },
      h3: { fontSize: '1.0625rem', lineHeight: '1.35' },
      h4: { fontSize: '0.9375rem', lineHeight: '1.4' },
      h5: { fontSize: '0.875rem', lineHeight: '1.4' },
      h6: { fontSize: '0.8125rem', lineHeight: '1.4' },
    },
  },

  radius: { xs: '4px', sm: '6px', md: '8px', lg: '10px', xl: '14px' },
  spacing: { xs: '0.5rem', sm: '0.75rem', md: '1rem', lg: '1.5rem', xl: '2rem' },

  /* Borders do the separating; shadows only lift what genuinely floats. */
  shadows: {
    xs: '0 1px 2px rgba(16, 24, 40, 0.04)',
    sm: '0 1px 3px rgba(16, 24, 40, 0.08), 0 1px 2px rgba(16, 24, 40, 0.04)',
    md: '0 4px 8px -2px rgba(16, 24, 40, 0.08), 0 2px 4px -2px rgba(16, 24, 40, 0.04)',
    lg: '0 12px 16px -4px rgba(16, 24, 40, 0.08), 0 4px 6px -2px rgba(16, 24, 40, 0.03)',
    xl: '0 20px 24px -4px rgba(16, 24, 40, 0.10), 0 8px 8px -4px rgba(16, 24, 40, 0.04)',
  },

  components: {
    Card: {
      defaultProps: { withBorder: true, radius: 'md', shadow: 'xs', padding: 'lg' },
      styles: { root: { borderColor: 'var(--hairline)', background: 'var(--surface)' } },
    },
    Paper: { defaultProps: { radius: 'md' } },
    Button: {
      defaultProps: { size: 'sm', fw: 500, radius: 'md' },
      styles: { root: { letterSpacing: '0' } },
    },
    ActionIcon: { defaultProps: { variant: 'subtle', color: 'ink', radius: 'md' } },
    Badge: {
      defaultProps: { radius: 'sm', fw: 500, variant: 'light' },
      styles: { label: { letterSpacing: '0', textTransform: 'none' } },
    },
    TextInput: { defaultProps: { size: 'sm', radius: 'md' } },
    PasswordInput: { defaultProps: { size: 'sm', radius: 'md' } },
    NumberInput: { defaultProps: { size: 'sm', radius: 'md' } },
    Textarea: { defaultProps: { size: 'sm', radius: 'md' } },
    Select: { defaultProps: { size: 'sm', radius: 'md' } },
    Autocomplete: { defaultProps: { size: 'sm', radius: 'md' } },
    MultiSelect: { defaultProps: { size: 'sm', radius: 'md' } },
    DateInput: { defaultProps: { size: 'sm', radius: 'md' } },
    DatePickerInput: { defaultProps: { size: 'sm', radius: 'md' } },
    DateTimePicker: { defaultProps: { size: 'sm', radius: 'md' } },
    Switch: { defaultProps: { size: 'sm', color: 'ink' } },
    Checkbox: { defaultProps: { size: 'sm', color: 'ink', radius: 'xs' } },
    SegmentedControl: { defaultProps: { size: 'sm', radius: 'md', color: 'ink' } },
    Modal: {
      defaultProps: {
        radius: 'md',
        centered: true,
        padding: 'xl',
        shadow: 'xl',
        overlayProps: { backgroundOpacity: 0.5, blur: 2, color: '#11151d' },
      },
      styles: {
        title: { fontWeight: 600, fontSize: '1.0625rem', lineHeight: 1.35 },
        header: { paddingBottom: '0.75rem' },
      },
    },
    Drawer: {
      defaultProps: { padding: 'xl', shadow: 'xl' },
      styles: { title: { fontWeight: 600, fontSize: '1.0625rem' } },
    },
    Tooltip: {
      defaultProps: { radius: 'md', fz: 'xs', withArrow: false, color: 'ink.9' },
    },
    Table: { defaultProps: { striped: false, highlightOnHover: false } },
    Alert: {
      defaultProps: { radius: 'md', variant: 'light' },
      styles: { message: { fontSize: '0.875rem' } },
    },
    Tabs: { defaultProps: { keepMounted: false, color: 'brass.6' } },
    Loader: { defaultProps: { size: 'sm', color: 'brass.6' } },
    Anchor: { defaultProps: { fw: 500, underline: 'never', c: 'accent.8' } },
    Divider: { styles: { root: { borderColor: 'var(--hairline)' } } },
    Menu: { defaultProps: { radius: 'md', shadow: 'lg' } },
    Pagination: { defaultProps: { color: 'ink', radius: 'md', size: 'sm' } },
    Timeline: { defaultProps: { color: 'brass.6' } },
    Avatar: { defaultProps: { color: 'ink', radius: 'sm' } },
    ThemeIcon: { defaultProps: { variant: 'light', color: 'ink', radius: 'md' } },
    Notification: { defaultProps: { radius: 'md' } },
  },
});

export type StatusTone = 'neutral' | 'active' | 'attention' | 'positive' | 'negative';

/**
 * Status → tone. Tones are rendered as a small dot plus neutral text, never as a
 * coloured pill, so a table of statuses reads as one calm column.
 */
export const STATUS_TONES: Record<string, StatusTone> = {
  // master data / parties
  ACTIVE: 'positive',
  INACTIVE: 'neutral',
  PROSPECT: 'attention',
  MERGED: 'neutral',

  // inquiries
  OPEN: 'active',
  IN_PROGRESS: 'active',
  WAITING: 'attention',
  QUOTED: 'active',
  CLOSED: 'neutral',
  CANCELLED: 'negative',

  // activities
  SCHEDULED: 'active',
  COMPLETED: 'positive',

  // outcomes and closure reasons
  CONVERTED_TO_DEAL: 'positive',
  CUSTOMER_INTERESTED: 'positive',
  CUSTOMER_NOT_INTERESTED: 'negative',
  FOLLOW_UP_REQUIRED: 'attention',
  NO_RESPONSE: 'neutral',
  RESCHEDULED: 'attention',
  PRICE_TOO_HIGH: 'negative',
  NO_STOCK: 'attention',
  SUPPLIER_UNAVAILABLE: 'attention',
  TRANSPORT_UNAVAILABLE: 'attention',
  CUSTOMER_CANCELLED: 'negative',
  DUPLICATE: 'neutral',
  OTHER: 'neutral',

  // responses
  QUOTE: 'active',
  COUNTER_OFFER: 'active',
  DECLINED: 'negative',
  INFO: 'neutral',

  // types and roles - descriptive, never alarming
  CUSTOMER: 'neutral',
  SUPPLIER: 'neutral',
  TRANSPORTER: 'neutral',
  TRANSPORT: 'neutral',
  SUPPLIES: 'neutral',
  PURCHASES: 'neutral',
  INTERESTED_IN: 'neutral',
  ADMIN: 'neutral',
  USER: 'neutral',
  SALESPERSON: 'neutral',
};

export const TONE_DOT: Record<StatusTone, string> = {
  neutral: 'var(--mantine-color-ink-4)',
  active: 'var(--mantine-color-accent-6)',
  attention: 'var(--mantine-color-amber-6)',
  positive: 'var(--mantine-color-moss-6)',
  negative: 'var(--mantine-color-rust-6)',
};

export const TONE_TEXT: Record<StatusTone, string> = {
  neutral: 'ink.6',
  active: 'ink.8',
  attention: 'amber.9',
  positive: 'moss.9',
  negative: 'rust.9',
};

/** The two sides of the market, used consistently by every chart and chip. */
export const MARKET = {
  supply: {
    color: 'var(--mantine-color-teal-7)',
    soft: 'var(--mantine-color-teal-0)',
    label: 'Supply',
  },
  demand: {
    color: 'var(--mantine-color-accent-6)',
    soft: 'var(--mantine-color-accent-0)',
    label: 'Demand',
  },
} as const;
