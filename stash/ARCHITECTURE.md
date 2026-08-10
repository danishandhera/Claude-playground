# Stash — Architecture

Status: design v1 (2026-08-01). Builds on the README product brief + the GitScout prior-art pass. Read the README first; this doc turns "here's the idea" into an exact, buildable plan for the Frontend and Backend agents.

## 0. One-paragraph recommendation

Build Stash as **a single local Python service on the M4 (FastAPI + SQLite) that serves a small React/Vite mobile web UI, with all heavy compute (Whisper, OCR, embeddings) done on-device and the only paid tokens spent in one batched Claude call per post — cached forever by shortcode.** Ingest is two-track exactly as GitScout found: parse the official **DYI export** for a complete, ban-free seed of every save (URL + author + collection + date), then **lazily enrich** each row via Instagram's private mobile JSON endpoints using the user's own cookies, behind a hard-coded rate-limit engine. Enrichment is a **cascade**: caption first (free, already in the API response), then Whisper transcript only for thin-caption Reels, then Vision OCR only for text-on-screen posts, then exactly one LLM structuring call to produce `{title, category, entities, summary, tags}`. Search and "what to watch next" run entirely locally on `sqlite-vec` embeddings. Ship in phases where **1a (DYI parse + searchable app) is independently useful with zero Instagram API risk and zero token cost** — everything riskier or costlier is gated behind proving that plumbing.

## 1. Goal & constraints

**Goal.** A personal, mobile-accessible web app that turns hundreds–thousands of Instagram saves into a *searchable, self-summarizing library*. The user searches by **content** ("anime", "leg day", "Dubai brunch"), gets **titled + summarized cards** instead of raw reels, and asks **"what should I watch next"** within a collection/category and gets ranked recommendations — all without opening Instagram.

**Constraints (hard):**
- **Single user, self-hosted on an M4 MacBook Air 16GB.** Favor local/free compute: whisper.cpp on the Neural Engine, Apple Vision OCR, local embeddings. No cloud GPU.
- **Token/cost-conscious.** Minimize LLM calls; cache deterministically per shortcode; cascade-gate the heavy stages so most posts never reach the LLM at all. Backfill is a **one-time** cost; steady state is near-zero.
- **Instagram rate limits & ban-avoidance are non-negotiable.** The seed is ban-free (DYI export). The enricher touches IG's private API and must obey a hard-coded rate controller with hard-stop on any challenge/checkpoint.
- **Mobile-accessible.** The end product is a web UI usable one-handed from the phone, inside the existing cross-device (claude.ai/code + repo) setup.

**Assumptions (flagged, not stalling):**
- **Compute and UI live on the same Mac.** "Mobile-accessible" = the phone reaches the Mac over the LAN (or a tunnel), not a public multi-tenant deployment. The Mac is the server; the phone is a thin client. (See §2 hosting + §7 open decisions for the tunnel choice.)
- **The Mac is not always on.** Enrichment is a job the user kicks off while the Mac is awake; the UI degrades gracefully to "seed-only" cards for not-yet-enriched posts.
- **Timezone Asia/Dubai, English UI.** DYI timestamps are Unix UTC; render local.
- **Collections are the user's ground-truth categories** (movies/songs/workouts/food/travel/anime…). We treat the DYI collection label as the primary category and let the LLM refine a finer `category`/`tags` within it.
- **Volume:** low thousands of posts. SQLite + `sqlite-vec` brute-force cosine over a few thousand vectors is sub-millisecond — no dedicated vector DB needed.

**Non-goals (v1):** multi-user/accounts, public hosting, real-time IG sync, downloading/rehosting media, a browser extension (kept as a *fallback* ingest, §7), anything that rehosts Instagram content publicly.

## 2. Stack recommendation

**One local Python service: FastAPI + SQLite (`sqlite-vec`) doing ingest, enrichment, and API; serving a React + Vite + TypeScript + Tailwind mobile UI as static files. Whisper via `whisper.cpp` (Core ML), OCR via Apple Vision (`ocrmac`), embeddings via a local sentence-transformer. Exactly one hosted dependency: the Anthropic API for the single structuring call per post.**

