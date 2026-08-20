# DubaiWatchExchange

Tooling + content to run **r/DubaiWatchExchange** — the UAE's watch buy/sell/trade subreddit.

**Approach (decided 2026-08-19):** AutoMod-first (zero hosting), grow via **monitor + manual invite** (ToS-safe), add a Claude-powered bot in Phase 2.

## What's here
```
reddit/
  RULES.md                 # official ruleset (paste into Mod Tools → Rules)
  automod.yaml             # AutoModerator config (paste into wiki/config/automoderator)
  flairs.md                # post + user (reputation) flairs
  community-appearance.md  # description, sidebar, widgets, visual assets
  removal-reasons.md       # one-click removal reasons
  pinned-posts.md          # welcome/start-here + monthly confirmation thread
  assets/                  # icon.svg, banner.svg (desert-oasis palette) + export guide
  wiki/                    # all wiki pages (index, how-to-sell/buy, scam-prevention,
                           #   reputation, timestamps, authenticity-uae, faq)
monitor/
  PLAN.md                  # Phase 2: watch classifieds subs → surface posts for manual invite
```

## GO-LIVE checklist (do these in the sub, ~30–45 min)
_Progress as of 2026-08-20: sub created, images + colours done. Everything below is still open._

**Do the wiki before AutoMod** — AutoMod's auto-comments link to `/wiki/timestamps` and `/wiki/scam-prevention`, so those pages should exist first or the links 404 on your very first post.
- [ ] **Rules:** Mod Tools → Rules → add the 12 rules from `reddit/RULES.md`.
- [ ] **AutoMod:** open `https://www.reddit.com/r/dubaiwatchexchange/wiki/config/automoderator`, paste `reddit/automod.yaml`, save.
- [ ] **Post flair:** create the templates in `reddit/flairs.md` (allow user assignment on WTS/WTB/WTT/WTI/Discussion).
- [ ] **User flair:** create the reputation templates; enable user flair.
- [ ] **Wiki:** create each page under `reddit/wiki/` at the matching URL (`/wiki/rules`, `/wiki/how-to-sell`, …). Set wiki to mod-edit only.
- [x] **Colours:** base `#E7D5B8` (sand), highlight `#7FA968`. ~~`#402D1D`~~ was the pre-2026-08-20 dark base.
- [x] **Assets:** icon + desktop/mobile banners uploaded.
- [ ] **Appearance (text):** still to do — community description + sidebar/widgets from `reddit/community-appearance.md`.
- [ ] **Removal reasons:** add the ones in `reddit/removal-reasons.md`.
- [ ] **Seed content:** post & pin the two threads in `reddit/pinned-posts.md` (Welcome + Monthly Confirmation); add 2–3 of your own real listings so it's not empty.
- [ ] **Test:** make a throwaway `[WTS]` post with no tag / no price to confirm AutoMod removes and comments correctly.

## Phase 2 (after it's live and has a heartbeat)
- Monitor tool for Dubai classifieds subs → surfaces watch posts to you for manual, respectful cross-list invites (see `monitor/PLAN.md`).
- Claude reputation bot (auto transaction-flair) + scam-triage assistant.
- Banner + icon via the design skill.
