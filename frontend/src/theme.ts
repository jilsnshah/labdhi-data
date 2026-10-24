import { createTheme, type MantineColorsTuple } from '@mantine/core';

/**
 * House style: a premium operations workspace for a physical trading desk.
 *
 * Three colours carry the identity. Charcoal is the structure - the sidebar,
 * body text, every border. Deep navy is the product's voice: the primary
 * action, a selected row, the figure that matters. Gold is the house mark, used where
 * the brand should be felt rather than shouted - the mark, the active nav
 * marker, a winning quote.
 *
 * Surfaces are a deliberate ladder, not one flat white: a cool grey workspace,
 * white content cards with a hairline and the faintest lift, a warmer grey for
 * grouped regions inside them (table heads, toolbars, panel bars), and tinted
 * states for hover and selection. Shadows appear only where something is
 * genuinely above the page.
 *
 * Type is Inter at operational-but-legible sizes - a 21px page title, 14px
 * body, 13px table text, 28px figures - with tabular numerals everywhere a
 * column of numbers can form.
 *
 * Colour names predate this palette and are kept: hundreds of call sites say
 * `ink.5` or `rust.8`, and the names are what the ramps mean.
 */

/** Charcoal to near-white: body text, borders, surfaces, the shell. */
const ink: MantineColorsTuple = [
  '#f8f9fa',
  '#f0f2f4',
  '#e4e7eb',
  '#cfd4db',
  '#a8b0ba',
  '#737d8a',
  '#5a636e',
  '#404750',
  '#2a2f37',
  '#17191e',
];

/** Deep navy: the primary action, a selected state, a figure under scrutiny. */
const navy: MantineColorsTuple = [
  '#eff3fa',
  '#dce4f1',
  '#b5c5e1',
  '#8ba3cd',
  '#6886bb',
  '#4f6da6',
  '#3e5c91',
  '#314a76',
  '#263b5e',
  '#1c2d49',
];

/** House gold. The mark, the active marker, a winning quote. */
const brass: MantineColorsTuple = [
  '#fdf9f0',
  '#f9f1dc',
  '#f1deb2',
  '#e5c886',
  '#d8b35d',
  '#c79b3b',
  '#b4882f',
  '#967026',
  '#78591f',
  '#5b4418',
];

/** Steel blue: in flight - open, quoted, scheduled. Also links. */
const info: MantineColorsTuple = [
  '#eff4fb',
  '#dde8f7',
  '#b7cdee',
  '#8dafe2',
  '#6b95d8',
  '#4d81cf',
  '#3f72c0',
  '#355fa2',
  '#2c4e84',
  '#233e69',
];

/** Supply side of the market. */
const teal: MantineColorsTuple = [
  '#eff5f4',
  '#dde9e7',
  '#b9d3cf',
  '#90b9b3',
  '#6ba29b',
  '#55938b',
  '#478079',
  '#3a6a64',
  '#2f5651',
  '#24433f',
];

/** Waiting, follow-up required, overdue. */
const amber: MantineColorsTuple = [
  '#fff8e8',
  '#ffeec7',
  '#fcda93',
  '#f6c25c',
  '#ecac34',
  '#db991e',
  '#c08316',
  '#9c6b13',
  '#7d560f',
  '#5e410b',
];

/** Below cost, lost, cancelled, overdue. */
const rust: MantineColorsTuple = [
  '#fdf2f1',
  '#fbe0dd',
  '#f4bdb7',
  '#e9958d',
  '#dd7167',
  '#d0594e',
  '#be453b',
  '#a03830',
  '#812d26',
  '#62221d',
];

/** Margin, completed, active. */
const moss: MantineColorsTuple = [
  '#eff6f1',
  '#dcecdf',
  '#b7d8be',
  '#8dc097',
  '#66aa75',
  '#4d995f',
  '#3e8850',
  '#327141',
  '#295d36',
  '#1f482a',
];

export const FONT_SANS =
  'Inter, "Geist Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
/** Figures use the UI face with tabular numerals; no second family is loaded. */
export const FONT_MONO = FONT_SANS;