| Layer | Choice | Why (one line) |
|---|---|---|
| Backend language | **Python 3.12** | The entire prior-art ecosystem (instaloader RateController, the `instagram_sync.py` endpoints, whisper.cpp bindings, `ocrmac`, sentence-transformers, `sqlite-vec`) is Python — reuse, don't re-derive. |
| Backend framework | **FastAPI + Uvicorn** | Boring, async-friendly, gives typed request/response models the Frontend consumes directly; serves both the JSON API and the built static UI from one process. |
| Job runner | **In-process background tasks + a `jobs` table** (no Celery/Redis) | Single user, single machine, one long backfill — a simple worker loop reading a checkpointed queue is enough; a broker is over-engineering here. |
| DB | **SQLite (WAL mode)** | One file, zero ops, perfect for single-user; holds seed rows, lazy enrichment, cache, checkpoints, and vectors in one place. |
| Vector store | **`sqlite-vec`** (vec0 virtual table in the same DB) | Keeps embeddings beside the data — no second datastore; brute-force cosine over a few thousand vectors is instant. |
| Embeddings | **Local `bge-small-en-v1.5`** (or `all-MiniLM-L6-v2`) via sentence-transformers | Free, fast on the M4, 384-dim, good enough for semantic search over short cards; zero per-query token cost. |
| Transcription | **`whisper.cpp` + Core ML, `base.en` (fallback `small.en`)** | Runs on the Neural Engine for free; only invoked for thin-caption Reels (cascade-gated). |
| OCR | **Apple Vision via `ocrmac`** | Free, native, high-quality on-screen text extraction; only for text-on-screen posts. |
| Video pull (audio only) | **`yt-dlp`, audio-only, on demand** | Reserved strictly for fetching audio when Whisper is needed; never a bulk downloader. `gallery-dl` (GPL-2.0) only ever shelled out as a CLI if used at all, never vendored. |
| LLM structuring | **Anthropic Claude (Haiku-class), one batched call per post** | The *only* token spend; produces `{title, category, entities, summary, tags}`; cached forever by shortcode. |
| Cookie extraction | **`browser_cookie3` / the prior-art `extract_cookies.py` (pycryptodome)** | Pull+decrypt the user's own IG cookies from Chrome/Safari for the enricher session. |
| Frontend | **React 18 + Vite + TypeScript + Tailwind** | Same stack as sibling projects (beanbuds/helthi) → familiar, fast to build a nice mobile card/search UI; built to static files FastAPI serves. |
| Frontend data | **Plain `fetch` + React Query (TanStack)** | Server owns the data; React Query handles search/list fetching, caching, and the "enrichment in progress" polling cleanly. |
| Hosting | **Localhost on the Mac + a Tailscale (or Cloudflare) tunnel for phone access** | Zero-cost, private, no public multi-tenant surface; the phone hits the Mac over the user's tailnet. (Open decision §7.) |

**Why one service, not a split frontend/backend deployment?** Single user, single machine. Splitting adds CORS, two processes, and two deploy targets for no benefit. FastAPI serves the built React bundle at `/` and the API under `/api/*` from one Uvicorn process the user starts with one command.

**Why SQLite + `sqlite-vec`, not Postgres/pgvector or a vector DB (Chroma/Qdrant/Pinecone)?** A few thousand short cards is tiny. `sqlite-vec` keeps vectors in the same file as the rows they belong to — one backup, one connection, no second service, no network hop, no cloud vendor. Postgres/pgvector or a dedicated vector DB is operational weight this scale never repays.

**Why local embeddings + local Whisper/OCR, not API calls for them?** The M4's Neural Engine does all three for free and offline. Paying per-token to transcribe or embed thousands of posts would blow the cost constraint; the *only* thing worth an API call is the final reasoning/structuring step, and even that is gated so most posts skip it.

**Why not a pure-PWA/no-backend design (the beanbuds pattern)?** Stash *needs* server-side compute: an authenticated IG session, rate-limited fetching, Whisper/OCR, and embedding. That can't live in the browser. So Stash is the one sibling project with a real (but local, single-user) backend — the UI stays thin.

## 3. Data model (SQLite)

WAL mode. Timestamps stored as Unix epoch (UTC) integers; rendered Asia/Dubai. `shortcode` is the natural dedupe key across every table and cache. **Seed rows are inserted complete from the DYI export; all enrichment columns are nullable and filled lazily** — a post is always at least a clickable seed card, and progressively becomes a rich card.

