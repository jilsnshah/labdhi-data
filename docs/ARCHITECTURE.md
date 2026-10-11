# Architecture

One backend, one database, two frontends — and an APK that wraps the second one.

```
                          PostgreSQL 16
                                ▲
                                │ SQLAlchemy 2 / Alembic
                                │
                           FastAPI API
                   (role gates + ownership scoping)
                 ┌──────────────┴───────────────┐
      /api/v1/...│                              │/api/v1/salesperson/...
   staff only    │                              │ field only
                 ▼                              ▼
        Admin web app                   Field (salesperson) web app
   React 19 · Mantine · desktop     React 18 · hand-rolled CSS · mobile-first
                 │                              │
                 ▼                              ▼
          browser (5173)                Capacitor 6 Android shell
                                                │
                                                ▼
                                           app-debug.apk
```

There is **no second database and no second service**. The field app is a
different *view* with a different *authorisation surface*, not a different system.

## Why two frontends instead of one app with role routing

The field bundle is 253 kB (82 kB gzipped) with no component library, because it
ships inside an APK and runs on a phone in a factory yard. The admin bundle is
dense, desktop-first and pulls in Mantine. Sharing one bundle would mean either
shipping the whole CRM to the phone or carving the admin app into lazy chunks for
little gain. They share what matters — the API contract, the business rules and
the database — and nothing that would let field code drift into CRM code.

## Request flow for a field request

```
APK WebView
  → GET /api/v1/salesperson/activities/today   (Authorization: Bearer <jwt>)
      → get_current_user()     decode JWT, load user, reject inactive
      → require_salesperson()  reject ADMIN / USER
      → service.today_activities(session, user)
             SELECT ... FROM activities
              WHERE assigned_salesperson_id = :current_user_id   ← from the token
                AND scheduled_at >= :business_day_start
      → SalespersonActivity DTO: name / contact / phone / address / maps_url
```

The scope predicate is attached inside the service, so an endpoint cannot
accidentally forget it: there is no "list activities" query in the field service
that is not already filtered by owner. A foreign id returns `404`, never `403`,
so the API does not confirm that somebody else's activity exists.

## Status model

```
Admin                                   Field user
─────                                   ──────────
create activity (SCHEDULED)
  + assign salesperson
  + location (required for VISIT)
                                        start      → IN_PROGRESS
                                        complete   → COMPLETED
                                                     + outcome_code
                                                     + completion note
                                                     + completed_by
                                        follow-up  → new SCHEDULED activity
                                                     parent_activity_id = previous
                                                     same customer, same assignee
reschedule / reassign / cancel
```

The field user can make exactly two status moves (`start`, `complete`) and create
exactly one kind of record (a follow-up for themselves). Rescheduling and
cancelling stay with the desk, by design (specification §28).

## Visit locations and history

An activity references `locations.id` **and** stores a `location_snapshot`
(JSONB) captured when it was created. The reference keeps the data normalised;
the snapshot means that renaming or moving a customer's warehouse next year does
not rewrite where somebody actually went last October. The field DTO renders the
snapshot, falling back to the live row if a legacy activity has none.

Navigation links are built on the server (`maps_url`): coordinates when the
location has them, a URL-encoded address otherwise. The app only has to open the
link, which Capacitor hands to the Google Maps app through an Android intent.

## Offline tolerance (not an offline-first engine)

A visit report must survive a dead signal in a factory:

1. The completion (with its optional follow-up) is written to an **outbox** in
   local storage *before* any network call —
   [salesperson-web/src/lib/offline.ts](../salesperson-web/src/lib/offline.ts).
2. The outbox is flushed immediately, then again on `networkStatusChange`, on app
   resume and on demand from the Profile screen.
3. `POST /salesperson/activities/{id}/complete` is **idempotent**: a repeat from
   the same salesperson returns `already_completed: true` instead of a conflict,
   so retries are safe.
4. A server-side rejection (for example, the office cancelled the activity) drops
   the queued item instead of blocking the queue forever; the user then sees the
   real state.
5. React Query keeps the last fetched schedule for an hour (`gcTime`), so the app
   still opens and shows the day with no connection.

What this is *not*: there is no bidirectional sync engine, no local database and
no conflict resolution UI. That was deliberate (specification §29).

