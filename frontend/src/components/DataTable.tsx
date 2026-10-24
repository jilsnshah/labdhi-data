import {
  Box,
  Card,
  Center,
  Group,
  LoadingOverlay,
  Pagination,
  Select,
  Table,
  Text,
  UnstyledButton,
} from '@mantine/core';
import { IconChevronDown, IconChevronUp, IconSelector } from '@tabler/icons-react';
import type { ReactNode } from 'react';

import { EmptyState } from '@/components/ui';

export interface Column<T> {
  key: string;
  label: string;
  render: (row: T) => ReactNode;
  sortable?: boolean;
  width?: number | string;
  align?: 'left' | 'right' | 'center';
  /**
   * On a phone each row is drawn as a card instead of a table row (see
   * `.data-table` in styles.css). These control how a column behaves there.
   */
  //: Headline of the card. Defaults to the first column.
  cardTitle?: boolean;
  //: Shown under the title with no label of its own.
  cardMeta?: boolean;
  //: Left out of the card entirely - noise on a small screen.
  cardHidden?: boolean;
}

export interface SortState {
  sortBy?: string;
  sortDir: 'asc' | 'desc';
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  total?: number;
  page?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  sort?: SortState;
  onSortChange?: (sort: SortState) => void;
  loading?: boolean;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  emptyHint?: string;
  rowKey?: (row: T) => string | number;
  /** Marks a row as the one that leads - the best quote, the winner. */
  rowHighlight?: (row: T) => boolean;
  /** Draw the surrounding card. Off when the table already sits in a SectionCard. */
  framed?: boolean;
  /**
   * Fill the remaining viewport height: the header stays pinned, the body
   * scrolls, and pagination never walks off the bottom of the page.
   */
  fill?: boolean;
}

export function DataTable<T extends { id?: number }>({
  columns,
  rows,
  total,
  page = 1,
  pageSize = 25,
  onPageChange,
  onPageSizeChange,
  sort,
  onSortChange,
  loading,
  onRowClick,
  emptyMessage = 'Nothing to show yet.',
  emptyHint,
  rowKey,
  rowHighlight,
  framed = true,
  fill = false,
}: DataTableProps<T>) {
  const pages = total && pageSize ? Math.max(1, Math.ceil(total / pageSize)) : 1;
  //: Does a column claim the card headline, or does the first one get it?
  const titled = columns.some((column) => column.cardTitle);

  const toggleSort = (key: string) => {
    if (!onSortChange) return;
    if (sort?.sortBy === key) {
      onSortChange({ sortBy: key, sortDir: sort.sortDir === 'asc' ? 'desc' : 'asc' });
    } else {
      onSortChange({ sortBy: key, sortDir: 'asc' });
    }
  };

  const showFooter = total !== undefined && Boolean(onPageChange);

  const body = (
    <Box
      pos="relative"
      style={
        fill
          ? { display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }
          : undefined
      }
    >
      <LoadingOverlay
        visible={Boolean(loading)}
        zIndex={2}
        overlayProps={{ blur: 1.5, backgroundOpacity: 0.45, color: '#fff' }}
        loaderProps={{ size: 'sm' }}
      />

      <Box style={fill ? { flex: 1, minHeight: 0, overflowY: 'auto' } : undefined}>
        <Table.ScrollContainer minWidth={680} type="native">
          <Table
            className="data-table"
            data-sticky={fill ? 'true' : undefined}
            verticalSpacing={6}
            horizontalSpacing="lg"
            fz="sm"
          >
            <Table.Thead>
              <Table.Tr>
                {columns.map((column) => {
                  const active = sort?.sortBy === column.key;
                  const label = (
                    <Text
                      fz={11}
                      fw={600}
                      tt="uppercase"
                      c={active ? 'ink.8' : 'ink.6'}
                      ta={column.align}
                      style={{ letterSpacing: '0.06em' }}
                    >
                      {column.label}
                    </Text>
                  );
                  return (
                    <Table.Th key={column.key} style={{ width: column.width }}>
                      {column.sortable && onSortChange ? (
                        <UnstyledButton onClick={() => toggleSort(column.key)} w="100%">
                          <Group
                            gap={4}
                            wrap="nowrap"
                            justify={column.align === 'right' ? 'flex-end' : 'flex-start'}
                          >
                            {label}
                            {active ? (
                              sort.sortDir === 'asc' ? (
                                <IconChevronUp size={13} stroke={2.4} />
                              ) : (
                                <IconChevronDown size={13} stroke={2.4} />
                              )
                            ) : (
                              <IconSelector size={13} opacity={0.35} />
                            )}
                          </Group>
                        </UnstyledButton>
                      ) : (
                        label
                      )}
                    </Table.Th>
                  );
                })}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((row, index) => (
                <Table.Tr
                  key={rowKey ? rowKey(row) : (row.id ?? index)}
                  data-clickable={onRowClick ? 'true' : undefined}
                  data-highlight={rowHighlight?.(row) ? 'true' : undefined}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  style={onRowClick ? { cursor: 'pointer' } : undefined}
                >
                  {columns.map((column, columnIndex) => (
                    <Table.Td
                      key={column.key}
                      align={column.align}
                      data-label={column.label || undefined}
                      data-card={
                        column.cardHidden
                          ? 'hidden'
                          : column.cardTitle || (columnIndex === 0 && !titled)
                            ? 'title'
                            : column.cardMeta
                              ? 'meta'
                              : undefined
                      }
                    >
                      {column.render(row)}
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))}
              {!rows.length && !loading && (
                <Table.Tr>
                  <Table.Td colSpan={columns.length}>
                    <Center>
                      <EmptyState title={emptyMessage} hint={emptyHint} compact />
                    </Center>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Box>

      {showFooter && (
        <Group
          justify="space-between"
          px="md"
          py={6}
          gap="sm"
          className="table-footer"
          style={{ borderTop: '1px solid var(--border)' }}
        >
          <Group gap="sm">
            <Text fz="xs" c="ink.6" fw={500} className="mono-tight">
              {total === 0
                ? 'No records'
                : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total!)} of ${total}`}
            </Text>
            {onPageSizeChange && total! > 10 && (
              <Select
                size="xs"
                w={78}
                data={['10', '25', '50', '100']}
                value={String(pageSize)}
                onChange={(value) => value && onPageSizeChange(Number(value))}
                allowDeselect={false}
                aria-label="Rows per page"
              />
            )}
          </Group>
          {pages > 1 && (
            <Pagination
              size="sm"
              radius="md"
              value={page}
              total={pages}
              onChange={onPageChange}
              withEdges={pages > 5}
            />
          )}
        </Group>
      )}
    </Box>
  );

  return framed ? (
    <Card
      padding={0}
      style={{
        overflow: 'hidden',
        ...(fill
          ? {
              //: Grow to the rows, shrink to the viewport - never a card of
              //: empty white under six records.
              flex: '0 1 auto',
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
            }
          : {}),
      }}
    >
      {body}
    </Card>
  ) : (
    body
  );
}