### `posts` — one row per saved item (seed + lazily-filled enrichment)
| column | type | source / notes |
|---|---|---|
| id | INTEGER PK | local autoincrement |
| shortcode | TEXT UNIQUE NOT NULL | **the dedupe & cache key**; parsed from the DYI post URL |
| url | TEXT NOT NULL | DYI `string_map_data["Saved on"].href` |
| author | TEXT | DYI item `title` (author handle) |
| saved_at | INTEGER | DYI `"Saved on".timestamp` (Unix) |
| ig_media_id | TEXT | filled by enricher (`id` from private API) |
| author_display | TEXT | enricher |
| media_type | INTEGER | enricher: `1→Post, 2→Reel/Video, 8→Carousel` — **decides the cascade** |
| content_type | TEXT | derived label from media_type |
| caption | TEXT | enricher (already in the API response) |
| thumbnail_url | TEXT | enricher: `image_versions2.candidates[0].url` |
| likes | INTEGER | enricher |
| transcript | TEXT | Whisper stage (nullable; only thin-caption Reels) |
| ocr_text | TEXT | Vision stage (nullable; only text-on-screen posts) |
| **title** | TEXT | LLM structuring output |
| **category** | TEXT | LLM (refines the collection label) |
| **summary** | TEXT | LLM |
| **entities** | TEXT (JSON array) | LLM (e.g. movie names, exercise names, place names) |
| **tags** | TEXT (JSON array) | LLM |
| enrich_status | TEXT | `seed` → `fetched` → `enriched` \| `failed` \| `unavailable` (deleted/private) |
| enriched_at | INTEGER | when the LLM stage completed |
| embed_text | TEXT | the merged caption+transcript+ocr+title+summary string that was embedded (for reproducibility) |

Indexes: `shortcode` (unique), `author`, `saved_at`, `enrich_status`, `category`.

### `collections` — the user's IG collections (ground-truth categories)
| column | type | source |
|---|---|---|
| id | INTEGER PK | local |
| ig_collection_id | TEXT | enricher (`/collections/list/`) — nullable; DYI gives names, API gives ids |
| name | TEXT NOT NULL | DYI `saved_saved_collections` name / API name |

### `post_collections` — join (a post can be in multiple collections)
| column | type | notes |
|---|---|---|
| post_id | INTEGER FK → posts.id | |
| collection_id | INTEGER FK → collections.id | |

PK = (post_id, collection_id). *(DYI files each save under the collection it was saved to; the join keeps it many-to-many for safety.)*

### `post_vectors` — `sqlite-vec` vec0 virtual table
```sql
CREATE VIRTUAL TABLE post_vectors USING vec0(
  post_id INTEGER PRIMARY KEY,
  embedding FLOAT[384]        -- bge-small-en / MiniLM dimension
);
```
One vector per post, embedded from `embed_text`. Re-embed only when `embed_text` changes.

### `enrich_cache` — deterministic per-stage cache (never redo work)
| column | type | notes |
|---|---|---|
| shortcode | TEXT | with `stage` forms the key |
| stage | TEXT | `api` \| `whisper` \| `ocr` \| `llm` \| `embed` |
| payload | TEXT (JSON) | the raw stage output (raw API JSON, transcript, OCR text, LLM JSON) |
| created_at | INTEGER | |

PK = (shortcode, stage). **This is the cost-control spine:** every expensive step checks the cache first; a re-run of the pipeline is free for anything already done. Survives DB migrations and re-parses.

### `jobs` / `checkpoints` — resumable ingest
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| kind | TEXT | `dyi_import` \| `api_fetch` \| `enrich` |
| status | TEXT | `queued` \| `running` \| `paused` \| `done` \| `failed` |
| cursor | TEXT | last `next_max_id` for API pagination |
| stats | TEXT (JSON) | counts: fetched / enriched / skipped / errored |
| updated_at | INTEGER | |

Plus a lightweight **`ingested_media` dedupe set** (or reuse `posts.ig_media_id` / `shortcode`) so a resumed fetch never re-processes an already-seen id. **Rule: never re-fetch or re-enrich a shortcode that's already `enriched`.**

