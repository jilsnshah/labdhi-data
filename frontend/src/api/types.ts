/** Types mirroring the backend Pydantic schemas (see /openapi.json). */

export type RecordStatus = 'ACTIVE' | 'INACTIVE';
export type UserRole = 'ADMIN' | 'USER' | 'SALESPERSON';
export type PartyType = 'CUSTOMER' | 'SUPPLIER' | 'TRANSPORTER';
/** How well we know a party. Orthogonal to `status`. */
export type PartyStage = 'PROSPECT' | 'ACTIVE' | 'MERGED';
export type PartySource = 'DESK' | 'QUICK_CREATE' | 'IMPORT' | 'FIELD';
export type LocationType = 'HEAD_OFFICE' | 'FACTORY' | 'WAREHOUSE' | 'DELIVERY_LOCATION' | 'OTHER';
export type PartyProductRelationship = 'SUPPLIES' | 'PURCHASES' | 'INTERESTED_IN';
export type InquiryType = 'CUSTOMER' | 'SUPPLIER' | 'TRANSPORT';
/** An inquiry is still being worked, or it is done. Nothing in between. */
export type InquiryStatus = 'ACTIVE' | 'CLOSED';
export type QuantityUnit = 'MT' | 'KG' | 'BAG' | 'LITRE' | 'PIECE';
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

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface IdName {
  id: number;
  name: string;
}

export interface User {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  role: UserRole;
  status: RecordStatus;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  token: { access_token: string; token_type: string; expires_in_minutes: number };
  user: User;
}

