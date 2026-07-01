# Sell Local

A web-based aggregator for peer-to-peer ("for sale") ads from Dubai community WhatsApp groups — so members can browse listings on a clean page instead of scrolling endless chat.

## The idea

Many Dubai communities run WhatsApp groups for P2P selling. Those groups already have **liquidity** (active buyers + sellers) but are a poor browsing experience. Sell Local aggregates those ads into a simple site: pick your community → see current listings with post/expiry dates → search.

**Core insight / moat:** piggyback on liquidity that already exists in WhatsApp groups instead of cold-starting a marketplace from zero.

## Strategic priorities

1. **Intake friction is the whole product.** The "simplify" promise dies if a human retypes WhatsApp posts. Listings must get in with near-zero manual effort.
2. **Trust & safety from day one.** Public, user-submitted content needs a lightweight approval queue — not a phase-2 afterthought — to keep out spam/scams.
3. **Validate adoption before building wide.** Prove one community will use this *instead of* their existing WhatsApp group before scaling.

## Plan

### Phase 1 — Core product (build first)
- Community picker (landing page)
- Ad listing per community: title, description, price, post date, expiry date, auto-flag/auto-hide expired
- Basic text search over title/description
- **Intake:** "paste your ad" web form → **LLM parses** messy text into structured fields → **approval queue** → publish
- Backend: lightweight DB (SQLite is plenty at this scale)
- Goal: validate that a real community adopts it

### Phase 2 — WhatsApp intake channel
- Dedicated WhatsApp Business number as the intake inbox
- Meta WhatsApp Cloud API (official, webhook-based — NOT group scraping, which risks bans/ToS)
- Same LLM parsing + approval pipeline, fed from WhatsApp messages (incl. item photos via media)
- Gated on Meta business verification (tie to IFZA licensing)

### Explicitly avoided
- Scraping personal/community WhatsApp groups — number-ban + ToS risk.

## Prior art (GitScout, 2026-06-30)

**Verdict:** don't fork a heavyweight classifieds CMS (Osclass/Yclas/OpenClassify) — build a thin custom app and steal patterns piecemeal.

Steal from:
- **[slyapustin/django-classified](https://github.com/slyapustin/django-classified)** — listing/category data model, image attach, filter-based search, and built-in ad **expiration** pattern (default ~30 days).
- **[hootlex/laravel-moderation](https://github.com/hootlex/laravel-moderation)** (MIT) — the approval-queue state machine: `status` (pending/approved/rejected/postponed) + `moderated_by` + `moderated_at`, with default queries returning only approved rows. Copy the schema/semantics, not the PHP.
- **[Secreto31126/whatsapp-api-js](https://github.com/Secreto31126/whatsapp-api-js)** (MIT) or **[official WhatsApp Node SDK](https://github.com/WhatsApp/WhatsApp-Nodejs-SDK)** — Phase 2 webhook intake; do NOT hand-roll `X-Hub-Signature-256` verification.
- LLM parsing: use provider-native structured output (JSON schema / tool-use) with a Pydantic/Zod model; no parsing library needed.

**Suggested data model (framework-agnostic):**
- `Community` (id, name, slug) — the picker is just a filter.
- `Listing` (id, community_id, title, description, price, currency, contact, created_at, **expires_at**, **status**, moderated_by, moderated_at, **source** ['web_form'|'whatsapp'], **raw_text**, image_url).
  - Keep `raw_text` (original message) for re-parsing/audit. `source` lets one pipeline serve both intake channels.
  - "Auto-hide expired" = query filter `expires_at > now()`, never a delete (preserve history).
  - Default every public read to `status='approved' AND expires_at > now()`; new listings land `pending`.
- **Search:** SQLite **FTS5** over title+description is plenty — no Elasticsearch.

**Watch-outs:**
- WhatsApp media URLs expire in ~5 min — download-and-store on receipt. Verify webhook signature before parsing.
- Phase 2 gated on Meta Business verification (weeks, tie to IFZA license).
- Listings carry phone numbers → decide public vs. gated contact now (PII / UAE expectations).
- Confirm django-classified's LICENSE before copying code verbatim (pattern-borrowing is fine).

## Status
- 2026-06-30: Named, scaffolded, prior-art researched. Concept + data model direction set; no code yet.

## Next steps (open)
- [x] GitScout: prior-art research — done (see above)
- [ ] Architect: turn the above into ARCHITECTURE.md (stack decision, schema, API, phased plan)
- [ ] Build prototype: community picker + listing + search + paste-ad form (with LLM parse + approval queue)
