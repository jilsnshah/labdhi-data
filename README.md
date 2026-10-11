# Trader CRM + Inquiry Management System

A production-shaped first version of the trading desk's single source of truth: master data,
parties (customers / suppliers / transporters), the inquiry lifecycle with sourcing and quote
history, customer activities, notes, and a 360° view of every relationship — **plus a
mobile-first field app (packaged as an Android APK) for salespeople who only execute the work
the desk assigns them**.

Two experiences, one backend and one database:

| | Admin / desk web app | Field app (APK) |
|---|---|---|
| Who | `ADMIN`, `USER` | `SALESPERSON` |
| Can | the whole CRM: parties, products, inquiries, activities, notes, assignment | only their own assigned activities |
| Cannot | — | browse customers, suppliers, transporters, products, inquiries, other people's work |
| Where | browser, desktop-first | phone, Capacitor WebView → `app-debug.apk` |

> **An admin assigns work. A salesperson executes that work.** The restriction is enforced in the
> API (role gates + ownership scoping), not by hiding screens — see
> [docs/PERMISSIONS.md](docs/PERMISSIONS.md) and
> [backend/tests/test_salesperson.py](backend/tests/test_salesperson.py).

Deliberately **not** included yet: purchases, sales, inventory, invoicing, accounting, transport
job execution. The database is designed so those can be added later without a redesign — see
[docs/ER_DIAGRAM.md](docs/ER_DIAGRAM.md#future-extension-points-designed-not-implemented).

**Stack:** FastAPI · SQLAlchemy 2 · PostgreSQL 16 · Alembic · Pydantic v2 · React · TypeScript ·
Vite · Mantine (admin) · TanStack Query · Capacitor 6 (Android). Modular monolith, no
microservices, no message bus, no Redis, no second database.

---

## 1. Quick start with Docker

```bash
cp .env.example .env            # adjust ports if 8000/5173/5433 are taken
docker compose up --build
```

> The `.env` committed with this checkout uses `BACKEND_PORT=8010` because port 8000 was already
> in use on the development machine; `frontend/.env` points at the same port. Change both back to
> 8000 if it is free for you.

* API: http://localhost:8000 · Swagger UI: http://localhost:8000/docs
* Admin web app: http://localhost:5173
* Field app (mobile web, the bundle that goes into the APK): http://localhost:5174
  — open it in a phone-sized browser window

Demo accounts:

| Role | Email | Password | Sees |
|---|---|---|---|
| Admin | `admin@tradercrm.in` | `admin123` | everything |
| Desk user | `ravi@tradercrm.in` | `ravi123` | the CRM, not user admin or audit logs |
| Salesperson | `rahul@tradercrm.in` | `rahul123` | 3 activities today (1 visit), 2 upcoming |
| Salesperson | `amit@tradercrm.in` | `amit123` | 1 visit today |

The backend container runs migrations and seeds demo data (`--if-empty`) before serving, and both
app containers bind-mount their source for live reload (drop the `volumes:` blocks in
`docker-compose.yml` for an immutable production image).

Reset the demo data at any time:

```bash
docker compose exec backend python -m app.seed      # truncates and reseeds
```

## 2. Local development

### Database

```bash
docker compose up -d db          # PostgreSQL on localhost:5433
```

### Backend

```bash
cd backend
python3 -m venv .venv            # Python 3.11+ (3.12/3.14 tested)
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head   # create the schema
.venv/bin/python -m app.seed     # realistic demo data (use --if-empty to keep existing data)
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### Admin frontend

```bash
cd frontend
npm install
cp .env.example .env             # point VITE_API_BASE_URL at the backend
npm run dev                      # http://localhost:5173
```

### Field app (web)

```bash
cd salesperson-web
npm install
cp .env.example .env             # VITE_API_BASE_URL is baked into the bundle
npm run dev                      # http://localhost:5174
```

### Field app (APK)

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17        # JDK 17
export ANDROID_HOME="$HOME/Library/Android/sdk"      # SDK platform 34 + build-tools 34
cd salesperson-web
npm run apk:debug    # → android/app/build/outputs/apk/debug/app-debug.apk
npm run apk:release  # signed when a keystore is configured, see docs/ANDROID.md
```

Full instructions, signing, icons, HTTPS and troubleshooting:
[docs/ANDROID.md](docs/ANDROID.md).

### Tests

```bash
cd backend
.venv/bin/python -m pytest       # 151 tests; creates/uses the trader_crm_test database
.venv/bin/python -m pytest tests/test_salesperson.py -q   # the authorization matrix (48)
.venv/bin/python -m pytest tests/test_prospects.py -q     # unknown parties, duplicates, merges (37)
.venv/bin/ruff check . && .venv/bin/ruff format --check app tests
```

```bash
cd frontend && npm run build          # admin: tsc -b + vite build
cd salesperson-web && npm run build   # field: tsc -b + vite build
```

Ports are configurable in `.env` (`POSTGRES_PORT`, `BACKEND_PORT`, `FRONTEND_PORT`). If the
backend does not run on 8000, set `VITE_API_BASE_URL` in `frontend/.env` to match.

---

## 3. What the system models

### Product identity

A tradable product is **material + grade + manufacturer**, each an independent entity with its own
id. Grades belong to a material, so an invalid pair cannot be created; the material + grade +
manufacturer combination is unique, so the same product cannot be entered twice. Applications
(PVC Pipes, PVC Windows, Profiles, …) attach many-to-many.

```
Material: PVC (id 1) ─┬─ Grade: K-67 (id 14, material_id 1)
                      └─ Manufacturer: Reliance (id 8)
                         → Product #5001 "Reliance PVC K-67"
                            Applications: PVC Pipes, PVC Windows, Profiles
```

Names are stored for display only — every relationship is a foreign key, and nothing important is
ever hard-deleted (master data is deactivated instead, so history stays valid).

### Unknown parties (walk-ins and cold calls)

An inquiry often arrives from somebody who is not in the system yet, and sometimes you need to
call a supplier whose name you only just heard. Both create a **real party in one step**, flagged
as a prospect, in the same transaction as the inquiry or activity:

```
New inquiry ▸ "New enquiry from someone new"
   Name   [ Patel Traders ]      Phone [ +91 99250 77001 ]
   City   [ Rajkot ]             GST   [ optional ]
   ⚠ Possible duplicates: Use "Patel Traders" (same phone · Rajkot · prospect)
```

* **Name or phone is enough.** A phone-only walk-in is listed by its number until somebody names it.
* It is created as `stage=PROSPECT` — fully usable, just not verified. `status` (active/inactive)
  stays a separate question.
* **Duplicates are caught at entry**: exact GST, exact phone (digits-only) or a similar name
  (trigram), with one tap to use the existing party instead. A warning, never a block — two
  different walk-ins may both be called "Patel Traders", so the unique-name rule applies to
  verified parties only.
* **Merge** folds a duplicate into the real party (admin only): inquiries, activities and notes
  move across, product and location links are de-duplicated, and the duplicate is retired as
  `MERGED` rather than deleted, so old links still resolve.
* **Promotion happens on evidence** — closing an inquiry as *Converted to deal* marks the prospect
  as known; `Parties ▸ Prospects` and `?stale_days=60` give you the cold list and the cleanup list.
* The field app cannot create parties at all, so none of this widens what a salesperson can reach.

### Parties and products

One `parties` table with a `party_type` enum, multiple locations per party
(head office / factory / warehouse / delivery point, one primary) and product links carrying a
relationship (`SUPPLIES`, `PURCHASES`, `INTERESTED_IN`). That link answers the two questions the
desk asks all day: *who can supply product X* and *which customers want product X*
(`GET /products/{id}/suppliers` and `/customers`).

### Inquiries

A common header (`inquiries`) plus a type-specific detail row, so customer, supplier and transport
inquiries share one lifecycle, one status machine and one response log:

```
Customer inquiry #1001  ABC Pipes · 20 MT Reliance PVC K-67 · required 10 Oct · target ₹91,000/MT
   ├── Supplier inquiry #1002  Mahavir Polymers  → QUOTE ₹92,000/MT, 40 MT, 2 days
   ├── Supplier inquiry #1003  Shakti Traders    → QUOTE ₹91,500/MT, 20 MT, 5 days
   ├── Supplier inquiry #1004  Oceanic Imports   → no response (WAITING)
   └── Transport inquiry #1005 Jay Transport     → QUOTE ₹18,000 Ahmedabad → Rajkot
Closed: PRICE_TOO_HIGH — "Customer required ₹91,000/MT, best was ₹91,500/MT. Declined."
```

Responses are **append-only** — a new quote never overwrites the previous one, so sourcing history
survives. Closing requires a *structured reason* **and** a free-text note; the database enforces
it with a check constraint, and the valid reasons differ per inquiry type.

### Activities, assignment and field execution

Activities hang off **any** party — customers mostly, but a cold supplier call or a transporter
meeting is real work and belongs on that party's page: `CALL`, `WHATSAPP`, `SMS`, `VISIT` (plus
`EMAIL`/`MEETING` headroom). A scheduled activity is just an activity with `status=SCHEDULED` and a future
`scheduled_at` — there is no separate table. An activity can be **assigned to a salesperson**
(`assigned_salesperson_id`, which must be an active `SALESPERSON` account); visits also carry a
`location_id` plus a snapshot of that address, so history stays accurate when the customer later
moves. A follow-up is a **new** activity pointing at its parent, which builds a chain:

```
Activity #500 CALL COMPLETED  note: "why scheduled"  outcome: "what happened"
   └── Activity #501 CALL SCHEDULED (parent_activity_id = 500)
```

`note` (plan) and `outcome` (result) are separate fields on purpose, and a completion also records
a structured `outcome_code` (`FOLLOW_UP_REQUIRED`, `CUSTOMER_INTERESTED`, …) plus `completed_by`.
WhatsApp/SMS are activity types today; the columns a real integration needs
(`external_message_id`, `delivery_status`, `read_status`) already exist and are nullable.

The field user's whole world is those assignments:

```
Admin                         Field app (phone)
─────                         ─────────────────
assign VISIT, 11:00,          Today ▸ 11:00 VISIT ABC Pipes ▸ [Navigate] → Google Maps
ABC Pipes factory,            ▸ Start ▸ Complete: outcome + "Customer wants 30 MT quote"
purpose + location            ▸ optional follow-up → CALL, 7 Oct, still assigned to them
see completion, outcome,
reporter and follow-up
```

Notes are a separate entity for business context ("customer is expanding a second factory"), kept
strictly apart from `audit_logs`, which records system changes (`OPEN → CLOSED`,
`ACTIVE → INACTIVE`) and is admin-only.

---

## 4. Using the app

