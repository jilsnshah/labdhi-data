# REST API

Base URL: `http://localhost:8000/api/v1` (interactive docs at `/docs`, OpenAPI at `/openapi.json`).

All endpoints except `POST /auth/login` require `Authorization: Bearer <token>`.

**Two surfaces, one API.** Everything under `/api/v1/...` is the back-office CRM and
requires an `ADMIN` or `USER` account. Everything under `/api/v1/salesperson/...` is the field
app and requires a `SALESPERSON` account. Each refuses the other role with `403`, and the field
endpoints are additionally scoped to the caller. See
[PERMISSIONS.md](PERMISSIONS.md) for the full matrix.

## Conventions

**Pagination** — every list endpoint accepts `page` (≥1) and `page_size` (1–200, default 25) and
returns:

```json
{ "items": [], "total": 42, "page": 1, "page_size": 25, "pages": 2 }
```

**Sorting** — `sort_by` (whitelisted per endpoint) and `sort_dir` (`asc|desc`). An unknown
`sort_by` returns `422` listing the allowed columns.

**Search** — `q` on every list endpoint; always server-side, never client-side filtering.

**Errors** — a single shape:

```json
{ "error": { "code": "validation_error", "message": "Grade 'MFI 0.3' belongs to material 'HDPE', not 'PVC'.", "field": "grade_id" } }
```

| Status | `code` | Meaning |
|---|---|---|
| 401 | `unauthorized` | missing/expired token, inactive account |
| 403 | `forbidden` | admin-only endpoint |
| 404 | `not_found` | unknown id |
| 409 | `conflict` | duplicate record, or an edit to a closed/completed record |
| 422 | `validation_error` | business rule or payload validation |

