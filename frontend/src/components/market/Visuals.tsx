/**
 * Small, hand-drawn visuals for the trading desk. Plain SVG - no chart library -
 * so they stay crisp, light and exactly on-brand.
 */

import { Box, Group, Text, Tooltip } from '@mantine/core';
import { useMemo } from 'react';

import type { Quote } from '@/lib/market';
import { fmtRate } from '@/lib/market';

/* ------------------------------------------------------------------ avatar */

/** Deep, desaturated tones - a party's colour is stable, never loud. */
const AVATAR_TONES = [
  ['#231f1b', '#416e59'],
  ['#96701a', '#6e5511'],
  ['#555049', '#416e59'],
  ['#b4871f', '#8b6c15'],
  ['#416e59', '#231f1b'],
  ['#726e67', '#555049'],
  ['#8b3c35', '#6e2f29'],
  ['#caa441', '#a98319'],
];

function hash(text: string): number {
  let value = 0;
  for (let i = 0; i < text.length; i += 1) value = (value * 31 + text.charCodeAt(i)) | 0;
  return Math.abs(value);
}

export function initialsOf(name?: string | null): string {
  if (!name) return '?';
  const words = name
    .replace(/[^\p{L}\p{N} ]/gu, ' ')
    .split(' ')
    .filter(Boolean);
  if (!words.length) return name.slice(0, 2);
  if (/^\d/.test(words[0])) return '#';
  return words
    .slice(0, 2)
    .map((word) => word[0]!.toUpperCase())
    .join('');
}

export function PartyAvatar({ name, size = 32 }: { name?: string | null; size?: number }) {
  const [from, to] = AVATAR_TONES[hash(name ?? '') % AVATAR_TONES.length];
  return (
    <span
      className="party-avatar"
      style={{
        width: size,
        height: size,
        fontSize: Math.round(size * 0.38),
        borderRadius: Math.round(size * 0.3),
        background: `linear-gradient(145deg, ${from}, ${to})`,
      }}
      aria-hidden
    >
      {initialsOf(name)}
    </span>
  );
}

/* --------------------------------------------------------------- sparkline */