### Admin web app

```
Dashboard                        open inquiries by type, today's activities, overdue follow-ups,
                                 field-team workload, recent and recently closed inquiries
Master Data  Products, Materials, Grades, Manufacturers, Applications, Locations
Parties      Customers, Suppliers, Transporters → 360° page per party
Inquiries    Customer, Supplier, Transport → inquiry detail with sourcing and timeline
Activities   Today, Upcoming, History, Calendar, Salespeople
Notes
Settings     profile, users (incl. salesperson accounts), audit log
```

* **⌘K / Ctrl+K** opens global search across parties, products, materials, grades and
  manufacturers (searching `K-67` finds the grade and its products; `Reliance` finds the
  manufacturer and its products; `ABC` finds the party).
* Every picker (customer, supplier, transporter, product, material, grade, manufacturer, location)
  is a server-backed autocomplete — the browser never loads whole tables.
* Grade dropdowns are filtered by the selected material; inactive master data is not offered for
  new records.
* The customer inquiry page has **Ask supplier** and **Arrange transport** buttons that pre-fill
  product, quantity, unit and date from the customer requirement.
* The activity form picks the party type (customer / supplier / transporter), creates an unknown
  party inline, assigns a salesperson, and warns (without blocking) when that person is already
  booked within an hour.
* A visit needs somewhere to go, but "just describe it" is a valid answer: *known address*,
  *new address* or free text like "his shop on Gondal Road". The field user can then pin the real
  coordinates on arrival, which fills in what the address master was missing.
* **Activities ▸ Calendar** shows a day or week per salesperson; **Activities ▸ Salespeople**
  shows each person's load and their today / upcoming / completed lists.
* Clicking any activity row opens the full record: assignment, brief, completion outcome, who
  reported it, and the follow-up chain.

