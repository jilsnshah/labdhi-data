import { Group, Stack, Text } from '@mantine/core';
import { useNavigate } from 'react-router-dom';

import type { InquiryListItem, InquiryType } from '@/api/types';
import { DataTable } from '@/components/DataTable';
import type { Column, SortState } from '@/components/DataTable';
import { StatusBadge } from '@/components/StatusBadge';
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
              <Group gap={6} wrap="nowrap">
                <Text fz="sm" fw={550} truncate maw={190}>
                  {row.party_name ?? '—'}
                </Text>
                {row.party_stage === 'PROSPECT' && (
                  <Text fz="xs" c="amber.8">
                    prospect
                  </Text>
                )}
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
                <Text fz="sm" c={row.location_name ? undefined : 'dimmed'} truncate maw={380}>
                  {row.location_name ?? '—'}
                </Text>
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
          <Text fz="sm" fw={650} className="mono-tight">
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