export function Sparkline({
  values,
  width = 120,
  height = 34,
  color = 'var(--brass)',
  fill = true,
}: {
  values: number[];
  width?: number;
  height?: number;
  color?: string;
  fill?: boolean;
}) {
  const id = useMemo(() => `spark-${Math.random().toString(36).slice(2, 9)}`, []);
  if (values.length < 2) return null;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = max - min || 1;
  const step = width / (values.length - 1);
  const points = values.map((value, index) => [
    index * step,
    height - 3 - ((value - min) / span) * (height - 6),
  ]);
  const line = points
    .map(([x, y], index) => `${index ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(' ');
  const area = `${line} L${width},${height} L0,${height} Z`;
  const [lastX, lastY] = points[points.length - 1];
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ display: 'block' }}
    >
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {fill && <path d={area} fill={`url(#${id})`} />}
      <path
        d={line}
        fill="none"
        stroke={color}
        strokeWidth={1.6}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={lastX} cy={lastY} r={2.6} fill={color} />
    </svg>
  );
}

/* ----------------------------------------------------------- market meter */

/**
 * Where quotes sit on one price axis: supply in forest green, demand in gold,
 * the highlighted quote as a brass marker. Read at a glance: is this cheap?
 */
export function MarketMeter({
  quotes,
  highlightId,
  height = 64,
  showScale = true,
}: {
  quotes: Quote[];
  highlightId?: number;
  height?: number;
  /** Min / max labels under the axis; off in dense rows. */
  showScale?: boolean;
}) {
  if (!quotes.length) return null;
  const rates = quotes.map((q) => q.rate);
  const lo = Math.min(...rates);
  const hi = Math.max(...rates);
  const pad = Math.max((hi - lo) * 0.12, hi * 0.004, 0.5);
  const min = lo - pad;
  const max = hi + pad;
  const pos = (rate: number) => ((rate - min) / (max - min)) * 100;

  const supply = quotes.filter((q) => q.side === 'supply');
  const demand = quotes.filter((q) => q.side === 'demand');
  const band = (list: Quote[]) =>
    list.length
      ? {
          left: pos(Math.min(...list.map((q) => q.rate))),
          right: pos(Math.max(...list.map((q) => q.rate))),
        }
      : null;
  const supplyBand = band(supply);
  const demandBand = band(demand);

  return (
    <Box pos="relative" h={height} mt={4}>
      {/* axis */}
      <Box
        pos="absolute"
        left={0}
        right={0}
        top={height / 2}
        h={2}
        style={{ background: 'var(--hairline)', borderRadius: 2 }}
      />
      {supplyBand && (
        <Box
          pos="absolute"
          top={height / 2 - 9}
          h={8}
          style={{
            left: `${supplyBand.left}%`,
            width: `${Math.max(supplyBand.right - supplyBand.left, 0.8)}%`,
            background: 'var(--supply-soft)',
            border: '1px solid rgba(65,110,89,0.35)',
            borderRadius: 4,
          }}
        />
      )}
      {demandBand && (
        <Box
          pos="absolute"
          top={height / 2 + 3}
          h={8}
          style={{
            left: `${demandBand.left}%`,
            width: `${Math.max(demandBand.right - demandBand.left, 0.8)}%`,
            background: 'var(--demand-soft)',
            border: '1px solid rgba(199,149,42,0.45)',
            borderRadius: 4,
          }}
        />
      )}
      {quotes.map((quote) => {
        const highlighted = quote.id === highlightId;
        const supplySide = quote.side === 'supply';
        return (
          <Tooltip
            key={quote.id}
            label={`${quote.partyName} · ${fmtRate(quote.rate)}/kg`}
            withinPortal
          >
            <Box
              pos="absolute"
              style={{
                left: `calc(${pos(quote.rate)}% - ${highlighted ? 7 : 4}px)`,
                top: highlighted ? height / 2 - 7 : supplySide ? height / 2 - 13 : height / 2 + 7,
                width: highlighted ? 14 : 8,
                height: highlighted ? 14 : 8,
                borderRadius: highlighted ? 4 : 99,
                transform: highlighted ? 'rotate(45deg)' : undefined,
                background: highlighted
                  ? 'var(--brass)'
                  : supplySide
                    ? 'var(--supply)'
                    : 'var(--demand)',
                border: '2px solid #fff',
                boxShadow: highlighted
                  ? '0 0 0 3px rgba(199,149,42,0.25), 0 2px 6px rgba(18,16,16,0.25)'
                  : '0 1px 3px rgba(18,16,16,0.25)',
                zIndex: highlighted ? 2 : 1,
                cursor: 'default',
              }}
            />
          </Tooltip>
        );
      })}
      {showScale && (
        <Group justify="space-between" pos="absolute" left={0} right={0} bottom={-4}>
          <Text fz={11} c="ink.5" className="figure">
            {fmtRate(lo)}
          </Text>
          <Text fz={11} c="ink.5" className="figure">
            {fmtRate(hi)}
          </Text>
        </Group>
      )}
    </Box>
  );
}

/* -------------------------------------------------------------- trend chart */

/**
 * Rates over time for one product: every recorded quote as a dot, the two
 * sides joined chronologically. Supply below demand is a market with margin.
 */
export function TrendChart({ quotes, height = 220 }: { quotes: Quote[]; height?: number }) {
  const width = 720;
  const padL = 56;
  const padR = 16;
  const padT = 14;
  const padB = 28;

  const prepared = useMemo(() => {
    const sorted = [...quotes].sort((a, b) => a.createdAt.localeCompare(b.createdAt));
    if (!sorted.length) return null;
    const times = sorted.map((q) => new Date(q.createdAt).getTime());
    const t0 = Math.min(...times);
    const t1 = Math.max(...times);
    const rates = sorted.map((q) => q.rate);
    const lo = Math.min(...rates);
    const hi = Math.max(...rates);
    const pad = Math.max((hi - lo) * 0.18, 0.5);
    const min = lo - pad;
    const max = hi + pad;
    const x = (t: number) =>
      padL +
      (t1 === t0 ? (width - padL - padR) / 2 : ((t - t0) / (t1 - t0)) * (width - padL - padR));
    const y = (r: number) => padT + (1 - (r - min) / (max - min)) * (height - padT - padB);
    const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => min + f * (max - min));
    const dayTicks = t1 === t0 ? [t0] : [t0, t0 + (t1 - t0) / 2, t1];
    return { sorted, x, y, ticks, dayTicks };
  }, [quotes, height]);

  if (!prepared) return null;
  const { sorted, x, y, ticks, dayTicks } = prepared;
  const path = (side: 'supply' | 'demand') =>
    sorted
      .filter((q) => q.side === side)
      .map(
        (q, i) =>
          `${i ? 'L' : 'M'}${x(new Date(q.createdAt).getTime()).toFixed(1)},${y(q.rate).toFixed(1)}`,
      )
      .join(' ');

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      style={{ display: 'block' }}
    >
      {ticks.map((tick) => (
        <g key={tick}>
          <line x1={padL} x2={width - padR} y1={y(tick)} y2={y(tick)} stroke="#eceae6" />
          <text
            x={padL - 10}
            y={y(tick) + 4}
            textAnchor="end"
            fontSize="11"
            fill="#726e67"
            fontFamily="IBM Plex Mono, monospace"
          >
            {tick.toFixed(1)}
          </text>
        </g>
      ))}
      {dayTicks.map((tick) => (
        <text
          key={tick}
          x={x(tick)}
          y={height - 8}
          textAnchor="middle"
          fontSize="11"
          fill="#726e67"
        >
          {new Date(tick).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
        </text>
      ))}
      <path
        d={path('supply')}
        fill="none"
        stroke="#416e59"
        strokeWidth={2}
        strokeLinejoin="round"
      />
      <path
        d={path('demand')}
        fill="none"
        stroke="#c7952a"
        strokeWidth={2}
        strokeLinejoin="round"
        strokeDasharray="5 4"
      />
      {sorted.map((q) => (
        <circle
          key={q.id}
          cx={x(new Date(q.createdAt).getTime())}
          cy={y(q.rate)}
          r={q.active ? 4.5 : 3.5}
          fill={q.active ? (q.side === 'supply' ? '#416e59' : '#c7952a') : '#fff'}
          stroke={q.side === 'supply' ? '#416e59' : '#c7952a'}
          strokeWidth={2}
        >
          <title>{`${q.partyName} · ₹${q.rate.toFixed(2)}/kg${q.active ? '' : ' (closed)'}`}</title>
        </circle>
      ))}
    </svg>
  );
}

