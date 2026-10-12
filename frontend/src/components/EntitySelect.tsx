/**
 * Searchable, server-backed pickers. Typing queries the backend (`?q=`), so the
 * browser never loads whole tables.
 */

import { Loader, MultiSelect, Select } from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { api } from '@/api/client';
import type { QueryValue } from '@/api/client';
import type { Page } from '@/api/types';

export type EntityKind =
  | 'product'
  | 'party'
  | 'material'
  | 'grade'
  | 'manufacturer'
  | 'application'
  | 'location'
  | 'user';

interface Row {
  id: number;
  name?: string;
  display_name?: string;
  label?: string | null;
  area?: string | null;
  city?: string;
  state?: string | null;
  status?: string;
}

const PATHS: Record<EntityKind, string> = {
  product: '/products',
  party: '/parties',
  material: '/materials',
  grade: '/grades',
  manufacturer: '/manufacturers',
  application: '/applications',
  location: '/locations',
  user: '/users',
};

function labelOf(kind: EntityKind, row: Row): string {
  if (kind === 'product') return row.display_name ?? `#${row.id}`;
  if (kind === 'location') {
    return [row.label, row.area, row.city, row.state].filter(Boolean).join(' - ') || `#${row.id}`;
  }
  return row.name ?? `#${row.id}`;
}

interface BaseProps {
  kind: EntityKind;
  label?: string;
  placeholder?: string;
  description?: string;
  filters?: Record<string, QueryValue>;
  /** Only ACTIVE records by default - inactive master data is not selectable. */
  includeInactive?: boolean;
  disabled?: boolean;
  required?: boolean;
  error?: string | null;
  clearable?: boolean;
}

function useEntityOptions(
  kind: EntityKind,
  filters: Record<string, QueryValue> | undefined,
  includeInactive: boolean,
  search: string,
  enabled = true,
) {
  const [debounced] = useDebouncedValue(search, 250);
  const params = useMemo(
    () => ({
      q: debounced || undefined,
      page_size: 25,
      ...(includeInactive ? {} : { status: 'ACTIVE' }),
      ...filters,
    }),
    [debounced, includeInactive, filters],
  );
  const query = useQuery({
    queryKey: ['select', kind, params],
    queryFn: () => api.get<Page<Row>>(PATHS[kind], params),
    enabled,
    staleTime: 15_000,
  });
  const options = (query.data?.items ?? []).map((row) => ({
    value: String(row.id),
    label: labelOf(kind, row),
  }));
  return { options, loading: query.isFetching };
}

export function EntitySelect({
  kind,
  value,
  onChange,
  label,
  placeholder,
  description,
  filters,
  includeInactive = false,
  disabled,
  required,
  error,
  clearable = true,
  initialLabel,
}: BaseProps & {
  value: number | null;
  onChange: (value: number | null) => void;
  initialLabel?: string | null;
}) {
  const [search, setSearch] = useState('');
  const { options, loading } = useEntityOptions(
    kind,
    filters,
    includeInactive,
    search,
    !disabled,
  );

  const data = useMemo(() => {
    if (value && initialLabel && !options.some((option) => option.value === String(value))) {
      return [{ value: String(value), label: initialLabel }, ...options];
    }
    return options;
  }, [options, value, initialLabel]);

  return (
    <Select
      label={label}
      description={description}
      placeholder={placeholder ?? 'Type to search...'}
      searchable
      clearable={clearable}
      disabled={disabled}
      required={required}
      error={error}
      nothingFoundMessage={loading ? 'Searching...' : 'No matches'}
      rightSection={loading ? <Loader size={14} /> : undefined}
      data={data}
      value={value ? String(value) : null}
      searchValue={search}
      onSearchChange={setSearch}
      onChange={(next) => onChange(next ? Number(next) : null)}
      comboboxProps={{ withinPortal: true }}
      limit={25}
    />
  );
}

export function EntityMultiSelect({
  kind,
  value,
  onChange,
  label,
  placeholder,
  description,
  filters,
  includeInactive = false,
  disabled,
  initialOptions = [],
}: BaseProps & {
  value: number[];
  onChange: (value: number[]) => void;
  initialOptions?: { id: number; label: string }[];
}) {
  const [search, setSearch] = useState('');
  const { options, loading } = useEntityOptions(kind, filters, includeInactive, search);

  const data = useMemo(() => {
    const merged = new Map(options.map((option) => [option.value, option]));
    initialOptions.forEach((option) => {
      if (!merged.has(String(option.id))) {
        merged.set(String(option.id), { value: String(option.id), label: option.label });
      }
    });
    return Array.from(merged.values());
  }, [options, initialOptions]);

  return (
    <MultiSelect
      label={label}
      description={description}
      placeholder={placeholder ?? 'Type to search...'}
      searchable
      clearable
      disabled={disabled}
      data={data}
      value={value.map(String)}
      searchValue={search}
      onSearchChange={setSearch}
      onChange={(next) => onChange(next.map(Number))}
      nothingFoundMessage={loading ? 'Searching...' : 'No matches'}
      comboboxProps={{ withinPortal: true }}
      limit={25}
    />
  );
}
