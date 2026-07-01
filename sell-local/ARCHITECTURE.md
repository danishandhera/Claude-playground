# Sell Local — Architecture

Status: design v1 (2026-07-01). Builds on the README product brief + GitScout prior-art pass. Read the README first; this doc turns it into a concrete build plan.

## 1. Goal & constraints

Aggregate P2P "for sale" ads from Dubai community WhatsApp groups into a clean browse-and-search site. Flow: pick community → browse live listings (post + expiry, expired auto-hidden) → search. Intake is the product: paste-ad web form (Phase 1) and official WhatsApp Cloud API webhook (Phase 2), both feeding one LLM-parse → approval-queue → publish pipeline.

Constraints:
- **Solo founder, ship fast, SQLite-scale.** Boring tech, one deployable, no infra sprawl.
- **Approval queue is Phase 1, non-negotiable** (trust & safety).
- **One pipeline, two channels** — every listing carries `raw_text` + `source`.
- **Auto-hide expired = query filter, never delete.**
- **Search = SQLite FTS5.**
- **Contacts public in Phase 1, but reveal-gate must be a toggle, not a rebuild.**

Assumptions (flag, don't stall): single region/timezone (Asia/Dubai); listings are English/Arabic free text; volume is tens–low-hundreds of listings/day at peak; one admin (the founder) works the queue. Default expiry = 30 days (django-classified pattern).

## 2. Stack recommendation

**Python 3.12 + FastAPI + SQLite (WAL) + Jinja2 server-rendered pages + htmx, deployed as one container on Fly.io. LLM parse via Claude `claude-haiku-4-5` using tool-use structured output validated by Pydantic.**

| Layer | Choice | Why (one line) |
|---|---|---|
| Language | Python 3.12 | Best-in-class LLM SDKs + Pydantic; founder-friendly. |
| Web framework | FastAPI | Async, typed, auto OpenAPI; the same app serves HTML pages, JSON, and the WhatsApp webhook. |
| DB | SQLite + WAL | "Plenty at this scale" per brief; zero ops; **FTS5 ships built in**. One file to back up. |
| Migrations | Alembic (or raw SQL in `/migrations`) | Versioned schema without a heavyweight ORM. |
| Data access | SQLModel (thin over SQLAlchemy) | Pydantic models double as DB rows and API schemas — less glue. |
| Frontend | Jinja2 + **htmx** + Tailwind (CDN) | No SPA. Server-rendered pages; htmx handles search-as-you-type + queue actions. Fast to ship solo, SEO-friendly (matters for a browse site). |
| LLM parse | Claude **`claude-haiku-4-5`**, tool-use JSON, Pydantic-validated | Cheap + fast for high-volume parsing; escalate a failed/low-confidence parse to `claude-sonnet-4-6`. Default per instruction to latest Claude. |
| Hosting | Fly.io (single machine + persistent volume for the SQLite file) | One `fly deploy`; volume gives durable SQLite; cheap. Render/Railway are equivalent runner-ups. |
| Auth (admin) | Single-admin session cookie + password (env var), later WhatsApp-verified | Only the founder needs the queue; don't build user accounts yet. |

**Runner-up (genuinely close):** Node + Hono/Express + better-sqlite3. Equally valid; Python wins only because the LLM-parse + Pydantic-validation loop is cleaner and the founder gets typed structured-output for free. Pick Python unless the founder is more fluent in JS.

**Why not the alternatives we rejected:** no Django (heavy for a thin app; we borrow its *patterns* not its weight), no Postgres/Elasticsearch (SQLite + FTS5 covers it), no React SPA (browse site wants HTML + SEO, htmx covers interactivity).

## 3. Data model

SQLite. `created_at`/timestamps stored UTC ISO-8601; render in Asia/Dubai.

### `community`
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT NOT NULL | e.g. "Arabian Ranches" |
| slug | TEXT UNIQUE NOT NULL | URL key: `/c/arabian-ranches` |
| is_active | BOOLEAN DEFAULT 1 | hide a community without deleting |
| created_at | TEXT NOT NULL | |

The picker is just `SELECT ... WHERE is_active=1`.

### `listing`
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| community_id | INTEGER FK → community.id | which group it belongs to |
| title | TEXT | LLM-extracted |
| description | TEXT | LLM-extracted |
| price | INTEGER | store minor-unit-free integer (AED whole); NULL = "ask"/free |
| currency | TEXT DEFAULT 'AED' | |
| contact | TEXT | **raw phone/handle, always stored**; rendering gated by a flag (§4) |
| image_url | TEXT | local path/URL to stored image; NULL if none |
| source | TEXT NOT NULL | `'web_form'` \| `'whatsapp'` |
| raw_text | TEXT NOT NULL | original message, for re-parse/audit |
| status | TEXT NOT NULL DEFAULT 'pending' | `pending`\|`approved`\|`rejected`\|`postponed` (laravel-moderation semantics) |
| moderated_by | TEXT | admin id/name; NULL until acted on |
| moderated_at | TEXT | timestamp of decision |
| reject_reason | TEXT | optional, for audit / future sender feedback |
| parse_confidence | REAL | 0–1 from parse step; low → flag in queue |
| created_at | TEXT NOT NULL | post date shown to users |
| expires_at | TEXT NOT NULL | default created_at + 30d |

### `listing_fts` (FTS5 virtual table)
`CREATE VIRTUAL TABLE listing_fts USING fts5(title, description, content='listing', content_rowid='id');` kept in sync by triggers on insert/update/delete. Search = FTS5 MATCH joined back to `listing`, filtered by the public predicate below.

**The one public-read predicate (single source of truth, wrap in a helper):**
```sql
WHERE status = 'approved' AND expires_at > :now [AND community_id = :cid] [AND id IN (FTS match)]
```
New rows land `pending` → invisible until approved. Expired rows drop out of the filter automatically; nothing is deleted.

## 4. System shape

One FastAPI app, three route groups + one background concern.

```
Browser ──HTML/htmx──▶ [Public routes]  ─────────────┐
Admin  ──cookie auth─▶ [Admin/queue routes] ─────────┤
Meta   ──webhook─────▶ [/webhook/whatsapp] (Phase 2) ─┤
                                                      ▼
                                          Parse service (Claude tool-use → Pydantic)
                                                      ▼
                                              SQLite (listing, community, FTS)
```

### Trust boundaries
- **Untrusted input:** paste-ad form body + WhatsApp webhook payload. Both are (a) size/rate-limited, (b) stored verbatim as `raw_text`, (c) parsed, (d) landed as `status='pending'`. **No user input is ever published without an admin approval.** That single gate is the trust boundary.
- **Admin routes** sit behind session auth; all mutations (approve/reject/edit) are admin-only, POST + CSRF token.
- **LLM output is untrusted too:** Pydantic-validate the tool-use result; on validation failure keep `raw_text`, set low `parse_confidence`, still enqueue (never drop a submission).
- **WhatsApp webhook:** verify `X-Hub-Signature-256` **before** parsing, using the SDK — do not hand-roll (GitScout note).

### Contact-gate design (honor the "toggle not rebuild" decision)
- `contact` is **always stored raw**.
- All rendering goes through **one** template partial / function `render_contact(listing, viewer)`.
- A config flag `CONTACT_MODE = 'public' | 'gated'`. Phase 1 = `public` → renders the number inline. Flipping to `gated` swaps that one partial for a "Reveal contact" htmx button (later gated on click/login) hitting `GET /api/listings/{id}/contact`. No schema or pipeline change — just the flag + the reveal endpoint (which can be stubbed now).

### Public routes (server-rendered HTML)
| Route | Contract |
|---|---|
| `GET /` | Community picker. Lists active communities. |
| `GET /c/{slug}` | Browse listings for a community. Query params: `q` (search), `page`. Applies public predicate. Returns HTML; htmx swaps the results list on search. |
| `GET /c/{slug}/search` | htmx partial: FTS5 results fragment for `q`. |
| `GET /listing/{id}` | Single listing detail (only if it passes public predicate). |
| `GET /api/listings/{id}/contact` | Reveal-contact endpoint. Phase 1: returns number (or no-op, since public). Exists so the gate is a flag flip. |

### Intake — paste-ad pipeline (Phase 1)
| Route | Contract |
|---|---|
| `GET /submit` | Paste-ad form: community select + free-text textarea (+ optional image upload). |
| `POST /submit` | Body: `community_id`, `raw_text`, optional `image`. → validate size/rate-limit → store image locally if present → call parse service → INSERT listing (`source='web_form'`, `status='pending'`, `expires_at=now+30d`, `parse_confidence`) → show "submitted, pending review". |

Pipeline: **paste → store raw_text → LLM parse (Claude tool-use, Pydantic schema {title, description, price, currency, contact, confidence}) → INSERT pending → admin queue → approve → visible.** Same function `enqueue_listing(source, raw_text, community_id, image?)` is the single entry point for BOTH channels.

### Admin / moderation routes (auth required)
| Route | Contract |
|---|---|
| `GET /admin/login`, `POST /admin/login` | Session cookie. |
| `GET /admin/queue` | Pending (+ postponed) listings, newest first; low-confidence flagged. Shows parsed fields side-by-side with `raw_text`. |
| `POST /admin/listing/{id}/approve` | `status='approved'`, set `moderated_by/at`. Allows inline field edits before approving. |
| `POST /admin/listing/{id}/reject` | `status='rejected'` + `reject_reason`. |
| `POST /admin/listing/{id}/postpone` | `status='postponed'` (revisit later). |
| `POST /admin/listing/{id}/reparse` | Re-run parse on stored `raw_text` (e.g. after prompt tweak). |

### Phase 2 — WhatsApp webhook (slots in with NO redesign)
| Route | Contract |
|---|---|
| `GET /webhook/whatsapp` | Meta verification handshake (`hub.challenge`). |
| `POST /webhook/whatsapp` | Verify `X-Hub-Signature-256` (SDK) → for each message: **download media immediately** (URLs expire ~5 min) → store image → call the SAME `enqueue_listing(source='whatsapp', raw_text=<message text>, community_id=<mapped>, image=<stored>)`. |

Because intake converges on `enqueue_listing()` and the queue/publish path is channel-agnostic (`source` distinguishes origin, `raw_text` preserved), Phase 2 adds only: the two webhook routes, media download, and a sender→community mapping. Everything downstream is reused.

## 5. Phased build plan

**Milestone 0 — Scaffold (Backend).** FastAPI app skeleton, SQLite + WAL, migrations, `community`/`listing` tables + `listing_fts` + triggers, seed 1–2 communities, config/env, public-predicate helper, deploy pipeline (Fly). *Dependency for everything.*

**Milestone 1 — Browse + search (Frontend + Backend).**
- Backend: `GET /`, `GET /c/{slug}`, `GET /listing/{id}`, FTS5 search query. Seed with hand-inserted approved listings.
- Frontend: picker page, listing grid, listing detail, htmx search-as-you-type, `render_contact` partial (public mode), expiry/post-date rendering (Dubai TZ). Tailwind styling.
- Deliverable: a browseable site with fake data.

**Milestone 2 — Intake + parse (Backend).** Parse service (Claude tool-use + Pydantic + confidence + Sonnet escalation), `enqueue_listing()`, `GET/POST /submit`, image storage. Deliverable: a submission lands as `pending`.

**Milestone 3 — Approval queue (Backend + Frontend).** Admin auth, `/admin/queue`, approve/reject/postpone/reparse, inline edit. Deliverable: end-to-end paste → parse → approve → live. **This closes the Phase-1 loop — ship + validate one community here.**

**Defer:** WhatsApp webhook (Phase 2, gated on Meta verification); reveal-contact gating (flag exists, wire the button when the founder decides); user accounts/favourites; multi-admin; categories/images gallery; analytics.

**Ownership:** Backend owns M0, M2, and the API/query side of M1/M3. Frontend owns pages/partials/htmx in M1/M3.

## 6. Risks & mitigations

1. **PII / contact exposure (highest).** Public phone numbers invite scraping/scam-harvesting and clash with UAE privacy expectations. *Mitigation:* contact rendering isolated behind one flag/partial + a ready reveal endpoint, so switching to gated is a config flip, not a migration. `raw_text` may also contain numbers — the parse step should extract `contact` into its field and the queue lets the admin scrub stray PII from `description` before approval. **Open decision for user below.**

2. **WhatsApp/Meta verification lag & media expiry (Phase 2).** Meta Business verification takes weeks (tie to IFZA license) and media URLs die in ~5 min. *Mitigation:* Phase 2 is fully decoupled — Phase 1 ships and validates without it. When it lands, download-media-on-receipt is baked into the webhook contract, and signature verification uses the SDK (no hand-rolled crypto).

3. **Parse quality / cost & moderation load.** Bad parses erode trust; a flood of junk submissions buries the solo admin. *Mitigation:* every submission is stored `raw_text`-first and never dropped; `parse_confidence` surfaces shaky parses; admin edits before approve; the approval gate itself is the spam wall. Rate-limit `/submit` per IP. SQLite-scale is fine until a community proves adoption — no premature scaling. (Note: SQLite single-writer means the webhook + admin writes serialize; at this volume that's a non-issue, but keep writes short.)

**Prior-art credits:** listing/expiry model + filter search ← [slyapustin/django-classified](https://github.com/slyapustin/django-classified); moderation state machine (`status`/`moderated_by`/`moderated_at`, default = approved-only) ← [hootlex/laravel-moderation](https://github.com/hootlex/laravel-moderation) (patterns only, confirm licenses before copying code); webhook signature handling ← official WhatsApp Node SDK / whatsapp-api-js.

## 7. Handoff

**Backend builds:** the FastAPI app, SQLite schema + FTS5 + triggers, the public-read predicate helper, `enqueue_listing()`, the Claude parse service (Pydantic-validated tool-use), `/submit`, admin auth + moderation routes, and the deploy. Exposes server-rendered routes and htmx partial endpoints.

**Frontend builds:** Jinja2 templates + Tailwind for the picker (`/`), community browse (`/c/{slug}`) with htmx search, listing detail, the `render_contact` partial (public mode + reveal-button stub), and the admin queue UI (side-by-side parsed vs. raw_text, approve/reject/postpone/edit controls).

**Contract between them:** server renders HTML; Frontend consumes route responses + htmx partials, not a JSON API (except the reveal-contact endpoint and htmx search fragment). Shared truths both must honor: (a) the single public predicate `status='approved' AND expires_at > now'`; (b) all contact rendering flows through `render_contact()` + `CONTACT_MODE`; (c) statuses are exactly `pending|approved|rejected|postponed`; (d) timestamps UTC in DB, Asia/Dubai in UI. Parse output schema `{title, description, price:int|null, currency, contact, confidence:float}` is the frontend/backend field contract for both the queue and listing views.

**Open decisions needing the user:**
1. **Contact policy for launch** — confirm public in Phase 1 (design supports flipping to gated later). Default assumption: public.
2. **Python vs. Node** — recommend Python; confirm if you're more fluent in JS (runner-up stack is ready).
3. **Community→sender mapping for Phase 2** — how does a WhatsApp message know which community it's for (one number per community, or a keyword prefix in the message)? Not needed until Phase 2, but decide before building intake mapping.
4. **Image handling in Phase 1 web form** — allow uploads at launch or defer to Phase 2 (schema already has `image_url`)? Default: optional upload allowed.