### `settings` — single-row app config
Cookie freshness marker, last successful auth time, rate-limit knobs, chosen Whisper model. Drives the re-auth banner (§6).

## 4. Ingest + enrichment pipeline

Two tracks feeding one staged, cached, resumable job. **Media_type, known before any heavy work, decides how far down the cascade a post goes.**

```
TRACK A — SEED (ban-free, no IG API, no tokens)
  DYI .zip ──▶ parse saved_posts.json (root: saved_saved_media)
                 └ item → {author, url→shortcode, saved_at}
             parse saved_collections.json (root: saved_saved_collections)
                 └ collection names + membership
  ──▶ UPSERT posts (enrich_status='seed') + collections + post_collections
  ✅ At this point the app is already searchable by collection/author/date + full-text on nothing-yet.

TRACK B — ENRICH (private IG API, rate-limited, cached, lazy)
  for each post where enrich_status='seed', oldest-cursor-first:
    [rate controller gate]  ← see §4.1; sleep/backoff/hard-stop here
    (1) API fetch  → media_type, caption, author_display, thumbnail, likes, ig_media_id
                     cache stage 'api'; set enrich_status='fetched'
    ── CASCADE GATE on media_type + caption richness ──
    (2) caption sufficient?  (len ≥ N chars & not just hashtags)
           yes → skip transcript & OCR
    (3) Reel/Video (media_type 2) AND caption thin?
           yes → yt-dlp audio-only → whisper.cpp (base.en) → transcript
                 cache stage 'whisper'
    (4) text-on-screen likely? (Reel/Carousel AND still thin after caption)
           yes → download 1 frame/thumbnail → Apple Vision OCR → ocr_text
                 cache stage 'ocr'
    (5) ONE batched LLM call over {caption, transcript, ocr_text, collection}
           → {title, category, entities, summary, tags}
           cache stage 'llm'; set enrich_status='enriched'
    (6) embed_text = merge(title, summary, caption, transcript, ocr_text)
           → local embedding → upsert post_vectors; cache stage 'embed'
    checkpoint cursor + dedupe id after each post.
```

**Cascade-gating logic (the cost lever).** Most posts stop early:
- **Post / Carousel (type 1/8):** no video → **never** transcribed. Caption (+ OCR only if still thin) → LLM. Cheapest path.
- **Reel with a rich caption:** caption alone → LLM. **No Whisper, no OCR.**
- **Reel with a thin caption:** Whisper transcript → (OCR if text-on-screen) → LLM. The expensive path, hit by a minority.
- **Every stage checks `enrich_cache` first.** Re-running the pipeline re-does nothing already computed. This is what makes backfill a *one-time* cost and steady-state ~free.

The LLM call is **batched per post** (single message carrying caption+transcript+ocr+collection, structured-output/tool schema for the five fields) and is the **only** token spend in the whole system (§5).

### 4.1 Rate-limit engine (hard-coded, from instaloader's RateController)

A single `RateController` wraps the enricher `requests.Session` (browser headers + `X-CSRFToken` from the `csrftoken` cookie). Rules, hard-coded:
- **Per-query-type sliding windows:** ~200 requests / 11-min window per query type; ~75 / window for "other"; global ~275 GraphQL / 10-min; ~200 iPhone-API / 30-min. Track timestamps per bucket; block until the oldest falls out of window.
- **Pre-request jittered sleep:** `sleep(min(expovariate(0.6), 15s))` before each call — human-like pacing.
- **Backoff:** exponential on HTTP 429; retry with growing delay, capped.
- **HARD-STOP (non-negotiable):** on `challenge_required`, `checkpoint_required`, or a login-redirect → **pause the job, do not retry**, set `settings.needs_reauth=true`, surface a first-class **"Re-auth needed"** state to the UI. Never hammer through a challenge.
- **Resume:** persist last `next_max_id` cursor + the dedupe set every post, so a paused/killed job resumes exactly where it stopped and **never re-fetches an enriched shortcode**.

Pagination follows `next_max_id` / `more_available` across `/api/v1/feed/saved/posts/` and `/api/v1/feed/collection/{id}/posts/`; `/api/v1/collections/list/` seeds collection ids.