export interface Material {
  id: number;
  name: string;
  description: string | null;
  status: RecordStatus;
  grade_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface Grade {
  id: number;
  name: string;
  material_id: number;
  material: IdName;
  description: string | null;
  status: RecordStatus;
  created_at: string;
  updated_at: string;
}

export interface Manufacturer {
  id: number;
  name: string;
  code: string | null;
  description: string | null;
  status: RecordStatus;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: number;
  name: string;
  description: string | null;
  status: RecordStatus;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: number;
  display_name: string;
  description: string | null;
  status: RecordStatus;
  material_id: number;
  grade_id: number;
  manufacturer_id: number;
  material: IdName;
  grade: IdName;
  manufacturer: IdName;
  applications: IdName[];
  created_at: string;
  updated_at: string;
}

export interface ProductPartyLink {
  party_id: number;
  party_name: string;
  party_type: string;
  relationship_type: string;
  phone: string | null;
  city: string | null;
  notes: string | null;
}

export interface Location {
  id: number;
  label: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  /** Locality within the city, e.g. Shapar or GIDC Vapi. */
  area: string | null;
  city: string;
  state: string | null;
  country: string;
  pincode: string | null;
  latitude: string | null;
  longitude: string | null;
  status: RecordStatus;
  display_name: string;
  created_at: string;
  updated_at: string;
}

export interface PartyLocation {
  id: number;
  party_id: number;
  location_id: number;
  location_type: LocationType;
  is_primary: boolean;
  location: Location;
}

export interface PartyProduct {
  id: number;
  party_id: number;
  product_id: number;
  relationship_type: PartyProductRelationship;
  notes: string | null;
  active: boolean;
  product: { id: number; display_name: string; status: RecordStatus };
}

export interface Party {
  id: number;
  name: string;
  party_type: PartyType;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  gst_number: string | null;
  notes: string | null;
  status: RecordStatus;
  stage: PartyStage;
  source: PartySource;
  merged_into_id: number | null;
  created_at: string;
  updated_at: string;
}

/** Minimum viable party, created inline from an inquiry or activity form. */
export interface PartyQuickCreate {
  name?: string | null;
  phone?: string | null;
  contact_person?: string | null;
  email?: string | null;
  gst_number?: string | null;
  city?: string | null;
  notes?: string | null;
  party_type?: PartyType;
}

export interface DuplicateCandidate {
  id: number;
  name: string;
  party_type: PartyType;
  stage: PartyStage;
  status: RecordStatus;
  phone: string | null;
  gst_number: string | null;
  city: string | null;
  match_reason: 'exact_gst' | 'exact_phone' | 'similar_name';
  score: number;
}

export interface DuplicateCheckResult {
  candidates: DuplicateCandidate[];
  has_exact_match: boolean;
}

export interface PartyMergeResult {
  survivor_id: number;
  merged_party_id: number;
  moved: Record<string, number>;
  message: string;
}

export interface PartyMoveResult {
  party: Party;
  /** Product links carried over, renamed to suit the new book. */
  products_repointed: number;
}

export interface PartyBookSummary {
  total: number;
  verified: number;
  prospects: number;
  with_open_inquiries: number;
  cities: number;
}

export interface PartyListItem extends Party {
  primary_city: string | null;
  product_count: number;
  open_inquiry_count: number;
}

export interface PartyApplication {
  id: number;
  party_id: number;
  application_id: number;
  notes: string | null;
  active: boolean;
  application: ApplicationRef;
}

export interface PartyDetail extends Party {
  locations: PartyLocation[];
  products: PartyProduct[];
  /** End-uses this party works in, independent of what they have traded. */
  applications: PartyApplication[];
}

export interface InquiryListItem {
  id: number;
  inquiry_type: InquiryType;
  status: InquiryStatus;
  title: string | null;
  party_id: number | null;
  party_name: string | null;
  party_stage: PartyStage | null;
  product_id: number | null;
  product_name: string | null;
  quantity: string | null;
  unit: QuantityUnit | null;
  /** Supplier / customer inquiries. */
  location_name: string | null;
  location_area: string | null;
  location_city: string | null;
  /** Rupees per kilogram (supplier / customer inquiries). */
  rate: string | null;
  /** Transport inquiries. */
  pickup_name: string | null;
  delivery_name: string | null;
  /** Rupees (transport inquiries). */
  price: string | null;
  created_by: number;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

/* ---------------------------------- bids -------------------------------- */
export type BidType = 'CUSTOMER' | 'SUPPLIER' | 'TRANSPORT';
export type BidStatus = 'DRAFT' | 'OPEN' | 'CLOSED';

export interface BidListItem {
  id: number;
  bid_type: BidType;
  status: BidStatus;
  title: string | null;
  product_id: number | null;
  product_name: string | null;
  quantity: string;
  unit: QuantityUnit;
  pickup_name: string | null;
  delivery_name: string | null;
  closes_at: string | null;
  participant_count: number;
  quote_count: number;
  /** Highest on a customer bid, lowest on the others. */
  best_price: string | null;
  winner_party_name: string | null;
  no_winner: boolean;
  created_by: number;
  created_by_name: string | null;
  created_at: string;
  published_at: string | null;
  closed_at: string | null;
}

export interface BidQuote {
  id: number;
  participant_id: number;
  price: string;
  quantity: string | null;
  notes: string | null;
  submitted_at: string;
  revision: number;
  party: PartyRef;
  is_winner: boolean;
}

export interface BidParticipant {
  id: number;
  party: PartyRef;
  first_opened_at: string | null;
  last_opened_at: string | null;
  quote: BidQuote | null;
  /** Copy-ready link to this party's view of this bid. */
  bid_link: string;
  /** Their permanent portal, listing every bid they are in. */
  portal_link: string;
}

export interface BidDetail {
  id: number;
  bid_type: BidType;
  status: BidStatus;
  title: string | null;
  quantity: string;
  unit: QuantityUnit;
  specifications: string | null;
  closes_at: string | null;
  product: ProductRef | null;
  pickup_location: LocationRef | null;
  delivery_location: LocationRef | null;
  created_by: number;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  closed_at: string | null;
  no_winner: boolean;
  awarded_at: string | null;
  creator: IdName | null;
  closer: IdName | null;
  participant_count: number;
  quote_count: number;
  winner: BidQuote | null;
  best_price: string | null;
}

export interface BidEvent {
  at: string;
  action: string;
  summary: string;
  actor: string | null;
}

/* The participant's side, served without a login. */
export interface PortalQuote {
  price: string;
  quantity: string | null;
  notes: string | null;
  submitted_at: string;
  revision: number;
}

/* ------------------- enquiries parties raise themselves ------------------ */
/** NEW: waiting on the desk. ACCEPTED: it became an inquiry. */
export type PortalEnquiryStatus = 'NEW' | 'ACCEPTED' | 'DECLINED';

/** One enquiry, as the party who sent it sees it. */
export interface PortalEnquiry {
  id: number;
  inquiry_type: InquiryType;
  status: PortalEnquiryStatus;
  /** Ours if they picked it from the list, theirs if they typed it. */
  product_name: string | null;
  quantity: string;
  unit: QuantityUnit;
  from_place: string | null;
  to_place: string | null;
  rate: string | null;
  notes: string | null;
  created_at: string;
}

/** A line in the grade picker on the public form. */
export interface PortalProduct {
  id: number;
  display_name: string;
}

/** The same enquiry in the desk's inbox, with who sent it. */
export interface DeskEnquiry {
  id: number;
  inquiry_type: InquiryType;
  status: PortalEnquiryStatus;
  party: PartyRef;
  /** Set when they found their grade in our list. */
  product: ProductRef | null;
  /** Set when they typed it instead. Exactly one of the two is filled in. */
  product_text: string | null;
  quantity: string;
  unit: QuantityUnit;
  from_place: string | null;
  to_place: string | null;
  rate: string | null;
  notes: string | null;
  created_at: string;
  /** The inquiry it became, once accepted. */
  inquiry_id: number | null;
  handled_at: string | null;
  handler: IdName | null;
}

export interface DeskEnquiryCounts {
  new: number;
  accepted: number;
  declined: number;
}

/** The links the desk copies for one party. */
export interface EnquiryLink {
  party_id: number;
  enquiry_link: string;
  portal_link: string;
}

/** WON: their offer was taken. NOT_SELECTED: another was, and they are not told whose. */
export type PortalResult = 'WON' | 'NOT_SELECTED' | 'NO_WINNER' | 'UNDECIDED';

export interface PortalBid {
  id: number;
  bid_type: BidType;
  status: BidStatus;
  title: string;
  product_name: string | null;
  quantity: string;
  unit: QuantityUnit;
  pickup_name: string | null;
  delivery_name: string | null;
  specifications: string | null;
  closes_at: string | null;
  best_is_highest: boolean;
  best_price: string | null;
  bidders: number;
  leading: boolean;
  my_quote: PortalQuote | null;
  can_quote: boolean;
  closed_at: string | null;
  /** How a closed bid ended for this party. Null while it is open. */
  result: PortalResult | null;
}

export interface PortalHome {
  participant_name: string;
  party_type: string;
  open_bids: PortalBid[];
  closed_bids: PortalBid[];
}

export interface PartyRef {
  id: number;
  name: string;
  party_type: PartyType;
  status: RecordStatus;
  stage: PartyStage;
}

export interface ProductRef {
  id: number;
  display_name: string;
  status: RecordStatus;
}

export interface LocationRef {
  id: number;
  label: string | null;
  area: string | null;
  city: string;
  state: string | null;
}

export interface TimelineEvent {
  at: string;
  kind: string;
  title: string;
  description: string | null;
  actor: string | null;
  ref_type: string | null;
  ref_id: number | null;
}

/** A recorded quotation. Exactly one of the three detail blocks is set. */
export interface InquiryDetail {
  id: number;
  inquiry_type: InquiryType;
  status: InquiryStatus;
  title: string | null;
  created_by: number;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  closed_by: number | null;
  creator: IdName | null;
  closer: IdName | null;
  customer_detail: {
    customer_id: number;
    product_id: number;
    quantity: string;
    unit: QuantityUnit;
    location_id: number | null;
    /** Rupees per kilogram. */
    rate: string | null;
    customer: PartyRef;
    product: ProductRef;
    location: LocationRef | null;
  } | null;
  supplier_detail: {
    supplier_id: number;
    product_id: number;
    quantity: string;
    unit: QuantityUnit;
    location_id: number | null;
    /** Rupees per kilogram. */
    rate: string | null;
    supplier: PartyRef;
    product: ProductRef;
    location: LocationRef | null;
  } | null;
  transport_detail: {
    transporter_id: number;
    quantity: string;
    unit: QuantityUnit;
    pickup_location_id: number;
    delivery_location_id: number;
    /** Rupees. */
    price: string | null;
    transporter: PartyRef;
    pickup_location: LocationRef;
    delivery_location: LocationRef;
  } | null;
}

export interface Activity {
  id: number;
  party_id: number;
  activity_type: ActivityType;
  status: ActivityStatus;
  subject: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  note: string | null;
  outcome: string | null;
  outcome_code: ActivityOutcome | null;
  parent_activity_id: number | null;
  related_inquiry_id: number | null;
  created_by: number;
  created_at: string;
  updated_at: string;
  party: PartyRef | null;
  creator: IdName | null;
  assigned_salesperson_id: number | null;
  assigned_salesperson: IdName | null;
  completed_by: number | null;
  completer: IdName | null;
  location_id: number | null;
  location: LocationRef | null;
  /** Text-only address or a spot pinned from the field app, when there is no location row. */
  location_snapshot: {
    label?: string | null;
    city?: string | null;
    latitude?: string | null;
    longitude?: string | null;
  } | null;
}

export interface SalespersonWorkload {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  status: RecordStatus;
  today_total: number;
  today_completed: number;
  today_pending: number;
  upcoming: number;
  overdue: number;
}

export interface ScheduleConflict {
  activity_id: number;
  scheduled_at: string;
  activity_type: ActivityType;
  customer_name: string;
  minutes_apart: number;
}

export interface ConflictCheckResult {
  has_conflict: boolean;
  conflicts: ScheduleConflict[];
}

export interface ActivityWithChain extends Activity {
  follow_ups: Activity[];
}

export interface Note {
  id: number;
  party_id: number;
  note: string;
  created_by: number;
  created_at: string;
  updated_at: string;
  creator: IdName | null;
  party: PartyRef | null;
}

export interface DashboardCounts {
  open_customer_inquiries: number;
  open_supplier_inquiries: number;
  open_transport_inquiries: number;
  todays_activities: number;
  overdue_activities: number;
  upcoming_followups: number;
  active_customers: number;
  active_suppliers: number;
  active_transporters: number;
  active_products: number;
  prospects: number;
}

export interface Dashboard {
  counts: DashboardCounts;
  todays_activities: Activity[];
  upcoming_followups: Activity[];
  recent_customers: Party[];
  recent_inquiries: InquiryListItem[];
  recently_closed_inquiries: InquiryListItem[];
}

export interface SearchHit {
  entity: string;
  id: number;
  label: string;
  sublabel: string | null;
  status: string | null;
}

export interface SearchResults {
  query: string;
  parties: SearchHit[];
  products: SearchHit[];
  materials: SearchHit[];
  grades: SearchHit[];
  manufacturers: SearchHit[];
  total: number;
}

export interface PartyStats {
  open_inquiries: number;
  closed_inquiries: number;
  activities: number;
  upcoming_activities: number;
  notes: number;
}

export interface Party360 {
  party: PartyDetail;
  stats: PartyStats;
  open_inquiries: InquiryListItem[];
  inquiry_history: InquiryListItem[];
  activities: Activity[];
  upcoming_activities: Activity[];
  notes: Note[];
  timeline: TimelineEvent[];
  deals: unknown[];
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  entity_type: string;
  entity_id: number;
  action: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  created_at: string;
  user: IdName | null;
}

export interface MetaEnums {
  record_status: RecordStatus[];
  party_type: PartyType[];
  location_type: LocationType[];
  party_product_relationship: PartyProductRelationship[];
  inquiry_type: InquiryType[];
  inquiry_status: InquiryStatus[];
  quantity_unit: QuantityUnit[];
  activity_type: ActivityType[];
  activity_status: ActivityStatus[];
  rules: {
    activity_transitions: Record<string, string[]>;
    party_product_relationships: Record<string, string[]>;
  };
}

export interface ApplicationRef {
  id: number;
  name: string;
  status: RecordStatus;
}

/** Logged by the salesperson themselves from the field app (a cold call or visit). */
export const isFieldLogged = (activity: {
  created_by: number;
  assigned_salesperson_id: number | null;
  parent_activity_id: number | null;
}): boolean =>
  activity.parent_activity_id == null &&
  activity.assigned_salesperson_id != null &&
  activity.created_by === activity.assigned_salesperson_id;
