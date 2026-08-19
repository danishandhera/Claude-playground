# Portfolio Status

_Living dashboard of all projects, maintained by the GM. Ask "where are we?" anytime._

**Last updated:** 2026-08-19

Legend — Phase: 💡 idea · 📐 design · 🔨 building · 🧪 validating · 🚢 shipped · ⏸ paused

---

## At a glance

| Project | Phase | Next action | Owner | Blocker |
|---|---|---|---|---|
| **firsttimemoms** | 🔨 → 🧪 | Focus group + onboard 2–3 real caregivers | **User** | Real caregiver supply (none yet) |
| **Sell Local** | 🚢 (M0/M1) | Decide M2 (paste-ad intake + LLM parse + approval queue) | Team/User | None |
| **food-compare** | 🚢 | Add real fixtures to arm the benchmark guard | User | None |
| **dubizzle-tool** | 🚢 | — (built; local listing filter) | — | None |
| **beanbuds** | 📐 | Review blueprint + answer 5 open Qs, then build v1 (PWA) | **User** | None |
| **Stash** | 📐 | Confirm 2 blueprint decisions + request IG export | **User** | Waiting on export file |
| **helthi** | 💡 → 📐 | Confirm tz + HR-zone model; then Phase 0/1 build (Whoop spine) | Team/User | Samsung export sample (gates Phase 3) |
| **DubaiWatchExchange** | 🔨 → 🧪 | Work the GO-LIVE checklist in the sub (rules/AutoMod/wiki/flairs) | **User** | None |

---

## firsttimemoms — UAE/GCC cultural postpartum caregiver marketplace
- **State:** Validated (Reviewer GO) → extracted from Claude prototype into a real Vite + React app. **Builds clean, runs, on GitHub.**
- **Location:** `firsttimemoms/` · pushed to `danishandhera/Claude-playground` (commit 3a6c827)
- **Done:** modular split (theme/scoring/data+hooks/App); priorities wired into matching; budget-bucket bug fixed; Card hoisted; data-loading hooks added.
- **Next (user):** run a focus group; onboard 2–3 real caregivers from UAE mum Facebook groups — this is the real unlock.
- **Next (team, later):** deferred cleanups (hoist `Frame`, accessibility pass); wire real backend/auth/bookings/reviews (dead CTAs are clean seams).
- **Open decisions:** Arab/GCC as its own segment card vs. a religious-support filter · first shop products (mughat + black-seed-honey?) · WhatsApp business number status.

## Sell Local — aggregator for P2P ads from Dubai community WhatsApp groups
- **State:** M0+M1 built, Tailwind-styled, **security-reviewed (SHIP), and on GitHub** (commit 8c384c0). FastAPI + SQLite + FTS5, browse/detail/search, 15/15 smoke checks. Mobile-first teal/slate design.
- **Location:** `sell-local/` · pushed to `danishandhera/Claude-playground`
- **Next (M2/M3):** paste-ad intake + LLM parse + approval queue; later Phase 2 WhatsApp Cloud API intake.
- **Confirmed:** stack Python/FastAPI/SQLite/htmx on Fly.io; contacts public in Phase 1 (one-line flip to gated); pin Python 3.12 in a Dockerfile at deploy.
- **Tracked follow-ups (from Reviewer, non-blocking):**
  - Backend: search `total` counts only current page (`main.py:168`) — use a COUNT(*) of the search query; before M2, document/enforce the "all timestamps UTC `+00:00` ISO" invariant next to `PUBLIC_PREDICATE` (`db.py:17`); migrate off deprecated `@app.on_event` + add a real migration story for M2.
  - Frontend: add pagination / "load more" UI (`_listings.html`) — pages 2+ currently unreachable; tighten `tel:` href to clean digits (`_contact_value.html`).

## food-compare — local UAE delivery price comparison CLI
- **State:** Shipped. Added a **unified fee-breakdown schema** (delivery/packing/service/small-order as explicit fields) shared by estimate mode now + exact-total mode later; TOTAL flags as an estimate when fees are unknown. Added `benchmark.py`, a parser-rot guard that re-prices real saved order pages against true checkout totals. On GitHub (commit f0bcb16).
- **Next (user):** the benchmark has **no fixtures yet** — save a real Talabat order page + its true checkout total into `fixtures/fixtures.json` to arm the guard.

## beanbuds — personal specialty-coffee tracking app
- **State:** 📐 Design. Named & scaffolded 2026-07-24; GM prior-art research + "log a brew" mockup done; **architect blueprint complete** (`beanbuds/ARCHITECTURE.md`).
- **Location:** `beanbuds/` (README + ARCHITECTURE committed)
- **Idea:** log beans + brew method + milk + tasting notes; chart preferences; compare roaster's stated flavor profile vs. what the user actually tastes, sliced by method (French press vs. De'Longhi Magnifica). Mobile-first, offline, must look nice.
- **Stack (decided):** PWA — React + Vite + TS, Tailwind, IndexedDB via Dexie, Recharts, Workbox. No backend/accounts/sync in v1 (reversible to Capacitor later). Method-aware brews = discriminated union keyed on `method` + method registry. Roaster-vs-me = set math on a shared curated flavor taxonomy (~24 terms under 8 SCA families).
- **v1 scope:** scaffold → beans CRUD → method-aware brew screen → structured tasting + roaster-vs-me strip → charts → backup (export/import + persistent storage). Bag-scan, full wheel, sync = v2.
- **Next (user):** review blueprint + answer 5 open Qs (sync vs. single-phone, units, bitterness slider, 24-term flavor list, milk enum), then build v1.