## Auth and users

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/login` | `{email, password}` → token + user |
| GET | `/auth/me` | current user |
| GET | `/users` | `q`, `status`, `role` (e.g. `SALESPERSON` for assignment pickers), `sort_by=name\|email\|created_at\|id` |
| POST | `/users` | admin only; `role` ∈ `ADMIN\|USER\|SALESPERSON`, optional `phone` |
| PATCH | `/users/{id}` | admin only; name, phone, role, status, password |

## Master data

| Method | Path | Filters |
|---|---|---|
| GET/POST | `/materials` | `q`, `status`, `sort_by=name\|created_at\|id` |
| GET/PATCH | `/materials/{id}` | |
| GET/POST | `/grades` | `q`, `material_id`, `status` |
| GET/PATCH | `/grades/{id}` | |
| GET/POST | `/manufacturers` | `q`, `status`, `sort_by=name\|code\|created_at\|id` |
| GET/PATCH | `/manufacturers/{id}` | |
| GET/POST | `/applications` | `q`, `status` |
| GET/PATCH | `/applications/{id}` | |
| GET/POST | `/products` | `q`, `material_id`, `grade_id`, `manufacturer_id`, `application_id`, `status` |
| GET/PATCH | `/products/{id}` | |
| GET | `/products/{id}/suppliers` | “which suppliers can provide product X?” |
| GET | `/products/{id}/customers` | “which customers want product X?” |
| GET/POST | `/locations` | `q` (label, area, city, state, address, pincode), `city`, `area` (exact, case-insensitive), `state`, `party_id`, `status`, `sort_by=city\|area\|label\|created_at\|id`. A location carries an optional `area` - the locality within the city (e.g. Shapar, GIDC Vapi) |
| GET | `/locations/areas` | distinct areas in use on active locations, alphabetical - for pickers and filters |
| GET/PATCH | `/locations/{id}` | |

Create a product:

```http
POST /api/v1/products
{ "material_id": 1, "grade_id": 14, "manufacturer_id": 8, "application_ids": [1, 2] }
```

`display_name` is optional and defaults to `"<manufacturer> <material> <grade>"`.
A grade that does not belong to the material is rejected with `422`; a duplicate
material+grade+manufacturer combination with `409`.

## Parties

| Method | Path | Notes |
|---|---|---|
| GET | `/parties` | `q`, `party_type`, `status`, `stage`, `include_merged`, `stale_days`, `city`, `location_id`, `product_id`, `sort_by=name\|created_at\|updated_at\|id`. Rows include `primary_city`, `product_count`, `open_inquiry_count`. |
| POST | `/parties` | optionally creates locations and product links inline; `stage` defaults to `ACTIVE` |
| GET/PATCH | `/parties/{id}` | |
| GET | `/parties/duplicates` | "did you mean this party?" - `party_type`, `name`, `phone`, `gst_number`, `exclude_id` |
| POST | `/parties/{id}/promote` | `PROSPECT` → `ACTIVE` |
| POST | `/parties/{id}/merge` | **admin only**; `{ "loser_id": 42, "note": "…" }` |
| GET | `/parties/{id}/overview` | **the 360° payload** |
| GET/POST | `/parties/{id}/locations` | `location_id` *or* an inline `location` object |
| PATCH/DELETE | `/parties/{id}/locations/{link_id}` | unlinks the location, never deletes it |
| GET/POST | `/parties/{id}/products` | `relationship_type` defaults by party type |
| PATCH/DELETE | `/parties/{id}/products/{link_id}` | |

```http
POST /api/v1/parties
{
  "name": "ABC Pipes",
  "party_type": "CUSTOMER",
  "phone": "+91 98250 11001",
  "locations": [{ "location": { "label": "Factory", "city": "Rajkot" }, "location_type": "FACTORY" }],
  "products": [{ "product_id": 5001, "relationship_type": "PURCHASES" }]
}
```

`GET /parties/{id}/overview` returns `party` (with locations and product links), `stats`,
`open_inquiries` (active), `inquiry_history` (closed), `activities`, `upcoming_activities`,
`notes`, a reverse-chronological `timeline`, and `deals` (always `[]` — the extension point for
the future trading module).

### Unknown parties

A party has a **`stage`** as well as a `status`:

| | meaning |
|---|---|
| `status` = `ACTIVE`/`INACTIVE` | may this be used for new business |
| `stage` = `PROSPECT` | met just now (walk-in, cold call); identity unverified. Still fully usable |
| `stage` = `ACTIVE` | a known, verified party |
| `stage` = `MERGED` | folded into another party; readable by id, never listed, refused for new records |

`source` records where the row came from: `DESK`, `QUICK_CREATE`, `IMPORT`, `FIELD`.

**From an inquiry form.** An unknown customer, supplier or transporter is saved first, from
just a name and a phone number, and then selected like any other party:

```http
POST /api/v1/parties/prospects
{ "party_type": "SUPPLIER", "name": "Gujarat Resins", "phone": "+91 90990 11223" }
```

It lands in Master Data as a `PROSPECT` (`source = QUICK_CREATE`) and is returned so the form can
select it immediately; later inquiries find it in the normal party search. Both fields are
required (`422` otherwise).

**From an activity.** `POST /activities` still accepts the party inline as a `new_party` block
(which carries its own `party_type`), created as a `PROSPECT` **in the same transaction** - if the
activity is rejected, no orphan party is left behind.

Rules:

* exactly one of the id or the `new_*` block (`422` otherwise);
* the block needs **at least a name or a phone** - with neither there is nothing to follow up on;
* a phone-only walk-in is displayed by its number until somebody names it;
* `city` is a shortcut that creates the primary location;
* a GST that already belongs to somebody returns `409` naming that party;
* only `ADMIN`/`USER` may do this - the field app has no party creation path at all.

**Name uniqueness** is enforced for verified parties only
(`UNIQUE (party_type, name) WHERE stage <> 'PROSPECT'`): two different walk-ins may both be
called "Patel Traders", but a verified duplicate is still refused. Promoting a prospect into a
name that is already taken returns `409` - merge them instead.

**Duplicate detection** is a warning, never a block:

```http
GET /api/v1/parties/duplicates?party_type=CUSTOMER&name=patel%20trader&phone=098250-11001
→ { "has_exact_match": true,
    "candidates": [ { "id": 12, "name": "Patel Traders", "stage": "PROSPECT",
                      "match_reason": "exact_phone", "score": 0.95,
                      "phone": "+91 98250 11001", "city": "Rajkot" } ] }
```

Ranking: `exact_gst` (1.0) → `exact_phone` (0.95) → `similar_name` (pg_trgm similarity).
Phones are compared digits-only (last 10). Without the `pg_trgm` extension the name match
degrades to a containment search instead of failing.

**Merging** folds a duplicate into the survivor and keeps everything:

```http
POST /api/v1/parties/12/merge
{ "loser_id": 48, "note": "Same shop, entered twice during a phone enquiry." }
→ { "survivor_id": 12, "merged_party_id": 48,
    "moved": { "customer_inquiries": 1, "activities": 1, "notes": 1,
               "party_products_deduped": 1 } }
