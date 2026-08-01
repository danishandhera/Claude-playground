# Portfolio Status

_Living dashboard of all projects, maintained by the GM. Ask "where are we?" anytime._

**Last updated:** 2026-08-01

Legend — Phase: 💡 idea · 📐 design · 🔨 building · 🧪 validating · 🚢 shipped · ⏸ paused

---

## At a glance

| Project | Phase | Next action | Owner | Blocker |
|---|---|---|---|---|
| **firsttimemoms** | 🔨 → 🧪 | Focus group + onboard 2–3 real caregivers | **User** | Real caregiver supply (none yet) |
| **Sell Local** | 🚢 (M0/M1) | Decide M2 (paste-ad intake + LLM parse + approval queue) | Team/User | None |
| **food-compare** | 🚢 | Add real fixtures to arm the benchmark guard | User | None |
| **dubizzle-tool** | 🚢 | — (built; local listing filter) | — | None |
| **beanbuds** | 💡 | Architect blueprint, then "log a brew" screen mockup | Team/User | None |
| **Stash** | 💡 | User requests IG data export (JSON, Saved-only, All time) | **User** | Waiting on export file |
| **helthi** | 💡 → 📐 | Confirm tz + HR-zone model; then Phase 0/1 build (Whoop spine) | Team/User | Samsung export sample (gates Phase 3) |

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
- **State:** 💡 Idea, named & scaffolded 2026-07-24. GM prior-art research done (see `beanbuds/README.md`).
- **Location:** `beanbuds/` (not yet committed)
- **Idea:** log beans + brew method + milk + tasting notes; chart preferences; compare roaster's stated flavor profile vs. what the user actually tastes, sliced by method (French press vs. De'Longhi Magnifica). Mobile-first, offline, must look nice.
- **Prior art verdict:** mature space — borrow proven design (Beanconqueror = best fork/reference, Ionic/Capacitor one-codebase→web+Android); build fresh for the roaster-vs-me charting gap. Steal: method-aware brew forms, SCA flavor wheel vocab, LLM bag-scanning.
- **Leaning stack:** PWA or Capacitor/Ionic, offline-first, local storage (architect to confirm).
- **Next:** architect blueprint → "log a brew" screen mockup for user reaction.

## helthi — personal fitness-data consolidator (Whoop + Hevy + Samsung Health)
- **State:** 📐 Design. Named & scaffolded 2026-07-31. GitScout prior-art + architect blueprint both done (`helthi/README.md`, `PRIOR-ART.md`, `ARCHITECTURE.md`).
- **Location:** `helthi/` (not yet committed)
- **Scope (locked):** 1 API source (Whoop OAuth) + 2 file-drop sources (Hevy CSV — no Pro; Samsung CSV). SQLite core + Streamlit dashboard. Four insights: recovery-vs-load · sleep→next-day performance · HR zones/workout · long-term trends.
- **Design:** Python 3.12 + stdlib sqlite3 + httpx + watchdog; Streamlit view. Three-layer model: raw landing tables → unified core (`day`/`session`/`session_hr_zone`) → derived joins. Heart of it is the time-alignment layer (three time formats → canonical UTC; wake-date "day" rule; HR-onto-session overlap). Rebuildable from raw.
- **Borrow kit:** hedgertronic/whoop (OAuth v2), sandseb123/Leo-Health-Core (ingestion arch), remuzel/hevy-api (Hevy schema), drkostas/hevy2garmin (HR overlay), davidmosiah/samsung-health-mcp (Samsung format check).
- **Phasing:** P0 scaffold/schema → P1 Whoop end-to-end (useful spine) → P2 Hevy CSV → P3 Samsung → P4 cross-source HR join → P5 polish.
- **Blocking on user:** (1) confirm home tz (Asia/Dubai?) + HR-zone model; (2) real Samsung Health export sample (gates Phase 3 parser).

## Stash — searchable home for Instagram saves
- **State:** 💡 Scaffolded 2026-08-01. Name chosen; Phase-1-first; delivered as a **mobile web app**.
- **Location:** `stash/` (see `stash/README.md`)
- **Idea:** hundreds/thousands of IG saves (movies, songs, workouts, Dubai food, travel, anime) → parse the official "Download Your Information" JSON export → searchable/filterable app over existing collections. Phase 2 (later): enrich captions via `instaloader` + LLM tagging for summaries/recommendations ("what anime to watch next").
- **Critical path:** blocked on **user requesting the IG export** (JSON, "Saved" only, All time). Parser built once we have a real sample schema.
- **Next (team):** GitScout prior-art on IG-export parsers / saved-post browsers; then architect Phase-1 blueprint.

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
