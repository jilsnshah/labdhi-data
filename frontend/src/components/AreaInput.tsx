/**
 * Area of a location: free text, with the areas already in use suggested as you
 * type - so the desk picks "Shapar" again instead of inventing "shapar gidc".
 */

import { Autocomplete } from '@mantine/core';

import { useLocationAreas } from '@/api/hooks';

export function AreaInput({
  value,
  onChange,
  label = 'Area',
}: {
  value: string;
  onChange: (value: string) => void;
  label?: string;
}) {
  const { data: areas } = useLocationAreas();
  return (
    <Autocomplete
      label={label}
      placeholder="e.g. Shapar, GIDC Vapi"
      data={areas ?? []}
      value={value}
      onChange={onChange}
      limit={8}
      comboboxProps={{ withinPortal: true }}
    />
  );
}
