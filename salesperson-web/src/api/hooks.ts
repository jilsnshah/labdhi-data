import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import type { CompleteResponse, Dashboard, FieldActivity, FieldContact, FieldStats } from './types';

export const useDashboard = (enabled = true) =>
  useQuery({
    queryKey: ['dashboard'],
    enabled,
    queryFn: () => api.get<Dashboard>('/salesperson/dashboard'),
    staleTime: 15_000,
  });

export const useToday = () =>
  useQuery({
    queryKey: ['today'],
    queryFn: () => api.get<FieldActivity[]>('/salesperson/activities/today'),
  });

export const useVisits = () =>
  useQuery({
    queryKey: ['visits'],
    queryFn: () => api.get<FieldActivity[]>('/salesperson/visits/today'),
  });

export const useUpcoming = () =>
  useQuery({
    queryKey: ['upcoming'],
    queryFn: () => api.get<FieldActivity[]>('/salesperson/activities/upcoming'),
  });

export const useHistory = () =>
  useQuery({
    queryKey: ['history'],
    queryFn: () => api.get<FieldActivity[]>('/salesperson/activities/history'),
  });

export const useActivity = (id: number | undefined) =>
  useQuery({
    queryKey: ['activity', id],
    queryFn: () => api.get<FieldActivity>(`/salesperson/activities/${id}`),
    enabled: Boolean(id),
  });

export const useContacts = (q: string) =>
  useQuery({
    queryKey: ['contacts', q],
    queryFn: () =>
      api.get<FieldContact[]>(`/salesperson/contacts${q ? `?q=${encodeURIComponent(q)}` : ''}`),
    placeholderData: (previous) => previous,
  });

export const useStats = () =>
  useQuery({
    queryKey: ['stats'],
    queryFn: () => api.get<FieldStats>('/salesperson/stats'),
    staleTime: 60_000,
  });

/** Everything changes after a write, and the data set is tiny - refetch all. */
export function useRefreshAll() {
  const queryClient = useQueryClient();
  return () => {
    [
      'dashboard',
      'today',
      'visits',
      'upcoming',
      'history',
      'activity',
      'contacts',
      'stats',
    ].forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }));
  };
}

export function useStartActivity() {
  const refresh = useRefreshAll();
  return useMutation({
    mutationFn: (id: number) => api.post<FieldActivity>(`/salesperson/activities/${id}/start`),
    onSuccess: refresh,
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (body: { current_password: string; new_password: string }) =>
      api.post<{ message: string }>('/salesperson/change-password', body),
  });
}

export type { CompleteResponse };