### Field app

```
Today      greeting, counts, overdue, then Morning / Afternoon / Evening cards
Visits     today's stops in order, each with [Navigate] (Google Maps) and [View]
Upcoming   the next 30 days, grouped by day
Profile    account, completed history, change password, log out
Pin        on a visit: "I'm here - save this spot" writes coordinates back for the office
Activity   customer + contact + address + purpose → Start → Complete → Follow-up
```

Everything is one or two taps: open the app, see the day, tap a visit, navigate, complete it with
an outcome, optionally schedule the follow-up. Reports are written to an on-device outbox before
the network call, so a dead signal in a factory yard cannot lose a visit report; the completion
endpoint is idempotent, so retries are safe.

### Typical flow

1. **Masters** — create material → grade → manufacturer → application → product, assign
   applications.
2. **Parties** — create customer/supplier, add locations, link products.
3. **Record a quote** — supplier, customer or transport inquiry: pick the party (or add an
   unknown one with just a name and phone - it is saved as a prospect), the product, quantity,
   location (pick any, or add a new one without leaving the form) and the rate in ₹/kg. Transport
   quotes take pickup, drop and a ₹ price instead.
4. **Keep it current** — edit any field from the inquiry page; status is simply *Active* or
   *Closed* and can be switched either way.
5. **Compare** — the inquiry lists show every party's rate side by side, filterable by status,
   party, product and date.
6. **Stay in touch** — schedule a call, complete it with an outcome, and let it create the next
   follow-up.

---

## 5. Demo scenario (seeded)

Sign in to the admin app as `admin@tradercrm.in`, open **Activities ▸ Salespeople**: Rahul has
three activities today (a visit to ABC Pipes at 11:00, a call at 15:00, a WhatsApp at 17:00) and
Amit has one visit at 12:00.

Now open the field app at http://localhost:5174 as `rahul@tradercrm.in / rahul123`:

* he sees **only his own** three activities — not Amit's visit, no customer list, no supplier,
  product or inquiry data (the API answers `403` for all of it);
* the ABC Pipes visit shows the factory address and a **Navigate** button that opens Google Maps
  on the stored coordinates;
* completing it with an outcome and a note immediately shows up for the admin — status, outcome
  code, reporter, note — and a follow-up he schedules stays assigned to him and appears in the
  admin's calendar.

## 6. Project layout

```
backend/
  app/
    main.py                FastAPI app, error handling, router wiring
    core/                  settings, security (bcrypt + JWT), dependencies, errors, pagination
    db/                    declarative base, engine/session
    models/                SQLAlchemy 2 models (masters, party, inquiry, activity, note, audit)
    schemas/               Pydantic v2 request/response schemas
    services/              business logic: validation, state machines, audit, queries, 360 view
    api/v1/                REST routers (thin; no business logic)
    seed.py                realistic demo data covering the whole workflow
  alembic/versions/        migrations (0001_initial_schema)
  tests/                   61 pytest tests incl. end-to-end workflows A–G
frontend/                  ADMIN web app (desktop-first)
  src/
    api/                   typed client + TanStack Query hooks
    components/            DataTable, EntitySelect, timelines, shared tables, modals
    layout/                app shell, navigation, global search
    pages/                 dashboard, masters, parties (360°), inquiries, activities
                           (incl. calendar + salespeople), notes, settings
    lib/                   auth context, formatting helpers
salesperson-web/           FIELD app (mobile-first, packaged as the APK)
  src/
    api/                   narrow client + hooks for /salesperson/*
    components/            Screen/Sheet shell, bottom nav, activity card
    lib/                   secure token storage, offline outbox, Capacitor bridge
    pages/                 today, visits, upcoming, history, activity detail, profile
  android/                 Capacitor 6 shell (manifest, icons, splash, signing config)
  resources/               icon + splash source art
docs/
  ARCHITECTURE.md          two-app architecture, request flow, offline strategy, push hooks
  PERMISSIONS.md           the authorization matrix and where each rule is enforced
  ER_DIAGRAM.md            schema, constraints, indexes, state machines, extension points
  API.md                   endpoint reference incl. the salesperson API
  ANDROID.md               APK build, signing, HTTPS, troubleshooting
docker-compose.yml         db + backend + admin web + field web
.env.example
```

