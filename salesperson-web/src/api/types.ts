export type ActivityType = 'CALL' | 'WHATSAPP' | 'SMS' | 'VISIT' | 'EMAIL' | 'MEETING';
export type ActivityStatus = 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
export type ActivityOutcome =
  | 'COMPLETED'
  | 'CUSTOMER_INTERESTED'
  | 'CUSTOMER_NOT_INTERESTED'
  | 'FOLLOW_UP_REQUIRED'
  | 'NO_RESPONSE'
  | 'RESCHEDULED'
  | 'OTHER';

export interface Profile {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  role: string;
}

export interface ActivityCustomer {
  name: string;
  contact_person: string | null;
  phone: string | null;
}

export interface ActivityLocation {
  label: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  latitude: string | null;
  longitude: string | null;
  formatted: string;
  maps_url: string;
}

export interface FieldActivity {
  id: number;
  activity_type: ActivityType;
  status: ActivityStatus;
  subject: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  purpose: string | null;
  completion_note: string | null;
  outcome_code: ActivityOutcome | null;
  parent_activity_id: number | null;
  is_visit: boolean;
  can_complete: boolean;
  /** Logged by the salesperson (a cold call or visit), not assigned by the office. */
  self_logged: boolean;
  customer: ActivityCustomer;
  location: ActivityLocation | null;
}

export interface DayCounts {
  today_total: number;
  today_pending: number;
  today_completed: number;
  today_visits: number;
  overdue: number;
  upcoming: number;
}

export interface Dashboard {
  profile: Profile;
  counts: DayCounts;
  today: FieldActivity[];
  overdue: FieldActivity[];
  next_activity: FieldActivity | null;
}

export interface LoginResponse {
  token: { access_token: string; token_type: string; expires_in_minutes: number };
  user: { id: number; name: string; email: string; role: string; status: string };
}

export interface CompleteResponse {
  activity: FieldActivity;
  already_completed: boolean;
}

/** Someone this salesperson has already worked with; `ref` is an own activity id. */
export interface FieldContact {
  ref: number;
  name: string;
  contact_person: string | null;
  phone: string | null;
  party_type: 'CUSTOMER' | 'SUPPLIER' | string;
  is_prospect: boolean;
  place: string | null;
  last_activity_at: string | null;
  activity_count: number;
}

export interface NewContact {
  name: string;
  phone: string | null;
  contact_person: string | null;
  party_type: 'CUSTOMER' | 'SUPPLIER';
}

export interface LogActivityRequest {
  contact_ref?: number | null;
  new_contact?: NewContact | null;
  activity_type: ActivityType;
  done: boolean;
  outcome_code?: ActivityOutcome | null;
  note?: string | null;
  at?: string | null;
  place?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  client_token?: string | null;
}

export interface LogActivityResponse {
  activity: FieldActivity;
  duplicate: boolean;
  new_contact_created: boolean;
}

export interface DayTally {
  date: string;
  completed: number;
}

export interface FieldStats {
  days: DayTally[];
  completed_7d: number;
  visits_7d: number;
  calls_7d: number;
  self_logged_7d: number;
  new_contacts_7d: number;
  on_time_rate: number | null;
}
