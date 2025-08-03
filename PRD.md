PRD — RPC-over-HTTP API Stack (FastAPI server, TS client, Dev Console)

0. Summary

Build a POST-only RPC API with FastAPI, a TypeScript client SDK, and a dev-centric web app to compose calls, inspect requests/responses, and visualize traces.
Domain: Seat-limited tour bookings with time-bound reservation holds, waitlists, inventory adjustments, and concurrency guarantees.

⸻

1. Goals & Non-Goals

Goals
	•	Contract-first OpenAPI with explicit RPC methods (/v1/{service}/{method}).
	•	Strong typing (Pydantic v2 / TS types), Problem Details errors, idempotency, pagination, and tracing.
	•	TS client usable inside an “old, complicated” Node app (zero-magic, fetch-based).
	•	Dev console for engineers: build requests, run flows, view headers/bodies, and trace links.

Non-Goals
	•	Public checkout/payments.
	•	Multi-tenant billing.
	•	Complex auth providers (use simple Bearer token).

⸻

2. Personas
	•	API Producer: Backend team owning FastAPI service.
	•	API Consumer: Node service calling the API via TS client.
	•	QA/Developer: Uses Dev Console to script and debug flows.

⸻

3. Domain Overview: Tours & Bookings
	•	Tour: A named trip with scheduled Departures (date/time, capacity).
	•	Hold: Temporary reservation for N seats with TTL (default 10 minutes). Expired holds auto-release capacity.
	•	Booking: Confirmed seats derived from a valid hold.
	•	Waitlist: If capacity is full, users can join a per-departure queue.
	•	Inventory Adjustment: Admin operation to increase/decrease capacity (e.g., bus swap).
	•	Concurrency Rules:
	•	Capacity decremented on hold creation, restored on expiry/cancel.
	•	Idempotency-Key required on mutating calls to prevent double-booking.
	•	Single-departure serialized operations (advisory locks) to avoid races.

⸻

4. System Architecture
	•	FastAPI app (async):
	•	DB: Postgres (async SQLAlchemy 2.x) + Alembic migrations.
	•	Background worker (async task runner) for hold expiry sweeps.
	•	Observability: OpenTelemetry (W3C trace context), structured logs.
	•	OpenAPI: Single source of truth (committed in repo); generated docs + examples; Spectral lint; oas-diff gate.
	•	TS Client SDK: openapi-typescript for types + thin fetch wrapper (undici compatible). No runtime framework lock-in.
	•	Dev Console Web App: Next.js + React + Tailwind + shadcn/ui.
	•	Features: request builder, schema-driven forms, environment switcher, run history, cURL/HTTP view, trace links.

⸻

5. API Style (RPC over HTTP)
	•	Routes: POST /v1/{service}/{method}
Examples: /v1/tour/create, /v1/departure/search, /v1/booking/hold, /v1/booking/confirm.
	•	Auth: Authorization: Bearer <token>.
	•	Idempotency: Idempotency-Key header on mutating methods (hold, confirm, cancel, adjust). Server must dedupe by (key + method + normalized body hash) within TTL (24h).
	•	Errors: RFC 9457 Problem Details (plus code, retryable, trace_id, violations[] for validation).
	•	Pagination: Cursor-based (cursor, limit, next_cursor).
	•	Timestamps: ISO-8601 UTC (Z).
	•	Money: Minor units (amount int, currency ISO-4217).
	•	Versioning: /v1 path; additive only; deprecations logged and announced.

⸻

6. Primary Methods (initial surface)

Service/Method	Purpose	Idempotent?	Notes
tour/create	Create a tour	✔ (by name+slug)	Admin
departure/create	Create a departure w/ capacity	✔	Admin
departure/search	Filter by tour/date/availability	n/a	Read
booking/hold	Create/refresh a seat hold (TTL)	✔	Requires Idempotency-Key
booking/confirm	Convert hold → booking	✔	Requires Idempotency-Key
booking/cancel	Cancel booking & free seats	✔	Requires Idempotency-Key
booking/get	Fetch booking by id	n/a	Read
waitlist/join	Join waitlist if full	✔	Dedup by user+departure
waitlist/notify	Internal: pop waitlist → issue hold	✔	Admin/worker
inventory/adjust	Adjust capacity (±)	✔	Admin; records audit
health/ping	Health check	n/a	Read


⸻

7. Data Models (excerpt)

// Money
{ "amount": 12999, "currency": "USD" } 

// Problem (error)
{
  "type": "https://docs.example.com/errors/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "Hold already exists",
  "instance": "/v1/booking/hold",
  "code": "HOLD_CONFLICT",
  "retryable": false,
  "trace_id": "c0ffee...",
  "violations": [{"path": "/seats", "message": "must be >=1"}]
}