### 4.2 Idempotency & re-runs
Everything keys on `shortcode`. Re-import the DYI export → UPSERT (no dupes, new saves added). Re-run enrichment → skips anything `enriched`, resumes `seed`/`fetched`. Delete the DB, keep `enrich_cache` (or vice-versa) → the cache rehydrates enrichment without re-fetching or re-spending tokens. A post that's gone (deleted/private) → `enrich_status='unavailable'`, still shows as a seed card.

## 5. Cost / token model

**The only paid tokens in Stash are the single Claude structuring call per post (stage 5). Everything else is local and free.**

- **Seed (Track A):** $0, 0 tokens, 0 IG calls. Fully useful on its own.
- **API fetch, Whisper, OCR, embeddings:** local/free compute on the M4. No tokens.
- **LLM structuring:** one Haiku-class call per post, small input (caption + transcript + OCR, all short text), small structured output. Ballpark low-hundreds of input tokens + ~150 output per post → **backfilling a few thousand posts is a one-time low-single-digit-dollars cost**, not recurring.
- **Caching makes it one-time:** `enrich_cache` stage `llm` means a post is *never* re-sent to the LLM. Steady state = only genuinely new saves since the last DYI export get a call. Search and recommendations spend **zero** tokens (local embeddings + local ranking).
- **Gating shrinks even the one-time cost:** cascade means most posts reach the LLM with just a caption (cheapest), a minority carry a transcript. No post triggers more than one LLM call.

**Cost knobs exposed in `settings`:** LLM model (Haiku vs. skip-LLM "captions-only" mode), Whisper model (`base.en`/`small.en`), min-caption-length gate `N`. The user can run a **$0 mode** (no LLM: title = first caption line, category = collection, search still works on caption+transcript embeddings) and only turn on the LLM if the richer cards prove worth it.

## 6. Search + recommendation design

All local, all token-free, over the enriched records.

**Card model (what the UI renders).** A search result / list item = `{shortcode, url, thumbnail_url, title, category, summary, tags, author, saved_at, collections[], enrich_status}`. Un-enriched posts render a seed card (author + collection + "open" link + "enrich now"); enriched posts render the rich card (title, summary, tags). One component, progressive fill.

**Semantic search.** `embed(query)` locally → cosine k-NN over `post_vectors` (`sqlite-vec`), optionally pre-filtered by collection/category/author/date in SQL. Blend with a cheap SQLite FTS5 keyword match over `title/caption/transcript/tags` so exact terms ("Naruto", a specific restaurant) rank even if the embedding is fuzzy. Return ranked cards. `"anime"` → semantically-near anime posts as titled, summarized cards — the core value.

**"What should I watch next" (recommendations over a category).** Scoped to a collection/category, blend three signals, all local:
1. **Relevance to intent** — if the user gives a seed ("more like this one" / "something short and funny"), cosine to that seed/query vector.
2. **Freshness/novelty** — surface saves the user likely forgot: older `saved_at`, and de-prioritize anything recently opened (track `last_opened_at` in a tiny events table — optional, additive).
3. **Diversity** — MMR (maximal-marginal-relevance) re-rank so the list isn't five near-duplicate posts; spread across entities/tags within the category.

Default "what to watch next in anime" with no seed = novelty + diversity ranking over the anime category (forgotten gems, varied). With a seed/query = relevance-weighted. All three are vector math + SQL over a few thousand rows → instant, $0.

**Endpoints (contract the Frontend builds against):**
| method + path | purpose | returns |
|---|---|---|
| `POST /api/import/dyi` | upload DYI zip → parse → seed | job id + counts |
| `GET /api/posts` | list/filter (collection, category, author, status, sort) | paginated cards |
| `GET /api/search?q=&collection=&limit=` | semantic+FTS blended search | ranked cards |
| `GET /api/recommend?category=&seed=&limit=` | "what to watch next" | ranked cards |
| `GET /api/collections` | list collections + counts | collections |
| `POST /api/enrich/start` (opt. `?collection=`) | kick off / resume enrichment job | job id |
| `GET /api/jobs/{id}` | progress polling (counts, status, needs_reauth) | job state |
| `POST /api/enrich/post/{shortcode}` | enrich one post on demand | updated card |
| `GET /api/status` | auth/cookie freshness, needs_reauth flag | status |

