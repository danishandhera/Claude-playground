# Flairs — Post & User

## Post flairs
Set in Mod Tools → Post Flair. Enable "Allow users to assign" for the item-type ones so posters can self-select, keep SOLD/PSA mod-only where noted. Suggested colours in brackets.

| Text | Who sets it | Notes |
|---|---|---|
| **WTS — Want to Sell** (green) | user | Pair with `[WTS]` title tag |
| **WTB — Want to Buy** (blue) | user | Pair with `[WTB]` |
| **WTT — Want to Trade** (purple) | user | Pair with `[WTT]` |
| **WTI — Info / Opinion** (grey) | user | IDs, valuations, "should I buy?" |
| **SOLD** (dark grey) | auto/mod | Set by AutoMod when OP says "sold" |
| **PSA / Scam Alert** (red) | mod only | Verified warnings only |
| **Discussion** (teal) | user | Market chat, meetups, no listing |
| **Meta** (orange) | mod | Sub announcements |

## User flairs — reputation
The core trust signal. Text is the confirmed transaction count; the number is bumped by the reputation process (see `wiki/reputation.md`). Start everyone unflaired.

| Flair text | Meaning |
|---|---|
| `+1 Transaction` … `+N Transactions` | Confirmed completed deals on this sub |
| `Dealer` (+ count) | Self-identified business/reseller (Rule 9) |
| `Verified Meetup ✓` | Optional badge for members who've done a mod-witnessed or well-documented in-person deal |
| `Mod` | Moderators |

**CSS classes** (for later styling / the reputation bot): `trans-1`, `trans-2`, … `dealer`, `verified`, `mod`.

## Flair templates to pre-create (copy-paste text)
Post flair: `WTS`, `WTB`, `WTT`, `WTI`, `SOLD`, `PSA`, `Discussion`, `Meta`
User flair: `+1 Transaction`, `+2 Transactions`, `+3 Transactions`, `+5 Transactions`, `+10 Transactions`, `Dealer`, `Verified Meetup ✓`
(The bot in Phase 2 will generate exact counts automatically; these are seeds so the field exists.)
