# Monitor + Manual-Invite tool (Phase 2)

**Goal:** find watch-for-sale posts in Dubai classifieds subs and surface them to *you* so you (or a mod) can send a **respectful, human, low-volume** invite to also list on r/DubaiWatchExchange.

**Explicitly NOT doing:** auto-reposting others' photos/content (ToS violation → sub ban) or auto-commenting/DMing at volume (spam flag). The tool assists a human; it never posts on its own.

## How it works
1. **Poll** target subs' new posts via Reddit's read API (PRAW, read-only, respects rate limits).
   - Candidate subs: r/DubaiPetrolHeads-style classifieds, r/dubai classifieds threads, local buy/sell subs (finalise list before build).
2. **Filter** to watch listings with an LLM/keyword pass: brand names (Rolex, Omega, Seiko, Tudor, Cartier, AP, Patek…), "watch", price signals, WTS intent. Score & dedupe.
3. **Output** a ranked digest (local file or a private modmail-to-self):
   - link, title, detected brand/price, why it matched.
4. **You decide** and send a personal invite in your own words. Optional: the tool drafts a friendly, non-spammy template you copy-paste manually.

## Invite etiquette (keep the sub safe)
- Low volume, genuinely relevant posts only.
- Personal tone, not copy-paste blasts; never repeated to the same user.
- Add value ("we're a UAE-specific watch marketplace with timestamps + rep") — don't denigrate the other sub.
- Stop if any target sub's rules disallow it.

## Build notes
- Python + PRAW; read-only script, runs on demand (cron later once it's live and worth it).
- Reuse patterns from the existing `dubizzle-tool` / `sell-local` intake approach where sensible.
- Needs a Reddit "script" app (client id/secret) on the mod account — set up at go-live time.

_Status: designed, not built. Gated on the sub being live with a heartbeat first._