**Trust boundaries.** Single-user, localhost + private tunnel → the main boundary is *outbound* to Instagram (the rate controller + cookie handling) and the one *outbound* Claude call. Inbound is one trusted user; validation is light (file-type check on the DYI upload, size caps, JSON-schema-validate the export before parsing). The IG cookies and the Anthropic key live in a local `.env` / macOS keychain, never in the repo, never sent to the browser.

## 7. Phased build plan

Each phase is independently useful and gated so risk/cost only appears once the prior phase proves out. **Phase 1a ships with zero IG-API risk and zero token cost.**

**Phase 1a — DYI parse + minimal searchable app (proves the plumbing).**
Backend: DYI-zip parser (`saved_posts.json` + `saved_collections.json` → `posts`/`collections`/`post_collections`, `enrich_status='seed'`); FastAPI skeleton; `GET /api/posts`, `GET /api/collections`, `POST /api/import/dyi`. Frontend: mobile UI — collection filter, author/date sort, FTS keyword search over what's there, seed cards linking out to IG. **No IG API, no tokens, no Whisper.** Deliverable: every save is browsable/searchable/filterable on the phone. *This is the whole of the README's current Phase 1 — validate it first.*

**Phase 1b — caption enrichment via private API (the real unlock).**
Backend: cookie extract/decrypt; the `requests.Session` enricher hitting `/collections/list/`, `/feed/saved/posts/`, `/feed/collection/{id}/posts/` with pagination; the **§4.1 rate controller** (windows, jittered sleep, backoff, hard-stop, checkpoint/resume); fill `media_type/caption/thumbnail/author_display/likes`; `enrich_cache` stage `api`; the re-auth flow + `GET /api/status`. Frontend: enrich-progress UI, the **re-auth banner**, rich cards showing caption+thumbnail. **Still no tokens** (captions alone already make cards far better). Deliverable: real thumbnails, captions, and IG-native categories, safely fetched.

**Phase 1c — transcript/OCR for thin-caption reels.**
Backend: the cascade gate; `yt-dlp` audio-only + `whisper.cpp` (Core ML) for thin-caption Reels; Apple Vision OCR for text-on-screen posts; cache stages `whisper`/`ocr`. Deliverable: even caption-less reels become searchable by their actual spoken/on-screen content — *without watching them*.

**Phase 2 — semantic search + recommendations (+ the one LLM call).**
Backend: the single batched Claude structuring call → `{title, category, entities, summary, tags}` (cache stage `llm`); local embeddings → `post_vectors`; `GET /api/search` (semantic+FTS blend) and `GET /api/recommend` (relevance+novelty+diversity/MMR). Frontend: the summarized-card search results and the "what should I watch next" view per category. Deliverable: the full product thesis — find-by-content + recommend, all local, one-time token cost.

**Deferred (designed-for, not built):** browser-extension fallback ingest (prior art `RiaDhanani/instagram-organizer`) if cookie/API auth breaks; a "$0 no-LLM mode" toggle; opened-history for better novelty ranking; incremental re-import automation.

**Ownership / handoff:**
- **Backend agent owns:** the DYI parser, the enricher + rate controller, the cascade pipeline, Whisper/OCR/embedding integration, the single LLM call, `sqlite-vec` search/recommend, and all `/api/*` endpoints. Core files (suggested): `stash/backend/parser.py`, `enricher.py`, `rate_controller.py`, `pipeline.py`, `llm.py`, `search.py`, `db.py`, `main.py`.
- **Frontend agent owns:** the React/Vite/Tailwind mobile UI — collection browser, search bar, the progressive card component, the recommend view, and the enrich-progress + re-auth banner. Built to static files served by FastAPI.
- **Contract between them:** the §6 endpoint table + the **card JSON shape** (`{shortcode, url, thumbnail_url, title, category, summary, tags, author, saved_at, collections[], enrich_status}`). Shared truths: (a) a post is *always* a valid card even at `enrich_status='seed'` — the UI must render progressive fill, never assume enrichment; (b) `shortcode` is the id everywhere; (c) job progress + `needs_reauth` come from `GET /api/jobs/{id}` and `GET /api/status`, which the UI polls; (d) search/recommend never block on enrichment — they rank whatever's embedded so far.