Layering: routers validate and shape payloads, services own business rules, models own
persistence. One transaction per request, committed by `UnitOfWorkMiddleware`
(`app/db/session.py`) **before the response is sent** — committing in a `yield` dependency happens
after the response and let a client read its own write as missing. A rejected request rolls back
completely, so a failed inquiry leaves no half-created party behind.

## 7. Configuration

All configuration comes from the environment (see [.env.example](.env.example)):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` / `TEST_DATABASE_URL` | PostgreSQL connections (psycopg 3 driver) |
| `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | token signing — **replace the key in production** |
| `CORS_ORIGINS` | comma-separated allowed origins |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` / `SEED_ADMIN_NAME` | seeded admin account |
| `DISPLAY_TIMEZONE_OFFSET_MINUTES` | business day boundary for "today"/"upcoming" (330 = IST) |
| `SALESPERSON_FOLLOWUP_TYPES` | activity types a field user may schedule (default `CALL,WHATSAPP,SMS,VISIT`) |
| `CORS_ORIGINS` | includes `:5174` and the APK's `https://localhost` / `capacitor://localhost` origins |
| `SCHEDULE_CONFLICT_WINDOW_MINUTES` | window used for the double-booking warning (default 60) |
| `POSTGRES_PORT`, `BACKEND_PORT`, `FRONTEND_PORT` | host ports used by Docker Compose |
| `VITE_API_BASE_URL` | API base URL used by both frontends (baked into the field bundle at build time) |
| `SALESPERSON_PORT` | host port for the field app dev server (5174) |

Authentication is JWT bearer with bcrypt password hashing and three roles (`ADMIN`, `USER`,
`SALESPERSON`). User administration, the audit log and activity assignment are admin-restricted;
all CRM endpoints refuse `SALESPERSON`; `/salesperson/*` refuses desk accounts and is scoped to
the caller. Timestamps are stored in UTC.

## 8. Verified workflows

`backend/tests/test_workflows.py` covers the critical paths end to end, and the full suite also
covers the validation and state-machine rules listed in [docs/API.md](docs/API.md):

| Workflow | Test |
|---|---|
| A — material → grade → manufacturer → application → product → applications | `test_workflow_a_add_product` |
| B/C — create supplier and customer, add location, associate products | `test_workflow_b_and_c_add_supplier_and_customer` |
| D/E — customer inquiry → ask three suppliers → compare responses → close | `test_workflow_d_e_customer_inquiry_sourced_and_closed` |
| F — transport inquiry → response → close | `test_workflow_f_transport_inquiry` |
| G — schedule call → complete with outcome → chained follow-up | `test_workflow_g_customer_activity_chain` |
| Field — admin assigns a visit → salesperson sees only their own work → start → complete → follow-up → admin sees it all | `tests/test_salesperson.py` (48 tests, incl. the full authorization matrix) |
| Unknown party — inquiry/activity from a walk-in → prospect created inline → duplicate warned → merged → promoted on conversion | `tests/test_prospects.py` (33 tests) |

```bash
cd backend && .venv/bin/python -m pytest -q
```

## 9. Known limitations

* Dates for inquiries are plain dates (no time-of-day); activity scheduling is timestamped.
* Roles are coarse (`ADMIN` / `USER` / `SALESPERSON`) — per-entity permissions are intentionally
  not built yet.
* The admin bundle is a single chunk; code-splitting can wait until the trading module lands.
  The field bundle is deliberately small (≈253 kB, 82 kB gzipped).
* `deals` in the 360° payload is always empty — it is the documented hook for purchases, sales,
  inventory lots and transport jobs.
* The field app tolerates bad networks (outbox + idempotent completion + cached schedule) but is
  not a full offline-first sync engine, and there is no "request reschedule" action yet — both
  were explicitly out of scope.
* Push notifications are designed for but not implemented; the extension point is described in
  [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
* A merge cannot be undone from the UI (the audit row records what moved, so it can be unpicked
  by hand). Field users still cannot capture prospects themselves — that would need the
  admin-approved submission queue sketched in the architecture doc.
* The release APK is unsigned unless you configure a keystore (no keystore is committed).
