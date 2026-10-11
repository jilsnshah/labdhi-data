# Permission matrix

Two very different experiences share one API and one database:

* **ADMIN / USER (desk)** own the CRM.
* **SALESPERSON (field)** owns only the execution of the activities assigned to them.

Everything below is enforced **server-side**. Hiding routes in a frontend is never the control.

## Enforcement points

| Layer | File | What it does |
|---|---|---|
| Role gate (staff) | [backend/app/core/deps.py](../backend/app/core/deps.py) | `require_staff` rejects `SALESPERSON` on every CRM router |
| Router default | [backend/app/api/v1/__init__.py](../backend/app/api/v1/__init__.py) | CRM routers are included with `dependencies=[Depends(require_staff)]`, so a newly added endpoint is closed to field accounts by default |
| Role gate (field) | [backend/app/core/deps.py](../backend/app/core/deps.py) | `require_salesperson` rejects desk accounts on `/salesperson/*` |
| Ownership scope | [backend/app/services/salesperson.py](../backend/app/services/salesperson.py) | every query filters `assigned_salesperson_id == current_user.id`; a foreign activity returns **404**, not 403, so the API never confirms it exists |
| Admin-only | `require_admin` | user administration, audit log, `POST /activities/{id}/assign` |
| Assignment validity | [backend/app/services/activities.py](../backend/app/services/activities.py) | `resolve_salesperson` refuses non-`SALESPERSON` and inactive accounts |
| Narrow DTOs | [backend/app/schemas/salesperson.py](../backend/app/schemas/salesperson.py) | the field app receives `{name, contact_person, phone}` for the customer and an address - no ids, no products, no inquiries |

The salesperson id is taken from the JWT subject. No endpoint accepts a
`salesperson_id` (or `customer_id`, or `assigned_salesperson_id`) from the client
as an authority: `POST /salesperson/activities/{id}/follow-up` derives the
customer, the assignee and the parent from the completed activity.

## Matrix

| Action | ADMIN | USER (desk) | SALESPERSON |
|---|:--:|:--:|:--:|
| View all customers / suppliers / transporters | yes | yes | **no** (403) |
| View assigned customer details | yes | yes | **limited**: name, contact person, phone, visit address |
| Create / edit / deactivate a party | yes | yes | **no** |
| View products, materials, grades, manufacturers, applications | yes | yes | **no** |
| View / create / edit inquiries | yes | yes | **no** |
| View locations master | yes | yes | **no** (only the address of their own activity) |
| Create an activity (for any party type) | yes | yes | **no** |
| Create an unknown party inline from an inquiry/activity (`new_*` → `PROSPECT`) | yes | yes | **no** |
| Check for duplicate parties | yes | yes | **no** |
| Promote `PROSPECT` → `ACTIVE` | yes | yes | **no** |
| Merge a duplicate party | yes | **no** | **no** |
| Assign / reassign an activity | yes | **no** (admin only) | **no** |
| View all activities | yes | yes | **no** |
| View own assigned activities | yes | yes | **yes** |
| Start own activity | yes | yes | **yes** |
| Complete own activity | yes | yes | **yes** |
| Complete another person's activity | yes | yes | **no** (404) |
| Create a follow-up on own activity | yes | yes | **yes** (stays with them) |
| Assign a follow-up to somebody else | yes | **no** | **no** |
| Change the customer on an activity | **no** (immutable by design) | no | no |
| Reschedule / cancel an activity | yes | yes | **no** |
| View today's visits with navigation | yes | yes | **yes - own only** |
| Open Google Maps | yes | yes | **yes** |
| Manage salespeople (create / deactivate) | yes | **no** | **no** |
| Pin coordinates on their own visit | yes | yes | **yes** (`/salesperson/activities/{id}/location-fix`, visits only, never overwrites existing coordinates) |
| Change own password | yes | yes | **yes** (`/salesperson/change-password`) |
| View audit logs | yes | **no** | **no** |
| Search (global CRM search) | yes | yes | **no** |

`USER` is the existing desk role: full CRM access, but user administration,
audit logs and activity assignment stay with `ADMIN`.

## Tests

The matrix is a test suite, not a promise:
[backend/tests/test_salesperson.py](../backend/tests/test_salesperson.py) (48 tests) and
[backend/tests/test_prospects.py](../backend/tests/test_prospects.py) (37 tests covering unknown
parties, duplicates and merges, including the field-role boundary).

| Requirement | Test |
|---|---|
| Salesperson cannot list customers, suppliers, transporters, products, inquiries, notes, activities, audit logs, users, search | `test_salesperson_cannot_reach_any_crm_endpoint` (parametrised over 16 endpoints) |
| Salesperson cannot read one customer or its 360 view | `test_salesperson_cannot_read_a_customer_record_directly` |
| Salesperson cannot write any CRM object | `test_salesperson_cannot_write_crm_data` |
| Salesperson cannot view another salesperson's activity | `test_salesperson_cannot_open_another_persons_activity` |
| Salesperson cannot complete another salesperson's activity | `test_salesperson_cannot_complete_another_persons_activity` |
| Id probing returns 404 | `test_salesperson_cannot_probe_unknown_ids` |
| Payload exposes nothing extra | `test_activity_payload_exposes_only_what_is_needed` |
| Salesperson can complete own activity | `test_salesperson_can_complete_own_activity` |
| Completion is retry-safe | `test_completion_is_idempotent_for_retries` |
| Salesperson can schedule a follow-up | `test_follow_up_inherits_customer_assignee_and_parent` |
| Follow-up cannot be reassigned or moved to another customer | `test_follow_up_ignores_any_attempt_to_reassign_or_change_customer` |
| Follow-up types are restricted | `test_follow_up_type_is_restricted` |
| Salesperson cannot patch or assign activities | `test_salesperson_cannot_patch_or_assign_activities` |
| Salesperson can see own visits with a maps link | `test_visit_carries_a_google_maps_link`, `test_maps_link_falls_back_to_the_address` |
| Salesperson cannot create, promote or merge parties, including through the inline `new_party` field | `test_salesperson_cannot_create_or_merge_parties` (test_prospects.py) |
| Salesperson can pin only their own visit | `test_salesperson_can_pin_the_place_they_found` (test_prospects.py) |
| Desk accounts are refused by the field API | `test_salesperson_endpoints_reject_staff_accounts` |
| Admin can assign and reassign | `test_admin_can_assign_and_reassign` |
| Only salesperson accounts can be assigned | `test_only_salesperson_accounts_can_be_assigned`, `test_inactive_salesperson_cannot_be_assigned` |
| Admin sees the completion | `test_salesperson_can_complete_own_activity` (admin assertion) |
| Admin sees workload and conflicts | `test_workload_and_conflict_warning`, `test_admin_sees_assignment_in_the_calendar` |

Run them:

```bash
cd backend && .venv/bin/python -m pytest tests/test_salesperson.py -q
```
