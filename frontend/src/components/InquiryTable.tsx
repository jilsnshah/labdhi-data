import { Badge, Group, Stack, Text, Tooltip } from '@mantine/core';
import { useNavigate } from 'react-router-dom';

import type { InquiryListItem, InquiryType } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column, SortState } from '@/components/DataTable';
import { StatusBadge } from '@/components/StatusBadge';
import { PartyAvatar } from '@/components/market/Visuals';
import { formatDate, formatMoney, formatQuantity, formatRate } from '@/lib/format';

interface Props {
  rows: InquiryListItem[];
  total?: number;
  page?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  sort?: SortState;
  onSortChange?: (sort: SortState) => void;
  loading?: boolean;
  framed?: boolean;
  fill?: boolean;
  showType?: boolean;
  showParty?: boolean;
  /** Set when every row is one type, so columns can be named for it. */
  inquiryType?: InquiryType;
  /** Off in narrow summaries such as the dashboard. */
  showLocation?: boolean;
  emptyMessage?: string;
  emptyHint?: string;
}

/** One inquiry row, used by the list pages, the dashboard and party pages. */
export function InquiryTable({
  rows,
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  sort,
  onSortChange,
  loading,
  framed = true,
  fill = false,
  showType = false,
  showParty = true,
  inquiryType,
  showLocation = true,
  emptyMessage = 'No inquiries found.',
  emptyHint,
}: Props) {
  const navigate = useNavigate();

  const columns: Column<InquiryListItem>[] = [
    {
      key: 'id',
      label: 'Inquiry',
      sortable: true,
      width: 108,
      render: (row) => (
        <Stack gap={0}>
          <Group gap={6} wrap="nowrap">
            <Text fw={650} fz="sm">
              #{row.id}
            </Text>
            {showType && <StatusBadge value={row.inquiry_type} size="xs" />}
            {row.source === 'PORTAL' && (
              // Nobody keyed this one in: the party sent it through their link.
              <Tooltip label="Sent in by the party through their own link" withArrow>
                <Badge size="xs" variant="light" color="brass">
                  Theirs
                </Badge>
              </Tooltip>
            )}
          </Group>
          <Text fz="xs" c="dimmed">
            {formatDate(row.created_at)}
          </Text>
        </Stack>
      ),
    },
    ...(showParty
      ? [
          {
            key: 'party',
            label: 'Party',
            render: (row: InquiryListItem) => (
              <Group gap={10} wrap="nowrap">
                <PartyAvatar name={row.party_name} size={30} />
                <Stack gap={0} style={{ minWidth: 0 }}>
                  <Text fz="sm" fw={600} c="ink.9" truncate maw={200}>
                    {row.party_name ?? '—'}
                  </Text>
                  {row.party_stage === 'PROSPECT' && (
                    <Text fz={11} fw={600} c="brass.8" tt="uppercase" style={{ letterSpacing: '0.08em' }}>
                      Prospect
                    </Text>
                  )}
                </Stack>
              </Group>
            ),
          },
        ]
      : []),
    {
      key: 'what',
      label: inquiryType === 'TRANSPORT' ? 'Quantity' : 'Product and quantity',
      width: inquiryType === 'TRANSPORT' ? 120 : undefined,
      render: (row) =>
        row.inquiry_type === 'TRANSPORT' ? (
          <Stack gap={0}>
            {inquiryType !== 'TRANSPORT' && (
              <Text fz="sm" c="ink.6">
                Transport
              </Text>
            )}
            <Text fz="sm" className="mono-tight">
              {formatQuantity(row.quantity, row.unit ?? undefined)}
            </Text>
          </Stack>
        ) : (
          <Stack gap={0}>
            <Text fz="sm" truncate maw={260}>
              {row.product_name ?? '—'}
            </Text>
            <Text fz="xs" c="dimmed" className="mono-tight">
              {formatQuantity(row.quantity, row.unit ?? undefined)}
            </Text>
          </Stack>
        ),
    },
    ...(showLocation
      ? [
          {
            key: 'where',
            label: inquiryType === 'TRANSPORT' ? 'Route' : 'Location',
            render: (row) =>
              row.inquiry_type === 'TRANSPORT' ? (
                // The route is the substance of a transport quote: never cut it short.
                <Stack gap={0}>
                  <Text fz="sm" truncate maw={420}>
                    {row.pickup_name ?? '—'}
                  </Text>
                  <Text fz="sm" c="ink.6" truncate maw={420}>
                    → {row.delivery_name ?? '—'}
                  </Text>
                </Stack>
              ) : (
                // Area and city are what a trader reads; the full place is on hover.
                <Tooltip label={row.location_name} disabled={!row.location_name} withinPortal>
                  <Text fz="sm" c={row.location_city ? undefined : 'dimmed'} truncate maw={300}>
                    {[row.location_area, row.location_city].filter(Boolean).join(', ') || '—'}
                  </Text>
                </Tooltip>
              ),
          } as Column<InquiryListItem>,
        ]
      : []),
    {
      key: 'quote',
      label: inquiryType === 'TRANSPORT' ? 'Price' : inquiryType ? 'Rate (₹/kg)' : 'Rate / price',
      align: 'right',
      render: (row) => {
        const quoted = row.inquiry_type === 'TRANSPORT' ? row.price : row.rate;
        if (!quoted) {
          return (
            <Text fz="sm" c="dimmed">
              —
            </Text>
          );
        }
        return (
          <Text fz="sm" fw={600} className="figure">
            {row.inquiry_type === 'TRANSPORT' ? formatMoney(quoted) : formatRate(quoted)}
          </Text>
        );
      },
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      width: 120,
      render: (row) => <StatusBadge value={row.status} withDot />,
    },
  ];

  return (
    <DataTable
      columns={columns}
      rows={rows}
      total={total}
      page={page}
      pageSize={pageSize}
      onPageChange={onPageChange}
      onPageSizeChange={onPageSizeChange}
      sort={sort}
      onSortChange={onSortChange}
      loading={loading}
      framed={framed}
      fill={fill}
      onRowClick={(row) => navigate(`/inquiries/${row.id}`)}
      emptyMessage={emptyMessage}
      emptyHint={emptyHint}
    />
  );
}