export const theme = createTheme({
  primaryColor: 'navy',
  primaryShade: { light: 8, dark: 7 },
  colors: {
    ink,
    navy,
    brass,
    info,
    teal,
    amber,
    rust,
    moss,
    //: Older call sites say `accent` for the gold and `slate`/`brand` for the neutrals.
    accent: brass,
    slate: ink,
    brand: navy,
  },
  white: '#ffffff',
  black: '#17191e',
  defaultRadius: 'md',

  fontFamily: FONT_SANS,
  fontFamilyMonospace: FONT_SANS,

  fontSizes: {
    xs: '0.75rem',
    sm: '0.8125rem',
    md: '0.875rem',
    lg: '1rem',
    xl: '1.125rem',
  },
  lineHeights: { xs: '1.4', sm: '1.45', md: '1.5', lg: '1.5', xl: '1.4' },

  headings: {
    fontFamily: FONT_SANS,
    fontWeight: '600',
    sizes: {
      h1: { fontSize: '1.3125rem', lineHeight: '1.3' },
      h2: { fontSize: '1.0625rem', lineHeight: '1.35' },
      h3: { fontSize: '0.9375rem', lineHeight: '1.4' },
      h4: { fontSize: '0.875rem', lineHeight: '1.45' },
      h5: { fontSize: '0.8125rem', lineHeight: '1.45' },
      h6: { fontSize: '0.75rem', lineHeight: '1.45' },
    },
  },

  radius: { xs: '3px', sm: '5px', md: '6px', lg: '8px', xl: '12px' },
  spacing: {
    xs: '0.375rem',
    sm: '0.5rem',
    md: '0.75rem',
    lg: '1rem',
    xl: '1.5rem',
  },

  /* A shadow means "this is above the page". Cards get the faintest lift; the
     rest is carried by one hairline. */
  shadows: {
    xs: '0 1px 2px rgba(23, 25, 30, 0.04)',
    sm: '0 1px 2px rgba(23, 25, 30, 0.04), 0 1px 3px -1px rgba(23, 25, 30, 0.05)',
    md: '0 2px 4px -1px rgba(23, 25, 30, 0.06), 0 6px 16px -4px rgba(23, 25, 30, 0.08)',
    lg: '0 8px 24px -6px rgba(23, 25, 30, 0.12)',
    xl: '0 20px 48px -12px rgba(23, 25, 30, 0.20)',
  },

  components: {
    Card: {
      defaultProps: { withBorder: true, radius: 'lg', shadow: 'sm', padding: 'lg' },
      styles: { root: { borderColor: 'var(--border)', background: 'var(--surface)' } },
    },
    Paper: { defaultProps: { radius: 'lg' } },
    Button: {
      defaultProps: { size: 'sm', fw: 550, radius: 'md' },
    },
    ActionIcon: { defaultProps: { variant: 'subtle', color: 'ink', radius: 'md' } },
    Badge: {
      defaultProps: { radius: 'sm', fw: 600, variant: 'light' },
      styles: { label: { letterSpacing: '0.01em', textTransform: 'none' } },
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
    Switch: { defaultProps: { size: 'sm', color: 'navy.8' } },
    Checkbox: { defaultProps: { size: 'sm', color: 'navy.8', radius: 'xs' } },
    SegmentedControl: {
      defaultProps: { size: 'sm', radius: 'md' },
      styles: {
        //: A white selected segment on a grey track; the label stays readable,
        //: which it does not when Mantine colours the indicator itself.
        root: { background: 'var(--canvas-deep)', border: '1px solid var(--border)' },
        indicator: { background: 'var(--surface)', boxShadow: 'var(--shadow-card)' },
        label: { color: 'var(--mantine-color-ink-6)', fontWeight: 500 },
      },
    },
    Modal: {
      defaultProps: {
        radius: 'lg',
        centered: true,
        padding: 'lg',
        shadow: 'xl',
        overlayProps: { backgroundOpacity: 0.45, blur: 2, color: '#17191e' },
      },
      styles: {
        title: { fontWeight: 600, fontSize: '1rem', lineHeight: 1.4 },
        header: { paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)' },
        body: { paddingTop: '1rem' },
      },
    },
    Drawer: {
      defaultProps: { padding: 'lg', shadow: 'xl' },
      styles: {
        title: { fontWeight: 600, fontSize: '1rem' },
        header: { borderBottom: '1px solid var(--border)' },
      },
    },
    Tooltip: {
      defaultProps: { radius: 'md', fz: 'xs', withArrow: false, color: 'ink.9' },
    },
    Table: { defaultProps: { striped: false, highlightOnHover: false } },
    Alert: {
      defaultProps: { radius: 'md', variant: 'light' },
      styles: { message: { fontSize: '0.8125rem' }, title: { fontSize: '0.875rem' } },
    },
    Tabs: { defaultProps: { keepMounted: false, color: 'navy.8' } },
    Loader: { defaultProps: { size: 'sm', color: 'navy.8' } },
    Anchor: { defaultProps: { fw: 500, underline: 'never', c: 'navy.7' } },
    Divider: { styles: { root: { borderColor: 'var(--border)' } } },
    Menu: { defaultProps: { radius: 'md', shadow: 'lg' } },
    Pagination: { defaultProps: { color: 'navy.8', radius: 'md', size: 'sm' } },
    Timeline: { defaultProps: { color: 'navy.8' } },
    Avatar: { defaultProps: { color: 'ink', radius: 'md' } },
    ThemeIcon: { defaultProps: { variant: 'light', color: 'ink', radius: 'md' } },
    Notification: { defaultProps: { radius: 'md' } },
  },
});

export type StatusTone = 'neutral' | 'active' | 'attention' | 'positive' | 'negative';

/**
 * Status → tone. A tone is rendered as a soft-tinted badge with a dot, so a
 * column of them reads as one calm list while the amber and red ones that need
 * a decision still carry.
 */
export const STATUS_TONES: Record<string, StatusTone> = {
  // master data / parties
  //: In flight, not finished - green is reserved for what has been won or done.
  ACTIVE: 'active',
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