Entities
	•	Tour { id, name, slug, description }
	•	Departure { id, tour_id, starts_at, capacity_total, capacity_available, price: Money }
	•	Hold { id, departure_id, seats, customer_ref, expires_at, status: (ACTIVE|EXPIRED|CONFIRMED|CANCELED), idem_key }
	•	Booking { id, hold_id, code, seats, customer_ref, status: (CONFIRMED|CANCELED), created_at }
	•	WaitlistEntry { id, departure_id, customer_ref, created_at, notified_at? }
	•	InventoryAdjustment { id, departure_id, delta, reason, created_at, actor }

⸻

8. Example Flows

A. Create tour and departure
	1.	POST /v1/tour/create → returns tour.id.
	2.	POST /v1/departure/create with capacity_total=40, starts_at=....

B. Hold → Confirm booking
	1.	POST /v1/booking/hold (Idempotency-Key: K1) → hold.id, expires_at.
	2.	POST /v1/booking/confirm (Idempotency-Key: K2, hold_id) → booking.id, code.
	•	Replays of K2 return same booking.

C. Full capacity
	•	booking/hold returns 409 with code="FULL"; client calls waitlist/join.

D. TTL expiry
	•	Worker expires holds after expires_at; capacity restored. If waitlist present, waitlist/notify may auto-issue a short hold for next in line.

⸻

9. Representative Schemas (OpenAPI excerpt-level)

components:
  schemas:
    Money:
      type: object
      required: [amount, currency]
      properties:
        amount: { type: integer, minimum: 0 }
        currency: { type: string, minLength: 3, maxLength: 3 }
    Problem:
      type: object
      required: [title, status]
      properties:
        type: { type: string, format: uri }
        title: { type: string }
        status: { type: integer }
        detail: { type: string }
        instance: { type: string }
        code: { type: string }
        retryable: { type: boolean }
        trace_id: { type: string }
        violations:
          type: array
          items:
            type: object
            properties:
              path: { type: string }
              message: { type: string }

booking/hold request

type: object
required: [departure_id, seats, customer_ref]
properties:
  departure_id: { type: string }
  seats: { type: integer, minimum: 1, maximum: 10 }
  customer_ref: { type: string, maxLength: 128 }
  ttl_seconds: { type: integer, minimum: 60, maximum: 3600, default: 600 }

booking/hold response

type: object
required: [id, expires_at, seats, departure_id, status]
properties:
  id: { type: string }
  departure_id: { type: string }
  seats: { type: integer }
  status: { type: string, enum: [ACTIVE, EXPIRED, CONFIRMED, CANCELED] }
  expires_at: { type: string, format: date-time }


⸻

10. Concurrency & Idempotency
	•	DB constraints:
	•	departure.capacity_available >= 0 guarded via row-level check and serialized updates.
	•	Unique (method, idem_key) table for idempotency results (payload hash stored).
	•	Locking:
	•	For booking/hold, take an advisory lock on departure.id during capacity check/update.
	•	Idempotency semantics:
	•	Replays with same key and same body → return stored response.
	•	Same key with different body → 422 code="IDEMPOTENCY_KEY_MISMATCH".

⸻

11. Observability
	•	Trace: Honor/expose traceparent; include trace_id in Problem responses.
	•	Logs: JSON (request_id, service.method, duration_ms, status).
	•	Metrics: histograms for latency per method; counters for 2xx/4xx/5xx; gauges for active holds.
	•	Headers: echo x-request-id if provided, else generate.

⸻

12. Security & Limits
	•	Bearer token auth; per-method scopes (via tags).
	•	Request body limit: 256 KB.
	•	Rate limits: default 60 rpm per token; respond 429 + Retry-After.
	•	Validation: strict JSON, unknown fields rejected in requests.

⸻

13. Dev Console (Web App)

Purpose: Build and run requests quickly; inspect headers/body; persist examples per method; shareable permalinks.

Features
	•	Environment switch (Local/Staging).
	•	Auth token manager.
	•	Method picker (from OpenAPI); auto-generate form from schemas; raw JSON editor toggle.
	•	Display: request/response tabs, headers, status, duration, trace link.
	•	History drawer; save named scenarios (e.g., “Full booking flow”).
	•	Import/export examples as JSON.
	•	Keyboard-centric UX.

⸻

14. TypeScript Client SDK

Constraints
	•	Framework-agnostic, zero heavy deps; works with Node’s fetch/Undici.
	•	Generated types from OpenAPI; handwritten thin wrapper per method.

Minimal Shape

export type ClientOpts = { baseUrl: string; token: string; fetch?: typeof fetch; timeoutMs?: number };
export class Client {
  constructor(opts: ClientOpts) { /* store opts */ }
  async booking_hold(req: HoldRequest, idemKey: string): Promise<HoldResponse> { /* POST /v1/booking/hold */ }
  async booking_confirm(req: ConfirmRequest, idemKey: string): Promise<BookingResponse> { /* ... */ }
  // All methods...
}

	•	Concerns handled centrally: auth header, Idempotency-Key, timeouts, retry (idempotent ops only), x-request-id, traceparent propagation.

