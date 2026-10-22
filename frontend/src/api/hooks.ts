/** React Query hooks. Lists are server-paginated, filtered and sorted. */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';

import { ApiError, api } from './client';
import type { QueryValue } from './client';
import type {
  PartyApplication,
  Activity,
  ActivityWithChain,
  ConflictCheckResult,
  DuplicateCheckResult,
  Application,
  AuditLog,
  Dashboard,
  DeskEnquiry,
  DeskEnquiryCounts,
  EnquiryLink,
  Grade,
  InquiryDetail,
  InquiryListItem,
  Location,
  Manufacturer,
  Material,
  MetaEnums,
  Note,
  Page,
  Party360,
  BidDetail,
  BidEvent,
  BidListItem,
  BidParticipant,
  BidQuote,
  PartyBookSummary,
  PartyDetail,
  PartyListItem,
  PartyLocation,
  PartyProduct,
  PartyMergeResult,
  PartyMoveResult,
  Product,
  ProductPartyLink,
  SalespersonWorkload,
  SearchResults,
  User,
} from './types';

export type Params = Record<string, QueryValue>;

const stale = { staleTime: 30_000 };

function listQuery<T>(key: string, path: string, params: Params) {
  return {
    queryKey: [key, params],
    queryFn: () => api.get<Page<T>>(path, params),
    placeholderData: keepPreviousData,
  };
}

/* ----------------------------- master data ----------------------------- */
export const useMaterials = (params: Params = {}) =>
  useQuery(listQuery<Material>('materials', '/materials', params));
export const useGrades = (params: Params = {}) =>
  useQuery(listQuery<Grade>('grades', '/grades', params));
export const useManufacturers = (params: Params = {}) =>
  useQuery(listQuery<Manufacturer>('manufacturers', '/manufacturers', params));
export const useApplications = (params: Params = {}) =>
  useQuery(listQuery<Application>('applications', '/applications', params));
export const useProducts = (params: Params = {}) =>
  useQuery(listQuery<Product>('products', '/products', params));
export const useLocations = (params: Params = {}) =>
  useQuery(listQuery<Location>('locations', '/locations', params));
/** Distinct areas already in use - offered as suggestions and filter options. */
export const useLocationAreas = () =>
  useQuery({
    queryKey: ['locations', 'areas'],
    queryFn: () => api.get<string[]>('/locations/areas'),
    ...stale,
  });

export const useProduct = (id?: number) =>
  useQuery({
    queryKey: ['product', id],
    queryFn: () => api.get<Product>(`/products/${id}`),
    enabled: Boolean(id),
  });

export const useProductSuppliers = (id?: number) =>
  useQuery({
    queryKey: ['product-suppliers', id],
    queryFn: () => api.get<ProductPartyLink[]>(`/products/${id}/suppliers`),
    enabled: Boolean(id),
  });

export const useProductCustomers = (id?: number) =>
  useQuery({
    queryKey: ['product-customers', id],
    queryFn: () => api.get<ProductPartyLink[]>(`/products/${id}/customers`),
    enabled: Boolean(id),
  });

/* -------------------------------- parties ------------------------------- */
export const useParties = (params: Params = {}) =>
  useQuery(listQuery<PartyListItem>('parties', '/parties', params));

/** Whole-book figures for the cards above the table, not just the loaded page. */
export const usePartyBookSummary = (partyType: string) =>
  useQuery({
    queryKey: ['party-book-summary', partyType],
    queryFn: () => api.get<PartyBookSummary>('/parties/summary', { party_type: partyType }),
    staleTime: 60_000,
  });

export const useParty = (id?: number) =>
  useQuery({
    queryKey: ['party', id],
    queryFn: () => api.get<PartyDetail>(`/parties/${id}`),
    enabled: Boolean(id),
  });

export const useParty360 = (id?: number) =>
  useQuery({
    queryKey: ['party-overview', id],
    queryFn: () => api.get<Party360>(`/parties/${id}/overview`),
    enabled: Boolean(id),
  });

/**
 * "Did you mean this party?" - called as the user types a new name or phone.
 * A warning, never a block.
 */
