import { createTheme, type MantineColorsTuple } from '@mantine/core';

/**
 * House style: gold, black and white. A commodity trading desk, not a SaaS
 * admin panel.
 *
 * A near-black shell frames a warm ivory working surface, and gold is the only
 * accent - used sparingly, for the thing that matters on a screen. The two
 * sides of the market are told apart by weight rather than hue: supply sits in
 * the dark neutral, demand in gold.
 *
 * The one colour outside the palette is a muted red, kept strictly for what is
 * wrong or about to be destroyed. A warning that does not look like a warning
 * is a hazard, so that exception earns its place.
 *
 * Type: a serif for titles and headline figures, a crisp grotesk for the UI,
 * and a tabular mono for every rate so columns of prices line up like a board.
 */

/** Warm black: text, borders, the shell and the primary button. */
const ink: MantineColorsTuple = [
  '#f7f6f4',
  '#eceae6',
  '#dbd8d2',
  '#bdb9b1',
  '#97938b',
  '#726e67',
  '#555049',
  '#3a3630',
  '#231f1b',
  '#121010',
];

/** Links, focus, the demand side: gold, deepened so it reads on white. */
const accent: MantineColorsTuple = [
  '#fbf6ea',
  '#f4ead1',
  '#e8d3a1',
  '#dbbb6e',
  '#cfa747',
  '#c6992f',
  '#b4871f',
  '#96701a',
  '#785915',
  '#5c4310',
];

/** Brass: the house accent. Highlights, the active nav marker, key figures. */
const brass: MantineColorsTuple = [
  '#fbf7ee',
  '#f4ebd6',
  '#e8d4a8',
  '#dcbc77',
  '#d2a84f',
  '#cb9c37',
  '#c7952a',
  '#af821f',
  '#9b7318',
  '#86620c',
];

/** Supply side of the market: the dark neutral, opposite gold. */
const teal: MantineColorsTuple = [
  '#f2f1ef',
  '#e3e1dc',
  '#c8c4bc',
  '#aaa49a',
  '#8d8679',
  '#726b5f',
  '#5a5349',
  '#433d35',
  '#2c2823',
  '#1a1714',
];

/** Attention: waiting, follow-up required, overdue. */
const amber: MantineColorsTuple = [
  '#fdf6ec',
  '#f8ebd8',
  '#f0d6ac',
  '#e7bf7c',
  '#dfac55',
  '#d79f3c',
  '#c98c28',
  '#a8731f',
  '#8a5e19',
  '#6d4a13',
];

/** Negative: below cost, lost, cancelled. */
const rust: MantineColorsTuple = [
  '#fdf1f0',
  '#f8e0de',
  '#f0bfbb',
  '#e69b95',
  '#dd7d75',
  '#d76961',
  '#c85a52',
  '#a84941',
  '#8b3c35',
  '#6e2f29',
];

/** Positive: margin, completed, active. Gold, not green. */
const moss: MantineColorsTuple = [
  '#fbf6e9',
  '#f3e9cf',
  '#e6d29d',
  '#d7b969',
  '#caa441',
  '#c29629',
  '#a98319',
  '#8b6c15',
  '#6e5511',
  '#53400c',
];

export const FONT_SANS =
  '"Instrument Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
export const FONT_SERIF = '"Instrument Serif", "Times New Roman", Georgia, serif';
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

  fontSizes: {
    xs: '0.8125rem',
    sm: '0.875rem',
    md: '0.9375rem',
    lg: '1.0625rem',
    xl: '1.25rem',
  },
  lineHeights: { xs: '1.45', sm: '1.5', md: '1.55', lg: '1.5', xl: '1.4' },
  headings: {
    fontFamily: FONT_SERIF,
    fontWeight: '400',
    sizes: {
      h1: { fontSize: '2.5rem', lineHeight: '1.1' },
      h2: { fontSize: '2.125rem', lineHeight: '1.15' },
      h3: { fontSize: '1.5rem', lineHeight: '1.25' },
      h4: { fontSize: '1.25rem', lineHeight: '1.3' },
      h5: { fontSize: '1.0625rem', lineHeight: '1.35' },
      h6: { fontSize: '0.9375rem', lineHeight: '1.4' },
    },
  },

  radius: { xs: '4px', sm: '7px', md: '10px', lg: '14px', xl: '20px' },
  spacing: { xs: '0.5rem', sm: '0.75rem', md: '1rem', lg: '1.5rem', xl: '2rem' },

  /* Layered, low-contrast shadows: depth you feel rather than see. */
  shadows: {
    xs: '0 1px 2px rgba(12, 21, 40, 0.04)',
    sm: '0 1px 2px rgba(12, 21, 40, 0.04), 0 4px 16px -8px rgba(12, 21, 40, 0.10)',
    md: '0 2px 4px rgba(12, 21, 40, 0.04), 0 12px 32px -12px rgba(12, 21, 40, 0.18)',
    lg: '0 4px 8px rgba(12, 21, 40, 0.05), 0 24px 56px -16px rgba(12, 21, 40, 0.24)',
    xl: '0 8px 16px rgba(12, 21, 40, 0.06), 0 40px 80px -24px rgba(12, 21, 40, 0.30)',
  },

  components: {
    Card: {
      defaultProps: { withBorder: true, radius: 'lg', shadow: 'sm', padding: 'lg' },
      styles: { root: { borderColor: 'var(--hairline)', background: 'var(--surface)' } },
    },
    Paper: { defaultProps: { radius: 'lg' } },
    Button: {
      defaultProps: { size: 'sm', fw: 600, radius: 'md' },
      styles: { root: { letterSpacing: '0.005em' } },
    },
    ActionIcon: { defaultProps: { variant: 'subtle', color: 'ink', radius: 'md' } },
    Badge: {
      defaultProps: { radius: 'xl', fw: 600, variant: 'light' },
      styles: { label: { letterSpacing: '0.02em', textTransform: 'none' } },
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
        radius: 'lg',
        centered: true,
        padding: 'xl',
        shadow: 'xl',
        overlayProps: { backgroundOpacity: 0.45, blur: 3, color: '#0c1528' },
      },
      styles: {
        title: { fontFamily: FONT_SERIF, fontWeight: 400, fontSize: '1.5rem', lineHeight: 1.2 },
        header: { paddingBottom: '0.75rem' },
      },
    },
    Drawer: {
      defaultProps: { padding: 'xl', shadow: 'xl' },
      styles: { title: { fontFamily: FONT_SERIF, fontWeight: 400, fontSize: '1.5rem' } },
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
    Avatar: { defaultProps: { color: 'ink', radius: 'xl' } },
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
