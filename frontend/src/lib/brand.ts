/**
 * Whose desk this is. The only place the software says a customer's name.
 *
 * Set per deployment through the build environment, so the same source ships
 * to anybody:
 *
 *   VITE_BRAND_NAME="Acme Polymers"
 *   VITE_BRAND_TAGLINE="Polymer trading"
 *
 * Unset, it falls back to the product's own name rather than to somebody
 * else's - a screen that says nothing is better than one advertising the last
 * customer to whoever is being shown it now.
 */

const name = (import.meta.env.VITE_BRAND_NAME as string | undefined)?.trim();
const tagline = (import.meta.env.VITE_BRAND_TAGLINE as string | undefined)?.trim();

export const BRAND = {
  /** The wordmark, in the shell, on the sign-in screen and on the portal. */
  name: name || 'Trader Desk',
  /** The line under it. Empty is fine; nothing is drawn. */
  tagline: tagline ?? 'Commodity trading',
  /** The letter in the square. Taken from the name so it never disagrees. */
  get mark(): string {
    return (this.name.trim()[0] ?? 'T').toUpperCase();
  },
} as const;

/**
 * A key for this browser's own stored preferences.
 *
 * Namespaced by the product rather than by a customer, so a deployment
 * rebranded tomorrow does not orphan what somebody saved today.
 */
export const storageKey = (suffix: string) => `trader-desk.${suffix}`;