/* ------------------------------------------------------------ spread strip */

/**
 * One row of the board as a picture: every offer (green) and every bid (gold)
 * on a shared price axis, with the gap between the best of each shaded - green
 * when you can buy below what you can sell, red when you cannot.
 */
export function SpreadStrip({
  supply,
  demand,
  height = 30,
}: {
  supply: Quote[];
  demand: Quote[];
  height?: number;
}) {
  const all = [...supply, ...demand];
  if (!all.length) return null;
  const rates = all.map((q) => q.rate);
  const lo = Math.min(...rates);
  const hi = Math.max(...rates);
  const pad = Math.max((hi - lo) * 0.15, hi * 0.003, 0.3);
  const min = lo - pad;
  const max = hi + pad;
  const pos = (rate: number) => ((rate - min) / (max - min)) * 100;
  const bestBuy = supply.length ? Math.min(...supply.map((q) => q.rate)) : null;
  const bestSell = demand.length ? Math.max(...demand.map((q) => q.rate)) : null;
  const mid = height / 2;

  return (
    <Box pos="relative" h={height} style={{ minWidth: 120 }}>
      <Box
        pos="absolute"
        left={0}
        right={0}
        top={mid - 1}
        h={2}
        style={{ background: 'var(--hairline)', borderRadius: 2 }}
      />
      {bestBuy !== null && bestSell !== null && (
        <Box
          pos="absolute"
          top={mid - 5}
          h={10}
          style={{
            left: `${pos(Math.min(bestBuy, bestSell))}%`,
            width: `${Math.abs(pos(bestSell) - pos(bestBuy))}%`,
            background: bestSell >= bestBuy ? 'rgba(73,120,93,0.22)' : 'rgba(200,90,82,0.22)',
            borderRadius: 3,
          }}
        />
      )}
      {all.map((quote) => (
        <Tooltip
          key={quote.id}
          label={`${quote.side === 'supply' ? 'Offer' : 'Bid'} · ${quote.partyName} · ${fmtRate(quote.rate)}/kg`}
          withinPortal
        >
          <Box
            pos="absolute"
            style={{
              left: `calc(${pos(quote.rate)}% - 5px)`,
              top: mid - 5,
              width: 10,
              height: 10,
              borderRadius: quote.side === 'supply' ? 99 : 2,
              background: quote.side === 'supply' ? 'var(--supply)' : 'var(--demand)',
              border: '2px solid #fff',
              boxShadow: '0 1px 3px rgba(18,16,16,0.3)',
            }}
          />
        </Tooltip>
      ))}
    </Box>
  );
}

/* --------------------------------------------------------------------- kpi */

export function KpiTile({
  label,
  value,
  hint,
  accent = 'var(--hairline)',
  spark,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  /** Colour of the top rule - ties the tile to a side of the market. */
  accent?: string;
  spark?: number[];
}) {
  return (
    <div className="kpi" style={{ ['--kpi-accent' as string]: accent }}>
      <div className="kpi-label">{label}</div>
      <Group justify="space-between" align="flex-end" wrap="nowrap" gap="xs">
        <div className="kpi-value">{value}</div>
        {spark && spark.some(Boolean) && (
          <Box mb={6}>
            <Sparkline values={spark} width={78} height={28} color={accent} />
          </Box>
        )}
      </Group>
      {hint && <div className="kpi-hint">{hint}</div>}
    </div>
  );
}
