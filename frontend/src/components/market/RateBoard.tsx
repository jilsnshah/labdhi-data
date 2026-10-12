/**
 * The rate board: for every product with live quotes, the cheapest offer we
 * could buy, the best demand we could sell into, and the spread between them.
 * This is the desk's one-glance answer to "where is there a trade?".
 */

import { Anchor, Box, Group, Stack, Text } from '@mantine/core';
import { Link } from 'react-router-dom';

import type { BoardLine, Quote } from '@/lib/market';
import { fmtRate, fmtTonnes } from '@/lib/market';
import { SpreadStrip } from './Visuals';

function Side({ quote, side }: { quote: Quote | null; side: 'supply' | 'demand' }) {
  if (!quote) {
    return (
      <Text fz="sm" c="ink.4">
        {side === 'supply' ? 'No offer' : 'No demand'}
      </Text>
    );
  }
  return (
    <Stack gap={1} style={{ minWidth: 0 }}>
      <Anchor
        component={Link}
        to={`/inquiries/${quote.id}`}
        fz={17}
        fw={600}
        className="figure"
        c={side === 'supply' ? 'teal.9' : 'accent.8'}
        style={{ lineHeight: 1.2 }}
      >
        {fmtRate(quote.rate)}
      </Anchor>
      <Text fz="xs" c="ink.5" truncate>
        {quote.partyName}
      </Text>
    </Stack>
  );
}

export function RateBoard({ lines, limit }: { lines: BoardLine[]; limit?: number }) {
  const shown = limit ? lines.slice(0, limit) : lines;
  if (!shown.length) {
    return (
      <Box p="xl">
        <Text fz="sm" c="ink.5" ta="center">
          No live quotes with a rate yet. Record supplier and customer inquiries to build the board.
        </Text>
      </Box>
    );
  }
  return (
    <div className="board">
      <div className="board-row board-head">
        <span className="block-label">Product</span>
        <span className="side-tag" data-side="supply">
          Best buy
        </span>
        <span className="side-tag" data-side="demand">
          Best sell
        </span>
        <span className="block-label" style={{ textAlign: 'right' }}>
          Spread / kg
        </span>
        <span className="block-label">Market</span>
      </div>
      {shown.map((line) => {
        const sign = line.spread === null ? 'none' : line.spread >= 0 ? 'pos' : 'neg';
        return (
          <div className="board-row" key={line.productId}>
            <Stack gap={2} style={{ minWidth: 0 }}>
              <Text fz="sm" fw={600} c="ink.9" truncate>
                {line.productName}
              </Text>
              <Text fz="xs" c="ink.5">
                {line.supply.length} offer{line.supply.length === 1 ? '' : 's'}
                {line.supplyTonnes ? ` · ${fmtTonnes(line.supplyTonnes)}` : ''}
                {'  ·  '}
                {line.demand.length} buyer{line.demand.length === 1 ? '' : 's'}
                {line.demandTonnes ? ` · ${fmtTonnes(line.demandTonnes)}` : ''}
              </Text>
            </Stack>
            <Side quote={line.bestBuy} side="supply" />
            <Side quote={line.bestSell} side="demand" />
            <Group justify="flex-end">
              <span className="spread-chip" data-sign={sign}>
                <Text fz={15} fw={600} className="figure" c="inherit" lh={1.2}>
                  {line.spread === null
                    ? '—'
                    : `${line.spread >= 0 ? '+' : '−'}${fmtRate(Math.abs(line.spread))}`}
                </Text>
                <Text fz={11} c="inherit" opacity={0.8} lh={1.2}>
                  {line.spreadPct === null
                    ? 'one-sided'
                    : `${line.spreadPct >= 0 ? '+' : '−'}${Math.abs(line.spreadPct).toFixed(1)}%`}
                </Text>
              </span>
            </Group>
            <SpreadStrip supply={line.supply} demand={line.demand} />
          </div>
        );
      })}
    </div>
  );
}