export const useDuplicateCheck = (params: {
  party_type?: string;
  name?: string;
  phone?: string;
  gst_number?: string;
  exclude_id?: number;
  enabled?: boolean;
}) => {
  const { enabled = true, ...query } = params;
  const hasInput =
    (query.name ?? '').trim().length >= 3 ||
    (query.phone ?? '').replace(/\D/g, '').length >= 6 ||
    (query.gst_number ?? '').trim().length >= 10;
  return useQuery({
    queryKey: ['party-duplicates', query],
    queryFn: () => api.get<DuplicateCheckResult>('/parties/duplicates', query),
    enabled: enabled && hasInput,
    staleTime: 10_000,
  });
};

/* ------------------------------- inquiries ------------------------------ */
export const useInquiries = (params: Params = {}) =>
  useQuery(listQuery<InquiryListItem>('inquiries', '/inquiries', params));

export const useInquiry = (id?: number) =>
  useQuery({
    queryKey: ['inquiry', id],
    queryFn: () => api.get<InquiryDetail>(`/inquiries/${id}`),
    enabled: Boolean(id),
  });

/* ---------------------------------- bids -------------------------------- */
/**
 * A live auction, so the desk watches it move rather than pressing refresh.
 * Polling stops once a bid is closed - there is nothing left to change - and
 * the browser pauses it while the tab is in the background.
 */
const LIVE_MS = 10_000;

export const useBids = (params: Params = {}) =>
  useQuery({
    ...listQuery<BidListItem>('bids', '/bids', params),
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });

