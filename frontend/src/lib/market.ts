/**
 * The desk's view of the market, derived from recorded inquiries.
 *
 * A supplier inquiry is an offer we could buy at; a customer inquiry is demand
 * we could sell into. Lining the two up per product gives the rate board: the
 * cheapest live offer, the richest live demand, and the spread between them.
 */

import type { InquiryListItem } from '@/api/types';

export type Side = 'supply' | 'demand';

export interface Quote {
  id: number;
  side: Side;
  productId: number;
  productName: string;
  partyName: string;
  partyId: number | null;
  /** Rupees per kilogram. */
  rate: number;
  /** Metric tonnes, when the unit is a weight; otherwise null. */
  tonnes: number | null;
  createdAt: string;
  active: boolean;
  location: string | null;
}

export function toQuote(row: InquiryListItem): Quote | null {
  if (row.inquiry_type === 'TRANSPORT') return null;
  if (!row.product_id || !row.rate) return null;
  const quantity = Number(row.quantity ?? 0);
  const tonnes = row.unit === 'MT' ? quantity : row.unit === 'KG' ? quantity / 1000 : null;
  return {
    id: row.id,
    side: row.inquiry_type === 'SUPPLIER' ? 'supply' : 'demand',
    productId: row.product_id,
    productName: row.product_name ?? `Product #${row.product_id}`,
    partyName: row.party_name ?? '—',
    partyId: row.party_id,
    rate: Number(row.rate),
    tonnes,
    createdAt: row.created_at,
    active: row.status === 'ACTIVE',
    location: row.location_name,
  };
}

export interface BoardLine {
  productId: number;
  productName: string;
  /** Cheapest live supplier offer - the price we could buy at. */
  bestBuy: Quote | null;
  /** Highest live customer rate - the price we could sell at. */
  bestSell: Quote | null;
  /** bestSell - bestBuy in ₹/kg; positive means a trade with margin exists. */
  spread: number | null;
  spreadPct: number | null;
  supply: Quote[];
  demand: Quote[];
  supplyTonnes: number;
  demandTonnes: number;
}

const sum = (values: Array<number | null>) =>
  values.reduce<number>((total, value) => total + (value ?? 0), 0);

/** One line per product with live quotes, the tradeable ones first. */
export function buildBoard(quotes: Quote[]): BoardLine[] {
  const byProduct = new Map<number, Quote[]>();
  for (const quote of quotes) {
    if (!quote.active) continue;
    const list = byProduct.get(quote.productId) ?? [];
    list.push(quote);
    byProduct.set(quote.productId, list);
  }

  const lines: BoardLine[] = [];
  for (const [productId, list] of byProduct) {
    const supply = list.filter((q) => q.side === 'supply').sort((a, b) => a.rate - b.rate);
    const demand = list.filter((q) => q.side === 'demand').sort((a, b) => b.rate - a.rate);
    const bestBuy = supply[0] ?? null;
    const bestSell = demand[0] ?? null;
    const spread = bestBuy && bestSell ? bestSell.rate - bestBuy.rate : null;
    lines.push({
      productId,
      productName: list[0].productName,
      bestBuy,
      bestSell,
      spread,
      spreadPct: spread !== null && bestBuy ? (spread / bestBuy.rate) * 100 : null,
      supply,
      demand,
      supplyTonnes: sum(supply.map((q) => q.tonnes)),
      demandTonnes: sum(demand.map((q) => q.tonnes)),
    });
  }

  return lines.sort((a, b) => {
    // Two-sided markets first, widest spread on top; then by depth.
    const aBoth = a.spread !== null ? 1 : 0;
    const bBoth = b.spread !== null ? 1 : 0;
    if (aBoth !== bBoth) return bBoth - aBoth;
    if (a.spread !== null && b.spread !== null) return b.spread - a.spread;
    return b.supply.length + b.demand.length - (a.supply.length + a.demand.length);
  });
}

/** Counts per day for the last `days` days, oldest first - for sparklines. */
export function dailyCounts(dates: string[], days = 14): number[] {
  const buckets = new Array<number>(days).fill(0);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  for (const value of dates) {
    const day = new Date(value);
    day.setHours(0, 0, 0, 0);
    const age = Math.round((today.getTime() - day.getTime()) / 86_400_000);
    if (age >= 0 && age < days) buckets[days - 1 - age] += 1;
  }
  return buckets;
}

export const fmtRate = (value: number) =>
  `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const fmtTonnes = (value: number) =>
  `${value.toLocaleString('en-IN', { maximumFractionDigits: 1 })} MT`;
