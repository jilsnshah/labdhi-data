/**
 * Whose desk this is. The only place the field app says a customer's name.
 *
 * Set per build through the environment, so the same source ships to anybody:
 *
 *   VITE_BRAND_NAME="Acme Polymers"
 *
 * Unset, it falls back to the product's own name rather than to somebody
 * else's.
 */

const name = (import.meta.env.VITE_BRAND_NAME as string | undefined)?.trim();

export const BRAND = {
  name: name || 'Trader Desk',
  get mark(): string {
    return (this.name.trim()[0] ?? 'T').toUpperCase();
  },
} as const;
