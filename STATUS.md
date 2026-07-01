# Portfolio Status

_Living dashboard of all projects, maintained by the GM. Ask "where are we?" anytime._

**Last updated:** 2026-07-01

Legend — Phase: 💡 idea · 📐 design · 🔨 building · 🧪 validating · 🚢 shipped · ⏸ paused

---

## At a glance

| Project | Phase | Next action | Owner | Blocker |
|---|---|---|---|---|
| **firsttimemoms** | 🔨 → 🧪 | Focus group + onboard 2–3 real caregivers | **User** | Real caregiver supply (none yet) |
| **Sell Local** | 🔨 | Frontend styling pass → Reviewer gate → push | Team | None |
| **food-compare** | 🚢 | — (built; local UAE delivery price CLI) | — | None |
| **dubizzle-tool** | 🚢 | — (built; local listing filter) | — | None |

---

## firsttimemoms — UAE/GCC cultural postpartum caregiver marketplace
- **State:** Validated (Reviewer GO) → extracted from Claude prototype into a real Vite + React app. **Builds clean, runs, on GitHub.**
- **Location:** `firsttimemoms/` · pushed to `danishandhera/Claude-playground` (commit 3a6c827)
- **Done:** modular split (theme/scoring/data+hooks/App); priorities wired into matching; budget-bucket bug fixed; Card hoisted; data-loading hooks added.
- **Next (user):** run a focus group; onboard 2–3 real caregivers from UAE mum Facebook groups — this is the real unlock.
- **Next (team, later):** deferred cleanups (hoist `Frame`, accessibility pass); wire real backend/auth/bookings/reviews (dead CTAs are clean seams).
- **Open decisions:** Arab/GCC as its own segment card vs. a religious-support filter · first shop products (mughat + black-seed-honey?) · WhatsApp business number status.

## Sell Local — aggregator for P2P ads from Dubai community WhatsApp groups
- **State:** Backend M0+M1 delivered — FastAPI + SQLite + FTS5 search, seed data, browse/detail/search routes. Runs; 15/15 smoke checks. Functional but unstyled.
- **Location:** `sell-local/` (not yet committed/pushed)
- **Next:** Frontend design pass (Tailwind) → Reviewer security/quality gate → commit + push.
- **Then (M2/M3):** paste-ad intake + LLM parse + approval queue; later Phase 2 WhatsApp Cloud API intake.
- **Confirmed:** stack Python/FastAPI/SQLite/htmx on Fly.io; contacts public in Phase 1 (one-line flip to gated); pin Python 3.12 in a Dockerfile at deploy.

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