⸻

15. Testing Strategy
	•	Contract tests: Dredd/Schemathesis against OpenAPI (happy paths + fuzz).
	•	Property tests:
	•	Capacity never negative.
	•	Hold expiry restores capacity.
	•	Idempotent confirm returns same booking.
	•	Concurrency tests: N parallel holds near capacity; verify no overbook.
	•	Migration tests: up/down against ephemeral DB.
	•	Load tests: target P95 < 100ms for reads; < 200ms for holds on warm cache.

⸻

16. Background Jobs
	•	Hold Expirer: runs every minute; transitions ACTIVE→EXPIRED; increments capacity; triggers waitlist flow.
	•	Waitlist Notifier: when capacity frees, atomically pop oldest entry and create a short hold (e.g., 5 min) + emit event/log (no email system included).

⸻

17. CI/CD & Repo Layout

/api
  openapi.yaml
  spectral.yaml
  oas-ci/ (oas-diff config, schemathesis cases)
/server
  app/ (FastAPI, routers, models, services)
  db/ (alembic, migrations, seeds)
  tests/ (unit, property, concurrency)
/sdk-ts
  src/ (client.ts, types from openapi-typescript)
/console
  app/ (Next.js pages/components), lib/ (client), tests/
/ops
  docker/, compose.yaml, env examples

Pipelines
	•	Lint OpenAPI (Spectral) → oas-diff (no breaking) → generate TS types → run server tests → run Schemathesis → build console → publish artifacts (SDK npm tag, server image).
	•	On merge to main: publish hosted docs and changelog (diff since last tag).

⸻

18. Acceptance Criteria
	•	OpenAPI defines all methods with examples and error shapes.
	•	FastAPI implements all listed methods with:
	•	Problem Details errors, idempotency storage, advisory locking for holds.
	•	Metrics, tracing, structured logs.
	•	Background expiry + waitlist notify.
	•	TS SDK compiles on Node ≥18, includes types, timeouts, and idempotency helpers.
	•	Dev Console:
	•	Executes any method end-to-end.
	•	Shows request/response + headers + status + trace id.
	•	Saves and replays scenarios.
	•	CI blocks breaking changes; property/concurrency tests pass.

⸻

19. Edge Cases
	•	Hold refresh before expiry: extend TTL; idempotent via same idem key or new key with refresh=true.
	•	Confirm on expired hold: 409 HOLD_EXPIRED.
	•	Inventory decrease below active holds: reject with 409 CAPACITY_CONFLICT.
	•	Duplicate waitlist join for same customer_ref+departure: 200 with existing entry (idempotent).

⸻

20. Milestones
	1.	M0 (Contract): OpenAPI + Spectral rules + examples.
	2.	M1 (Core Server): Tours/Departures CRUD, search, holds with idempotency, confirm/cancel, metrics/traces.
	3.	M2 (Expiry/Waitlist): Worker jobs + conflict handling.
	4.	M3 (SDK + Console): TS client + Dev Console v1 (run/save flows).
	5.	M4 (Hardening): Property/concurrency/load tests; docs site; changelog automation.

⸻

21. Definitions of Done (DoD)
	•	Re-running booking/confirm with same Idempotency-Key returns bit-identical body.
	•	Parallel 100 hold attempts on capacity 50 yields ≤50 ACTIVE holds; no negatives.
	•	Expiring holds restores capacity_available exactly.
	•	Console can complete the full flow A→B with visible trace id.

⸻

22. Appendix — Example Requests

Hold Seats

POST /v1/booking/hold
Authorization: Bearer <token>
Idempotency-Key: K1
Content-Type: application/json

{
  "departure_id": "dep_123",
  "seats": 3,
  "customer_ref": "cust_EVG",
  "ttl_seconds": 600
}

Confirm Booking

POST /v1/booking/confirm
Authorization: Bearer <token>
Idempotency-Key: K2
Content-Type: application/json

{ "hold_id": "hold_456" }

Error (Full)

HTTP/1.1 409 Conflict
Content-Type: application/problem+json

{
  "title": "Capacity full",
  "status": 409,
  "code": "FULL",
  "detail": "Departure dep_123 has no available seats",
  "trace_id": "c0ffee-..."
}


⸻

23. Agent Work Items (ready-to-build)
	•	Generate api/openapi.yaml covering all methods + examples.
	•	Set up server scaffolding, routers per service, Problem handler, idempotency table, advisory locks.
	•	Implement DB schema + migrations.
	•	Implement expiry/notify background workers.
	•	Add OTel, metrics, and structured logging.
	•	Add Spectral + oas-diff + Schemathesis in CI; fail on breaking changes.
	•	Generate TS types; implement sdk-ts/src/client.ts.
	•	Build Dev Console with schema-driven forms, history, and trace display.
	•	Write property/concurrency tests and load tests.
	•	Produce changelog and publish hosted docs on merge.