## 8. Risks & mitigations

1. **Instagram ban / rate-limit trip (highest).** The enricher uses the user's real session against private endpoints. *Mitigation:* the seed is 100% ban-free (DYI export), so the app is useful with zero API risk; the enricher is fully gated by the §4.1 rate controller (windows + jittered human-like sleep + backoff) and **hard-stops on any challenge/checkpoint** rather than pushing through; enrichment is lazy/resumable so it can run slow over days. The extension-scrape fallback (§7) is the escape hatch if the API path gets hostile.

2. **Cookie expiry (frequent, expected).** IG cookies die every few weeks. *Mitigation:* re-auth is a **first-class flow, not an error** — `settings.needs_reauth`, a persistent UI banner, a one-tap "refresh cookies" that re-runs the extractor; jobs pause and resume cleanly from the checkpoint cursor. Designed as normal operation.

3. **ToS / gray-area posture.** Parsing your *own* DYI export is explicitly sanctioned; hitting private endpoints with your own session is the gray part. *Mitigation:* single-user, personal, **no rehosting or public redistribution of IG content** (thumbnails cached locally, cards link back to IG); the whole heavy path is opt-in and gated behind the sanctioned seed. Keep it personal and private.

4. **Schema drift (DYI export + private API).** IG changes JSON shapes. *Mitigation:* validate the DYI export against the known `saved_saved_media` / `saved_saved_collections` schema on import and fail loudly with a diff, not silently; keep the raw API JSON in `enrich_cache` stage `api` so a parser fix can re-derive fields from cache **without re-fetching** (no extra ban risk, no tokens); isolate all field-mapping in `_parse_media_item`-style functions so drift is a one-file fix.

5. (Watch) **Whisper/OCR latency on the M4.** Thousands of thin-caption reels could be slow. *Mitigation:* cascade means only a minority need Whisper; `base.en` on Core ML is fast; it's a background, resumable, one-time backfill — throughput doesn't gate usefulness because seed+caption cards are already searchable.

**Prior-art credits:** DYI saved-export schema + parse ← [`onfabric/context-use`](https://github.com/onfabric/context-use) (`instagram/saved/schemas.py`, `pipe.py`, MIT); private-endpoint enricher + `_parse_media_item` normalized record + cookie extract/decrypt ← [`ayo-byte/instagram-notion-sync`](https://github.com/ayo-byte/instagram-notion-sync) (`instagram_sync.py`, `extract_cookies.py`, MIT); rate-limit engine (windows, jittered sleep, backoff, checkpoint/resume, challenge hard-stop) ← [instaloader `RateController`](https://github.com/instaloader/instaloader); extension-scrape fallback ingest ← [`RiaDhanani/instagram-organizer`](https://github.com/RiaDhanani/instagram-organizer). `gallery-dl` (GPL-2.0) only ever shelled out as a CLI, never vendored.

## 9. Open decisions needing the user

1. **Phone access method** — **Tailscale** (recommended: private tailnet, the phone reaches `mac:8000`, zero public surface) vs. a **Cloudflare Tunnel** (public URL, needs auth in front) vs. **LAN-only** (same-Wi-Fi only, simplest). Default: Tailscale.
2. **LLM on or off for v1** — ship Phase 2 with the Haiku structuring call (richer titles/summaries/entities, one-time low-$ cost) or start in **$0 no-LLM mode** (title = caption line, category = collection) and enable the LLM later? Default: build the pipeline LLM-ready, ship with it on for a small batch, let you judge the value before backfilling everything.
3. **Whisper model** — `base.en` (faster) vs. `small.en` (more accurate) for the thin-caption reels. Default: `base.en`, upgrade only if transcripts are weak.
4. **Embedding model** — `bge-small-en-v1.5` vs. `all-MiniLM-L6-v2` (both 384-dim, both fine). Default: `bge-small-en-v1.5`.
5. **Enrichment scope** — enrich everything, or only specific collections you actually search (e.g. anime/movies/food) to shrink the one-time backfill? Default: enrich on demand per collection, most-used first.
6. **Extension fallback** — build the browser-extension ingest now, or keep it deferred until (if) the API path breaks? Default: deferred.