## Session persistence

The JWT is stored through Capacitor Preferences, i.e. the app's private
`SharedPreferences` on Android — not the WebView's `localStorage`, and not
readable by other apps. On the web (dev or browser preview) it falls back to
`localStorage`. Everything goes through four functions in
[salesperson-web/src/lib/storage.ts](../salesperson-web/src/lib/storage.ts), so
swapping in `EncryptedSharedPreferences` later is a one-file change.

Session restore is network-tolerant: a `401` clears the token, but a network
error keeps it, so a field user who opens the app underground is not logged out.

## Push notifications (extension point, not implemented)

The data model already carries everything a notification needs:
`assigned_salesperson_id`, `scheduled_at`, `status`, and audit rows for
`ASSIGN` / `STATUS_CHANGE` / `COMPLETE`. To add FCM later:

1. Add `device_tokens(id, user_id, token, platform, created_at, last_seen_at)`.
2. Register the token after login from the app (`@capacitor/push-notifications`).
3. Emit on the events the desk already writes: assignment created or changed,
   activity cancelled, follow-up scheduled, plus a scheduled "visit at 11:00"
   reminder job reading `activities` by `scheduled_at`.

No existing table or endpoint has to change.

## One transaction per request, committed before the response

A FastAPI `yield` dependency runs its exit code *after* the response has been
sent, so committing there is observably racy: a client could read `201 Created`,
immediately `GET` the new record and be told it does not exist. The field app
does exactly that (write, then refresh), and it was reproducible.

`UnitOfWorkMiddleware` ([backend/app/db/session.py](../backend/app/db/session.py))
therefore owns the transaction: the session is parked on `request.state`, the
middleware commits on a 2xx/3xx, rolls back on a 4xx/5xx or an unhandled
exception, and the dependency only has to return the connection to the pool.
Writes are visible to the client's very next request, and a rejected request
leaves nothing behind - including the party a quick-create would have made.

## Unknown parties

A walk-in, or a supplier somebody mentioned in a broker group, becomes a **real `parties` row**
flagged `stage=PROSPECT`. From an inquiry form it is saved first from just a name and phone
(`POST /parties/prospects`) and then selected; from an activity it can be created inline in the
same transaction. Deliberately *not* a separate `leads` table: every FK in the system already
points at `parties.id`, so a prospect gets the 360° page, the activity chain and search for free -
and no table needs a nullable `lead_id` or a conversion step that rewrites history.

The price of letting anyone create parties is duplicates, so three things come with it:

1. **Detect at entry** - `GET /parties/duplicates` ranks exact GST, exact normalised phone and
   trigram name similarity. The inline form calls it as the trader types and offers "use this one
   instead".
2. **Merge afterwards** - `POST /parties/{id}/merge` repoints all history, de-duplicates the link
   tables, retires the loser as `MERGED` (never deletes it) and writes one audit row.
3. **Promote deliberately** - `POST /parties/{id}/promote` verifies a prospect from its page.

Name uniqueness is relaxed for prospects only (partial unique index), because blocking "Patel
Traders" at the moment a second Patel Traders walks in is worse than carrying a duplicate you can
merge later.

## Timezone handling

Everything is stored in UTC. "Today", "upcoming" and "overdue" are evaluated in
the business timezone (`DISPLAY_TIMEZONE_OFFSET_MINUTES`, default +05:30), so a
10 PM IST query does not roll the day over. The phone renders times in its own
locale.

## Module map

```
backend/app
  core/deps.py            CurrentUser / StaffUser / AdminUser / SalespersonUser
  api/v1/__init__.py      CRM routers mounted behind require_staff
  api/v1/salesperson.py   the entire field API surface (11 endpoints)
  services/salesperson.py ownership scoping, DTOs, maps links, idempotent completion
  services/activities.py  assignment validation, location snapshots, conflicts, workload
  models/activity.py      assigned_salesperson_id, completed_by, outcome_code, location_snapshot

frontend/src              admin: assignment UI, calendar, salespeople workload, activity drawer
salesperson-web/src       field: today, visits, upcoming, history, activity, profile
salesperson-web/android   Capacitor shell → APK
```