export const useBid = (id?: number) =>
  useQuery({
    queryKey: ['bid', id],
    queryFn: () => api.get<BidDetail>(`/bids/${id}`),
    enabled: Boolean(id),
    refetchInterval: (query) => (query.state.data?.status === 'OPEN' ? LIVE_MS : false),
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

/** The offers on one bid, a page at a time - a hundred may be bidding. */
export const useBidQuotes = (id: number | undefined, params: Params = {}, live = false) =>
  useQuery({
    ...listQuery<BidQuote>(`bid-quotes-${id}`, `/bids/${id}/quotes`, params),
    enabled: Boolean(id),
    refetchInterval: live ? LIVE_MS : false,
    refetchIntervalInBackground: false,
  });

/** Everyone invited, a page at a time, with their links. */
export const useBidParticipants = (id: number | undefined, params: Params = {}, live = false) =>
  useQuery({
    ...listQuery<BidParticipant>(`bid-participants-${id}`, `/bids/${id}/participants`, params),
    enabled: Boolean(id),
    refetchInterval: live ? LIVE_MS : false,
    refetchIntervalInBackground: false,
  });

/** The latest entries only: a busy auction writes hundreds of them. */
export const useBidHistory = (id?: number, live = false, params: Params = {}) =>
  useQuery({
    ...listQuery<BidEvent>(`bid-history-${id}`, `/bids/${id}/history`, { page_size: 8, ...params }),
    enabled: Boolean(id),
    refetchInterval: live ? LIVE_MS : false,
    refetchIntervalInBackground: false,
  });

/* ------------------- enquiries parties raise themselves ------------------ */
/**
 * The inbox for enquiries that arrived through a portal link.
 *
 * Parties write in whenever they like, so this polls: an enquiry sitting
 * unread is the one thing on the desk that somebody outside is waiting on.
 */
export const usePortalEnquiries = (params: Params = {}) =>
  useQuery({
    ...listQuery<DeskEnquiry>('portal-enquiries', '/portal-enquiries', params),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

export const usePortalEnquiry = (id?: number) =>
  useQuery({
    queryKey: ['portal-enquiry', id],
    queryFn: () => api.get<DeskEnquiry>(`/portal-enquiries/${id}`),
    enabled: Boolean(id),
  });

/** For the badge on the nav: how many are waiting to be read. */
export const usePortalEnquiryCounts = () =>
  useQuery({
    queryKey: ['portal-enquiry-counts'],
    queryFn: () => api.get<DeskEnquiryCounts>('/portal-enquiries/counts'),
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

/** The link this party uses to raise enquiries. Issues their code on first ask. */
export const useEnquiryLink = (partyId?: number) =>
  useQuery({
    queryKey: ['enquiry-link', partyId],
    queryFn: () => api.get<EnquiryLink>(`/portal-enquiries/link/${partyId}`),
    enabled: Boolean(partyId),
    staleTime: Infinity,
  });

/* ------------------------------- activities ----------------------------- */
export const useActivities = (params: Params = {}) =>
  useQuery(listQuery<Activity>('activities', '/activities', params));

export const useActivity = (id?: number) =>
  useQuery({
    queryKey: ['activity', id],
    queryFn: () => api.get<ActivityWithChain>(`/activities/${id}`),
    enabled: Boolean(id),
  });

export const useSalespeopleWorkload = (includeInactive = false) =>
  useQuery({
    queryKey: ['salespeople-workload', includeInactive],
    queryFn: () =>
      api.get<SalespersonWorkload[]>('/activities/salespeople/workload', {
        include_inactive: includeInactive,
      }),
  });

export const useActivityCalendar = (
  dateFrom: string,
  dateTo: string,
  salespersonId?: number | null,
) =>
  useQuery({
    queryKey: ['activity-calendar', dateFrom, dateTo, salespersonId ?? null],
    queryFn: () =>
      api.get<Activity[]>('/activities/calendar', {
        date_from: dateFrom,
        date_to: dateTo,
        salesperson_id: salespersonId ?? undefined,
      }),
    enabled: Boolean(dateFrom && dateTo),
  });

/** Scheduling conflict warning for a salesperson at a given time. */
export const useConflictCheck = (
  salespersonId: number | null | undefined,
  scheduledAt: string | null | undefined,
  excludeActivityId?: number,
) =>
  useQuery({
    queryKey: ['conflicts', salespersonId ?? null, scheduledAt ?? null, excludeActivityId ?? null],
    queryFn: () =>
      api.get<ConflictCheckResult>('/activities/conflicts/check', {
        salesperson_id: salespersonId ?? undefined,
        scheduled_at: scheduledAt ?? undefined,
        exclude_activity_id: excludeActivityId,
      }),
    enabled: Boolean(salespersonId && scheduledAt),
    staleTime: 5_000,
  });

/* --------------------------------- notes -------------------------------- */
export const useNotes = (params: Params = {}) =>
  useQuery(listQuery<Note>('notes', '/notes', params));

/* -------------------------------- system -------------------------------- */
export const useDashboard = () =>
  useQuery({ queryKey: ['dashboard'], queryFn: () => api.get<Dashboard>('/dashboard') });

export const useMeta = () =>
  useQuery({
    queryKey: ['meta'],
    queryFn: () => api.get<MetaEnums>('/meta/enums'),
    staleTime: Infinity,
  });

export const useSearch = (q: string, enabled = true) =>
  useQuery({
    queryKey: ['search', q],
    queryFn: () => api.get<SearchResults>('/search', { q }),
    enabled: enabled && q.trim().length > 0,
    ...stale,
  });

export const useUsers = (params: Params = {}) =>
  useQuery(listQuery<User>('users', '/users', params));

export const useAuditLogs = (params: Params = {}) =>
  useQuery(listQuery<AuditLog>('audit-logs', '/audit-logs', params));

/* ------------------------------- mutations ------------------------------ */
/** Keys invalidated after a successful write, so lists and 360 views refresh. */
const INVALIDATE_ALL = [
  'materials',
  'grades',
  'manufacturers',
  'applications',
  'products',
  'product',
  'product-suppliers',
  'product-customers',
  'locations',
  'parties',
  'party',
  'party-overview',
  'inquiries',
  'inquiry',
  'activities',
  'activity',
  'notes',
  'dashboard',
  'users',
  'audit-logs',
  'search',
  'party-duplicates',
  'portal-enquiries',
  'portal-enquiry',
  'portal-enquiry-counts',
  'select',
  'salespeople-workload',
  'activity-calendar',
  'conflicts',
];

export function useApiMutation<TInput, TResult>(
  mutate: (input: TInput) => Promise<TResult>,
  options: { successMessage?: string; invalidate?: string[] } = {},
) {
  const queryClient = useQueryClient();
  return useMutation<TResult, ApiError, TInput>({
    mutationFn: mutate,
    onSuccess: () => {
      (options.invalidate ?? INVALIDATE_ALL).forEach((key) =>
        queryClient.invalidateQueries({ queryKey: [key] }),
      );
      if (options.successMessage) {
        notifications.show({ color: 'teal', message: options.successMessage });
      }
    },
    onError: (error) => {
      notifications.show({
        color: 'red',
        title: error.status === 409 ? 'Conflict' : 'Could not save',
        message: error.message,
        autoClose: 6000,
      });
    },
  });
}

/* Convenience writers used across the app. */
export const createEntity = <T>(path: string, body: unknown) => api.post<T>(path, body);
export const patchEntity = <T>(path: string, body: unknown) => api.patch<T>(path, body);

export const bidApi = {
  create: (body: unknown) => api.post<BidDetail>('/bids', body),
  patch: (id: number, body: unknown) => api.patch<BidDetail>(`/bids/${id}`, body),
  addParticipants: (id: number, partyIds: number[]) =>
    api.post<BidDetail>(`/bids/${id}/participants`, { party_ids: partyIds }),
  removeParticipant: (id: number, participantId: number) =>
    api.delete<BidDetail>(`/bids/${id}/participants/${participantId}`),
  publish: (id: number) => api.post<BidDetail>(`/bids/${id}/publish`),
  close: (id: number, withoutWinner = false) =>
    api.post<BidDetail>(`/bids/${id}/close?without_winner=${withoutWinner}`),
  award: (id: number, quoteId: number) =>
    api.post<BidDetail>(`/bids/${id}/award`, { quote_id: quoteId }),
};

export const portalEnquiryApi = {
  /** Create the inquiry this enquiry asked for, on the desk's own terms. */
  accept: (id: number, body: unknown) => api.post<DeskEnquiry>(`/portal-enquiries/${id}/accept`, body),
  decline: (id: number) => api.post<DeskEnquiry>(`/portal-enquiries/${id}/decline`),
};

export const inquiryApi = {
  create: (body: unknown) => api.post<InquiryDetail>('/inquiries', body),
  /** Edit any field, including `status` (ACTIVE <-> CLOSED). */
  patch: (id: number, body: unknown) => api.patch<InquiryDetail>(`/inquiries/${id}`, body),
};

export const locationApi = {
  /** Saved to Master Data, so the next inquiry can pick it too. */
  create: (body: unknown) => api.post<Location>('/locations', body),
};

export const activityApi = {
  create: (body: unknown) => api.post<Activity>('/activities', body),
  patch: (id: number, body: unknown) => api.patch<Activity>(`/activities/${id}`, body),
  assign: (id: number, salespersonId: number | null) =>
    api.post<Activity>(`/activities/${id}/assign`, {
      assigned_salesperson_id: salespersonId,
    }),
  complete: (id: number, body: unknown) =>
    api.post<{ activity: Activity; follow_up: Activity | null }>(
      `/activities/${id}/complete`,
      body,
    ),
};

export const partyApi = {
  create: (body: unknown) => api.post<PartyDetail>('/parties', body),
  /** Name + phone only; lands in Master Data as a PROSPECT of the given type. */
  createProspect: (body: { party_type: string; name: string; phone: string }) =>
    api.post<PartyDetail>('/parties/prospects', body),
  patch: (id: number, body: unknown) => api.patch<PartyDetail>(`/parties/${id}`, body),
  promote: (id: number) => api.post<PartyDetail>(`/parties/${id}/promote`),
  /** Move a party into another book: a customer you also buy from, say. */
  move: (id: number, partyType: string) =>
    api.post<PartyMoveResult>(`/parties/${id}/move`, { party_type: partyType }),
  merge: (survivorId: number, loserId: number, note?: string | null) =>
    api.post<PartyMergeResult>(`/parties/${survivorId}/merge`, {
      loser_id: loserId,
      note: note ?? null,
    }),
  addLocation: (id: number, body: unknown) =>
    api.post<PartyLocation>(`/parties/${id}/locations`, body),
  updateLocation: (id: number, linkId: number, body: unknown) =>
    api.patch<PartyLocation>(`/parties/${id}/locations/${linkId}`, body),
  removeLocation: (id: number, linkId: number) =>
    api.delete<{ message: string }>(`/parties/${id}/locations/${linkId}`),
  addProduct: (id: number, body: unknown) =>
    api.post<PartyProduct>(`/parties/${id}/products`, body),
  updateProduct: (id: number, linkId: number, body: unknown) =>
    api.patch<PartyProduct>(`/parties/${id}/products/${linkId}`, body),
  removeProduct: (id: number, linkId: number) =>
    api.delete<{ message: string }>(`/parties/${id}/products/${linkId}`),
  addApplication: (id: number, body: unknown) =>
    api.post<PartyApplication>(`/parties/${id}/applications`, body),
  removeApplication: (id: number, linkId: number) =>
    api.delete<{ message: string }>(`/parties/${id}/applications/${linkId}`),
};

export const noteApi = {
  create: (body: unknown) => api.post<Note>('/notes', body),
  patch: (id: number, body: unknown) => api.patch<Note>(`/notes/${id}`, body),
};