```

Inquiries, activities and notes are repointed; product and location links are repointed *and
de-duplicated* (they carry unique constraints, and a party may have only one primary location);
missing survivor details (phone, email, GST, contact) are filled in from the loser; the loser
becomes `stage=MERGED`, `status=INACTIVE`, `merged_into_id=<survivor>`, and is refused for new
inquiries and activities. One `MERGE` audit row records what moved. Admin only, same party type,
cannot merge a party into itself.

**Promotion** is deliberate: `POST /parties/{id}/promote` turns a prospect into a verified party
and is idempotent. Closing an inquiry does not change the party.

**Stale leads**: `GET /parties?stale_days=60` lists prospects older than 60 days with no inquiry
and no activity - the cleanup list.

## Inquiries

An inquiry is a **recorded quotation**: there is no request / response workflow and no
communication log. Status is either `ACTIVE` or `CLOSED`, and it is changed with the same `PATCH`
as any other field, in either direction.

| Method | Path | Notes |
|---|---|---|
| GET | `/inquiries` | `q`, `inquiry_type`, `status` (`ACTIVE`/`CLOSED`), `party_id`, `product_id`, `location_id` (any location on the inquiry), `area` (any location on the inquiry - for transport either end - is in this area), `material_id`, `grade_id`, `manufacturer_id`, `application_id` (through the inquiry's product; transport inquiries have no product and never match these), `created_from`, `created_to`, `sort_by=id\|created_at\|updated_at\|status\|closed_at` |
| POST | `/inquiries` | one entry point; the `inquiry_type` selects the detail block; optional top-level `status` |
| GET | `/inquiries/{id}` | the inquiry and its detail block |
| PATCH | `/inquiries/{id}` | any field: `status`, `party_id`, `product_id`, `quantity`, `unit`, `location_id`, `rate` (supplier / customer), `pickup_location_id`, `delivery_location_id`, `price` (transport) |

Supplier and customer inquiries carry a **rate in rupees per kilogram** and one location; transport
inquiries carry a **price in rupees** and a pickup and drop location. Locations are any active
Master Data location - they are never filtered by the party. A location that does not exist yet
is created with `POST /locations` and is then reusable everywhere.

Supplier quote:

```http
POST /api/v1/inquiries
{
  "inquiry_type": "SUPPLIER",
  "supplier": {
    "supplier_id": 31, "product_id": 5001, "quantity": "25", "unit": "MT",
    "location_id": 9, "rate": "90.80"
  }
}
```

Customer inquiry - the same fields:

```http
POST /api/v1/inquiries
{
  "inquiry_type": "CUSTOMER",
  "customer": {
    "customer_id": 12, "product_id": 5001, "quantity": "20",
    "location_id": 2, "rate": "92.50"
  }
}
```

Transport quote:

```http
POST /api/v1/inquiries
{
  "inquiry_type": "TRANSPORT",
  "transport": {
    "transporter_id": 41, "quantity": "20",
    "pickup_location_id": 9, "delivery_location_id": 2, "price": "18000"
  }
}
```

Close, reopen, or correct a rate:

```http
PATCH /api/v1/inquiries/1001
{ "status": "CLOSED" }

PATCH /api/v1/inquiries/1001
{ "status": "ACTIVE", "rate": "91.75" }
```

List rows carry `party_name`, `party_stage`, `product_name`, `quantity`, `unit`, and either
`location_name` + `rate` or `pickup_name` + `delivery_name` + `price`. Every change is written to
the audit log.

## Activities (any party)

| Method | Path | Notes |
|---|---|---|
| GET | `/activities` | `q`, `party_id` (`customer_id` is a deprecated alias), `activity_type`, `status` (repeatable), `assigned_salesperson_id`, `unassigned_only`, `scope=today\|upcoming\|overdue\|history`, `date_from`, `date_to`, `related_inquiry_id` |
| POST | `/activities` | `party_id` **or** `new_party`; `status=SCHEDULED` (default) or `COMPLETED` to log something already done; optional `assigned_salesperson_id`, and `location_id` / `new_location` / `location_text` |
| GET | `/activities/{id}` | includes `follow_ups`, the assignee, the reporter and the location |
| PATCH | `/activities/{id}` | reschedule, retype, edit the plan, reassign, change the location |
| POST | `/activities/{id}/assign` | **admin only**; `{ "assigned_salesperson_id": 7 }`, `null` hands it back to the desk |
| POST | `/activities/{id}/complete` | requires `outcome` (note) and optional `outcome_code`; optional `follow_up` creates the chained activity |
| GET | `/activities/salespeople/workload` | per-salesperson counts: today total/done/pending, upcoming, overdue |
| GET | `/activities/calendar` | `date_from`, `date_to`, optional `salesperson_id` - the scheduling calendar |
| GET | `/activities/conflicts/check` | `salesperson_id`, `scheduled_at`, optional `exclude_activity_id` - a **warning**, never a block |

Assign while creating:

```http
POST /api/v1/activities
{
  "customer_id": 12,
  "activity_type": "VISIT",
  "scheduled_at": "2026-10-04T11:00:00+05:30",
  "subject": "Visit ABC Pipes factory",
  "note": "Discuss the monthly PVC requirement. Ask about October.",
  "assigned_salesperson_id": 7,
  "location_id": 2
}
```

**Breaking change:** `activities.customer_id` is now `party_id`, and activities may hang off a
customer, a **supplier** or a **transporter** - a cold supplier call belongs on the supplier's
page. `customer_id` is still accepted in request bodies and as a list filter; responses return
`party_id` and `party`.

Rules: `assigned_salesperson_id` must be an **active `SALESPERSON`** account (`422` otherwise);
the party must not be `MERGED`; `VISIT` and `MEETING` need somewhere to go. For a visit, provide
one of:

| field | use |
|---|---|
| `location_id` | an address already on file |
| `new_location` | create it inline (`city` required); reusable afterwards |
| `location_text` | all you know is "his shop, Gondal Road" - stored as a snapshot, no location row |
| *(omitted)* | falls back to the party's primary location, or `422` if there is none |

The address is snapshotted onto the activity, so later edits to the location do not rewrite
history. The party of an activity can never be changed.

Conflict warning:

```http
GET /api/v1/activities/conflicts/check?salesperson_id=7&scheduled_at=2026-10-04T11:15:00%2B05:30
→ { "has_conflict": true,
    "conflicts": [ { "activity_id": 11, "activity_type": "VISIT",
                     "customer_name": "ABC Pipes",
                     "scheduled_at": "2026-10-04T11:00:00+00:00",
                     "minutes_apart": 15 } ] }