## helthi — personal fitness-data consolidator (Whoop + Hevy + Samsung Health)
- **State:** 📐 Design. Named & scaffolded 2026-07-31. GitScout prior-art + architect blueprint both done (`helthi/README.md`, `PRIOR-ART.md`, `ARCHITECTURE.md`).
- **Location:** `helthi/` (not yet committed)
- **Scope (locked):** 1 API source (Whoop OAuth) + 2 file-drop sources (Hevy CSV — no Pro; Samsung CSV). SQLite core + Streamlit dashboard. Four insights: recovery-vs-load · sleep→next-day performance · HR zones/workout · long-term trends.
- **Design:** Python 3.12 + stdlib sqlite3 + httpx + watchdog; Streamlit view. Three-layer model: raw landing tables → unified core (`day`/`session`/`session_hr_zone`) → derived joins. Heart of it is the time-alignment layer (three time formats → canonical UTC; wake-date "day" rule; HR-onto-session overlap). Rebuildable from raw.
- **Borrow kit:** hedgertronic/whoop (OAuth v2), sandseb123/Leo-Health-Core (ingestion arch), remuzel/hevy-api (Hevy schema), drkostas/hevy2garmin (HR overlay), davidmosiah/samsung-health-mcp (Samsung format check).
- **Phasing:** P0 scaffold/schema → P1 Whoop end-to-end (useful spine) → P2 Hevy CSV → P3 Samsung → P4 cross-source HR join → P5 polish.
- **Blocking on user:** (1) confirm home tz (Asia/Dubai?) + HR-zone model; (2) real Samsung Health export sample (gates Phase 3 parser).

## Stash — content-searchable home for Instagram saves
- **State:** 📐 Design. Scaffolded 2026-08-01; GitScout prior-art + architect blueprint both done (`stash/README.md`, `ARCHITECTURE.md`).
- **Location:** `stash/`
- **Idea:** hundreds/thousands of IG saves (movies, songs, workouts, Dubai food, travel, anime) → make each **findable by content** (never re-watch a reel). Search "anime" → titled, summarized cards; plus "what should I watch next" recommendations.
- **Design (locked by architect):** one local Python service (FastAPI + SQLite/`sqlite-vec`) on the M4 + thin React/Vite/Tailwind mobile UI; phone reaches Mac over Tailscale. **Two-track ingest:** (A) parse the official DYI JSON export = ban-free/token-free seed (URL+author+collection+date, NO captions); (B) throttled, resumable enricher hitting IG's private mobile JSON endpoints with the user's own cookies to fill caption/thumbnail. **Cascade-gated enrichment:** caption → whisper.cpp (local/free) → Apple Vision OCR (local/free) → ONE cached Claude call per post. All heavy compute on-device; only token spend is the batched structuring call, cached forever by shortcode. Search + recommend fully local (sqlite-vec + FTS5).
- **Rate/ban mitigation:** instaloader's sliding-window limits hard-coded; jittered sleep; checkpoint/resume; hard-stop → "re-auth needed" on any IG challenge. App stays fully useful on the ban-free seed alone.
- **Phasing:** 1a DYI parse + searchable app ($0, no API risk) → 1b caption enrichment via private API (real unlock, still $0) → 1c transcript/OCR for thin-caption reels → 2 semantic search + recommendations + the one LLM call.
- **Blocking on user:** (1) request the IG export (JSON, "Saved" only, All time) — the seed list; (2) confirm 2 decisions: phone-access method (default Tailscale) + enrich strategy (lazy per-collection vs. backfill-all).

---

## Team & infrastructure
- **GM (main chat):** coordination, ideation, git/versioning/pushes (held until user says go).
- **Agents (user-level, all projects):** `gitscout` (prior-art research) · `architect` (blueprints) · `frontend` · `backend` · `reviewer` (read-only QA).
- **Not hired yet (by design):** Analyst (for on-demand business/data analysis once there's data) · DevOps/Release · Growth. Add when volume justifies.
- **Tooling:** `gh` v2.95 installed + authed (danishandhera) · Node v24 LTS + `~/.local/bin` binaries (arm64) · agent permissions widened for unattended runs.
- **Hardware:** M4 MacBook Air 16GB (good fit; workload is cloud-brained + light-local).

---

## Open decisions awaiting user
1. firsttimemoms: Arab/GCC as own segment card vs. religious-support filter.
2. firsttimemoms: first shop products to add.
3. firsttimemoms: WhatsApp business number (real number vs. "contact directly" link).
4. Sell Local: proceed with Frontend styling + Reviewer finish now?
5. DubaiWatchExchange: final list of Dubai classifieds subs to monitor (gates Phase 2 build).

## DubaiWatchExchange — UAE watch buy/sell/trade subreddit (r/DubaiWatchExchange)
- **State:** Sub is live but empty; the US-heavy r/watchexchange localised for UAE. Phase 1 content authored (rules, AutoMod, flairs+reputation, wiki x8, sidebar, removal reasons, pinned posts, brand assets). **Ready to paste into Reddit.**
- **Location:** `dubaiwatchexchange/` · content in `reddit/`, go-live checklist in `README.md`
- **Decisions (2026-08-19):** AutoMod-first (no hosting); grow via monitor + manual invite (ToS-safe — no auto-repost/auto-DM); AutoMod thresholds kept at <21d / <50 karma → held for review.
- **Brand:** pastel desert-oasis — soft green `#7FA968` on brown `#402D1D`; `icon.svg` + `banner.svg` in `reddit/assets/` (export to PNG before upload).
- **Next (user):** run the GO-LIVE checklist (~30–45 min), post/pin the two threads in `reddit/pinned-posts.md`, seed 2–3 real listings, then test AutoMod.
- **Phase 2 (designed, not built):** classifieds monitor → manual invite (`monitor/PLAN.md`); Claude reputation bot + scam-triage.
