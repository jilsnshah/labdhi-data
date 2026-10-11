import { createTheme, type MantineColorsTuple } from '@mantine/core';

/**
 * Institutional visual language.
 *
 * One neutral scale carries the whole interface. Colour is rationed: a single
 * deep blue for things you can click, and three desaturated semantics (amber,
 * rust, moss) that appear only as a status dot or a number that needs action.
 * Surfaces are white with hairline borders and no drop shadows, so density
 * comes from rhythm rather than from boxes inside boxes.
 */

/** Neutral: text, borders, surfaces, and the near-black primary button. */
const ink: MantineColorsTuple = [
  '#f6f7f8',
  '#eceef0',
  '#dfe2e6',
  '#ccd1d7',
  '#a8b0ba',
  '#7f8894',
  '#5c6672',
  '#3f4853',
  '#232a33',
  '#11161d',
];

/** The only interactive accent: links, active navigation, focus. */
const accent: MantineColorsTuple = [
  '#eef2fa',
  '#dde4f4',
  '#b9c8e8',
  '#92aadb',
  '#7191d0',
  '#5c81c9',
  '#4f77c6',
  '#4166ae',
  '#385a9c',
  '#2b4a88',
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

/** Negative: cancelled, declined, lost on price. */
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

/** Positive: converted, completed, active. */
const moss: MantineColorsTuple = [
  '#eef5f2',
  '#dcebe5',
  '#b6d6ca',
  '#8dbfac',
  '#6cab94',
  '#569e84',
  '#48977b',
  '#378368',
  '#2d745c',
  '#20644d',
];

export const theme = createTheme({
  primaryColor: 'ink',
  primaryShade: { light: 9, dark: 8 },
  colors: { ink, accent, amber, rust, moss, slate: ink, brand: accent },
  white: '#ffffff',
  black: '#11161d',
  defaultRadius: 'sm',

  fontFamily:
    'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  fontFamilyMonospace:
    'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace',

  fontSizes: {
    xs: '0.8125rem',
    sm: '0.875rem',
    md: '0.9375rem',
    lg: '1.0625rem',
    xl: '1.1875rem',
  },
  lineHeights: { xs: '1.45', sm: '1.5', md: '1.55', lg: '1.5', xl: '1.4' },
  headings: {
    fontWeight: '600',
    sizes: {
      h1: { fontSize: '1.625rem', lineHeight: '1.25' },
      h2: { fontSize: '1.375rem', lineHeight: '1.3' },
      h3: { fontSize: '1.125rem', lineHeight: '1.35' },
      h4: { fontSize: '1rem', lineHeight: '1.4' },
      h5: { fontSize: '0.9375rem', lineHeight: '1.4' },
      h6: { fontSize: '0.875rem', lineHeight: '1.4' },
    },
  },

  radius: { xs: '4px', sm: '6px', md: '8px', lg: '12px', xl: '16px' },
  spacing: { xs: '0.5rem', sm: '0.75rem', md: '1rem', lg: '1.5rem', xl: '2rem' },

  /* Flat by design: elevation is reserved for things that float above the page. */
  shadows: {
    xs: 'none',
    sm: 'none',
    md: '0 8px 24px rgba(17, 22, 29, 0.08)',
    lg: '0 16px 48px rgba(17, 22, 29, 0.12)',
    xl: '0 24px 64px rgba(17, 22, 29, 0.16)',
  },

  components: {
    Card: {
      defaultProps: { withBorder: true, radius: 'md', shadow: 'xs', padding: 'lg' },
      styles: { root: { borderColor: 'var(--mantine-color-ink-2)' } },
    },
    Paper: { defaultProps: { radius: 'md' } },
    Button: {
      defaultProps: { size: 'sm', fw: 550, radius: 'sm' },
      styles: { root: { letterSpacing: '0.005em' } },
    },
    ActionIcon: { defaultProps: { variant: 'subtle', color: 'ink', radius: 'sm' } },
    Badge: {
      defaultProps: { radius: 'sm', fw: 600, variant: 'default' },
      styles: { label: { letterSpacing: '0.02em', textTransform: 'none' } },
    },
    TextInput: { defaultProps: { size: 'sm', radius: 'sm' } },
    PasswordInput: { defaultProps: { size: 'sm', radius: 'sm' } },
    NumberInput: { defaultProps: { size: 'sm', radius: 'sm' } },
    Textarea: { defaultProps: { size: 'sm', radius: 'sm' } },
    Select: { defaultProps: { size: 'sm', radius: 'sm' } },
    MultiSelect: { defaultProps: { size: 'sm', radius: 'sm' } },
    DateInput: { defaultProps: { size: 'sm', radius: 'sm' } },
    DatePickerInput: { defaultProps: { size: 'sm', radius: 'sm' } },
    DateTimePicker: { defaultProps: { size: 'sm', radius: 'sm' } },
    Switch: { defaultProps: { size: 'sm', color: 'ink' } },
    Checkbox: { defaultProps: { size: 'sm', color: 'ink', radius: 'xs' } },
    SegmentedControl: { defaultProps: { size: 'sm', radius: 'sm', color: 'ink' } },
    Modal: {
      defaultProps: { radius: 'md', centered: true, padding: 'xl', shadow: 'lg' },
      styles: {
        title: { fontWeight: 600, fontSize: '1rem' },
        header: { paddingBottom: '0.75rem' },
      },
    },
    Drawer: {
      defaultProps: { padding: 'xl', shadow: 'lg' },
      styles: { title: { fontWeight: 600, fontSize: '1rem' } },
    },
    Tooltip: {
      defaultProps: { radius: 'sm', fz: 'xs', withArrow: false, color: 'ink.9' },
    },
    Table: { defaultProps: { striped: false, highlightOnHover: false } },
    Alert: {
      defaultProps: { radius: 'md', variant: 'light' },
      styles: { message: { fontSize: '0.875rem' } },
    },
    Tabs: { defaultProps: { keepMounted: false, color: 'ink' } },
    Loader: { defaultProps: { size: 'sm', color: 'ink.6' } },
    Anchor: { defaultProps: { fw: 500, underline: 'never', c: 'accent.9' } },
    Divider: { styles: { root: { borderColor: 'var(--mantine-color-ink-2)' } } },
    Menu: { defaultProps: { radius: 'md', shadow: 'md' } },
    Pagination: { defaultProps: { color: 'ink', radius: 'sm', size: 'sm' } },
    Timeline: { defaultProps: { color: 'ink' } },
    Avatar: { defaultProps: { color: 'ink', radius: 'xl' } },
    ThemeIcon: { defaultProps: { variant: 'light', color: 'ink', radius: 'sm' } },
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
  SUPPLIES: 'neutral',
  PURCHASES: 'neutral',
  INTERESTED_IN: 'neutral',
  ADMIN: 'neutral',
  USER: 'neutral',
  SALESPERSON: 'neutral',
};

export const TONE_DOT: Record<StatusTone, string> = {
  neutral: 'var(--mantine-color-ink-4)',
  active: 'var(--mantine-color-accent-7)',
  attention: 'var(--mantine-color-amber-7)',
  positive: 'var(--mantine-color-moss-7)',
  negative: 'var(--mantine-color-rust-7)',
};

export const TONE_TEXT: Record<StatusTone, string> = {
  neutral: 'ink.6',
  active: 'ink.8',
  attention: 'amber.9',
  positive: 'moss.9',
  negative: 'rust.9',
};