```

```http
POST /api/v1/activities/500/complete
{
  "outcome": "Customer expects requirement next week.",
  "follow_up": { "activity_type": "CALL", "scheduled_at": "2026-10-12T10:30:00Z",
                 "note": "Follow up on the PVC requirement." }
}
```

`scope` windows are evaluated in the business timezone
(`DISPLAY_TIMEZONE_OFFSET_MINUTES`, default +05:30).

## Salesperson (field) API

Only `SALESPERSON` accounts may call these, and every response is restricted to the
authenticated user's own assigned activities. The caller's id comes from the token: no endpoint
accepts a `salesperson_id`, a `customer_id` or an `assigned_salesperson_id` from the client.
An activity belonging to someone else returns **404**, so the API never reveals that it exists.

| Method | Path | Notes |
|---|---|---|
| GET | `/salesperson/me` | name, email, phone, role |
| GET | `/salesperson/dashboard` | one call for the home screen: profile, counts, today, overdue, next activity |
| GET | `/salesperson/activities/today` | today in the business timezone, ascending |
| GET | `/salesperson/activities/overdue` | still-open activities from before today |
| GET | `/salesperson/activities/upcoming` | `days` (default 30, max 90) |
| GET | `/salesperson/activities/history` | own completed/cancelled work, `limit` (max 200) |
| GET | `/salesperson/visits/today` | today's `VISIT` activities, each with a maps link |
| GET | `/salesperson/activities/{id}` | one own activity, restricted payload |
| POST | `/salesperson/activities/{id}/start` | `SCHEDULED` → `IN_PROGRESS`; repeating it is harmless |
| POST | `/salesperson/activities/{id}/complete` | outcome + note; **idempotent** |
| POST | `/salesperson/activities/{id}/follow-up` | creates the next activity for the same customer and the same field user |
| POST | `/salesperson/activities/{id}/location-fix` | `{latitude, longitude}` - pin the place they actually found |
| POST | `/salesperson/change-password` | `current_password`, `new_password` |

What an activity looks like to the field app — note what is *absent*: no ids to probe with, no
products, no inquiries, no GST, no party record:

```json
{
  "id": 1024,
  "activity_type": "VISIT",
  "status": "SCHEDULED",
  "subject": "Visit ABC Pipes factory",
  "scheduled_at": "2026-10-04T05:30:00Z",
  "purpose": "Discuss the monthly PVC requirement. Ask about October.",
  "completion_note": null,
  "outcome_code": null,
  "parent_activity_id": null,
  "is_visit": true,
  "can_complete": true,
  "customer": { "name": "ABC Pipes", "contact_person": "Jignesh Patel", "phone": "+91 98250 11001" },
  "location": {
    "label": "ABC Pipes Factory",
    "address_line_1": "Shapar Veraval GIDC",
    "city": "Rajkot", "state": "Gujarat", "pincode": "360024",
    "latitude": "22.1736", "longitude": "70.8697",
    "formatted": "ABC Pipes Factory, Shapar Veraval GIDC, Rajkot, Gujarat, 360024",
    "maps_url": "https://www.google.com/maps/dir/?api=1&travelmode=driving&destination=22.1736,70.8697"
  }
}
```

`maps_url` is built on the server: coordinates when the location has them, a URL-encoded address
otherwise (including a `location_text` address). The app only opens it.

**Location fix** — the person standing at the gate is the best source of coordinates:

```http
POST /api/v1/salesperson/activities/1024/location-fix
{ "latitude": "22.173600", "longitude": "70.869700" }
```

Coordinates that were **missing** on the location master are filled in. Existing coordinates are
never overwritten from the field: the correction lands on that activity's snapshot and in the
audit log for the desk to review. Visits only, own activities only.

Completion:

```http
POST /api/v1/salesperson/activities/1024/complete
{
  "outcome_code": "FOLLOW_UP_REQUIRED",
  "completion_note": "Customer wants a quotation for 30 MT.",
  "client_token": "1738-ab12cd"
}
→ { "activity": { … "status": "COMPLETED" … }, "already_completed": false }
```

`outcome_code` ∈ `COMPLETED | CUSTOMER_INTERESTED | CUSTOMER_NOT_INTERESTED |
FOLLOW_UP_REQUIRED | NO_RESPONSE | RESCHEDULED | OTHER`. The server records `status`,
`completed_at`, `completed_by`, `outcome_code` and the note. A repeat of the same completion by
the same user returns `already_completed: true` instead of `409`, which is what makes the app's
offline outbox safe to retry. Completing a cancelled activity returns `409`.

Follow-up — the client sends only what it is allowed to decide:

```http
POST /api/v1/salesperson/activities/1024/follow-up
{
  "activity_type": "CALL",
  "scheduled_at": "2026-10-10T16:00:00+05:30",
  "note": "Call about the October requirement."
}
```

The server derives `customer_id`, `assigned_salesperson_id` (always the caller) and
`parent_activity_id` from the completed activity; any such fields in the body are ignored.
Allowed types come from `SALESPERSON_FOLLOWUP_TYPES` (default `CALL,WHATSAPP,SMS,VISIT`);
anything else is `422`. The date must be in the future.

## Notes, search, dashboard, metadata, audit

| Method | Path | Notes |
|---|---|---|
| GET/POST | `/notes` | `q`, `party_id`, `party_type` |
| PATCH | `/notes/{id}` | |
| GET | `/search?q=` | parties, products, materials, grades, manufacturers (`limit` 1–25) |
| GET | `/dashboard` | counts + today's activities, follow-ups, recent and recently closed inquiries |
| GET | `/meta/enums` | every enum plus the state-machine and relationship rules |
| GET | `/audit-logs` | admin only; `entity_type`, `entity_id`, `user_id` |
| GET | `/health` | unauthenticated liveness check (outside `/api/v1`) |

## Validation rules enforced by the API

* A grade belongs to exactly one material; a product's grade must belong to its material.
* Product combinations (material + grade + manufacturer) are unique.
* Customer inquiries require a `CUSTOMER`, supplier inquiries a `SUPPLIER`, transport inquiries a
  `TRANSPORTER`; activities require a `CUSTOMER`.
* Quantities, rates and prices must be positive.
* Transport pickup and drop locations must differ.
* An inquiry `PATCH` refuses fields that belong to another inquiry type (a `rate` on a transport
  inquiry, a route on a supplier quote) and refuses to empty a required field.
* Inactive parties, products, grades, materials, manufacturers, applications and locations cannot
  be used for new business records; existing history keeps working.
* Suppliers may only `SUPPLIES`; customers `PURCHASES`/`INTERESTED_IN`; transporters have no
  product links. Party-product links are unique per relationship.
* Inquiry status is `ACTIVE` or `CLOSED`; closing stamps `closed_at` / `closed_by`, reopening clears them.
* Completed or cancelled activities reject edits and a second completion.
* Only an active `SALESPERSON` account can be assigned to an activity.
* `VISIT`/`MEETING` activities require a location; calls, WhatsApp and SMS do not.
* A salesperson can only act on activities assigned to them, can only move
  `SCHEDULED → IN_PROGRESS → COMPLETED`, and can only create a follow-up for themselves.
* A prospect from an inquiry form needs a name **and** a phone; an inline `new_party` on an
  activity needs at least one of them. Both are created as `PROSPECT`.
* A `MERGED` party cannot be used for a new inquiry or activity.
* Verified parties keep a unique name per type; prospects do not.
* A GST number stays globally unique, and a colliding GST on quick-create names the owner.
