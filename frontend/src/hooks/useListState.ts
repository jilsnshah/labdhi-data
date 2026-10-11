import { useDebouncedValue } from '@mantine/hooks';
import { useCallback, useMemo, useState } from 'react';

import type { SortState } from '@/components/DataTable';

export interface ListState<F extends Record<string, unknown>> {
  q: string;
  setQ: (value: string) => void;
  page: number;
  setPage: (value: number) => void;
  pageSize: number;
  setPageSize: (value: number) => void;
  sort: SortState;
  setSort: (value: SortState) => void;
  filters: F;
  setFilter: <K extends keyof F>(key: K, value: F[K]) => void;
  resetFilters: () => void;
  /** Query params ready to hand to the API. */
  params: Record<string, string | number | boolean | undefined | (string | number)[]>;
}

export function useListState<F extends Record<string, unknown>>(
  initialFilters: F,
  initialSort: SortState = { sortDir: 'asc' },
  initialPageSize = 25,
): ListState<F> {
  const [q, setQValue] = useState('');
  const [debouncedQ] = useDebouncedValue(q, 300);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSizeValue] = useState(initialPageSize);
  const [sort, setSortValue] = useState<SortState>(initialSort);
  const [filters, setFilters] = useState<F>(initialFilters);

  const setQ = useCallback((value: string) => {
    setQValue(value);
    setPage(1);
  }, []);

  const setPageSize = useCallback((value: number) => {
    setPageSizeValue(value);
    setPage(1);
  }, []);

  const setSort = useCallback((value: SortState) => {
    setSortValue(value);
    setPage(1);
  }, []);

  const setFilter = useCallback(<K extends keyof F>(key: K, value: F[K]) => {
    setFilters((current) => ({ ...current, [key]: value }));
    setPage(1);
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(initialFilters);
    setQValue('');
    setPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const params = useMemo(() => {
    const cleaned: Record<string, never> = {} as Record<string, never>;
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        (cleaned as Record<string, unknown>)[key] = value;
      }
    });
    return {
      ...cleaned,
      q: debouncedQ || undefined,
      page,
      page_size: pageSize,
      sort_by: sort.sortBy,
      sort_dir: sort.sortDir,
    };
  }, [filters, debouncedQ, page, pageSize, sort]);

  return {
    q,
    setQ,
    page,
    setPage,
    pageSize,
    setPageSize,
    sort,
    setSort,
    filters,
    setFilter,
    resetFilters,
    params,
  };
}
