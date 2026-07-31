# beanbuds

A personal specialty-coffee tracking app for a home brewer — log what beans you bought, how you brewed them, and what you actually tasted, then chart your preferences over time.

## The idea

Specialty coffee bags come with a stated flavor profile, but what you taste when *you* brew it — on a French press one day, a De'Longhi Magnifica the next — is often different. beanbuds captures both sides and the brew method in between, so you can:

- Track beans (roaster, origin, process, roast level, price, the bag's stated notes).
- Log each brew with **method-specific** parameters (French press vs. Magnifica are different forms).
- Record how it actually tasted using a **structured flavor vocabulary** (SCA flavor wheel) + a rating.
- **Chart your preferences over time** and see the gap between the roaster's notes and your palate.

Mobile-first (used at the counter, one-handed, offline). Must look nice and be comfortable to use.

## Core insight / motivation

The value is in the **delta**: roaster's stated profile vs. what the user actually tastes, sliced by brew method. No open-source app nails this comparison + charting — that's the wedge.

## Strategic priorities

1. **Logging friction is the whole product.** Capturing a brew must be fast, one-handed, and work offline. If it's tedious, it won't get used.
2. **Structured tasting data, not free text.** Free notes can't be charted. A fixed flavor taxonomy (SCA wheel) + sliders + rating is what makes trends possible.
3. **Method-aware brews.** French press and the Magnifica need different fields; one bean → many brews → each with its own method parameters.

## Requirements (from user)

- Runs on phone: **web app (PWA) or Android** — one phone, personal use.
- Looks nice / comfortable to use.
- Tracks: beans bought · brew method · milk (yes/no + type) · how it tasted · flavor profiles tasted.
- Handles multiple brew methods with different parameters (French press, De'Longhi Magnifica).
- Compare tasted profile vs. the bag's stated profile.

## Data model (draft, distilled from prior art)

- **Bean/Bag:** roaster, origin, process, roast level, roast date, price, weight, *roaster's stated flavor notes*, photo.
- **Brew:** linked bean, method (French press / Magnifica / …), grind size/setting, dose (g), water (g or ratio), temp, brew time, milk? (type/amount). *Method determines which fields show.*
- **Tasting:** rating, flavor-wheel tags (structured), acidity/body/sweetness sliders, free notes, photo.

## Prior art (GM research, 2026-07-24)

**Verdict:** the space is mature — borrow proven design, build fresh for the roaster-vs-me charting gap. Optionally fork Beanconqueror as a head start.

**Open source:**
- [Beanconqueror](https://github.com/graphefruit/Beanconqueror) — gold standard. Ionic/Angular/Capacitor (one codebase → web + Android), offline-first, most mature data model. Best fork/reference candidate.
- [B{rew}log](https://github.com/jnsgruk/brewlog) — self-hosted Rust/SQLite web app. Notable: **LLM "bag scanning"** (photo → auto-fill bean). Mostly written by Claude.
- [CafedentialApp](https://github.com/whiteSHADOW1234/CafedentialApp) — Flutter, SCA cupping-protocol scoring UI reference.
- [Coffee-Ratio](https://github.com/johnmahlon/Coffee-Ratio) — simple ratio calculator + brew timer.

**Commercial (design/feature inspiration):**
- [Beanwise](https://play.google.com/store/apps/details?id=app.beanwise) — separate parameter sets per brew method (matches the French-press-vs-Magnifica need).
- [BeanBook](https://beanbook.app/) — compares *your* tasting notes vs. the roaster's notes (our exact motivation).
- [Siip](https://www.siip.coffee/) — "Vivino for coffee," 30k+ coffee index, scan-a-bag.
- [iBrewCoffee](https://ibrew.coffee/), [Brewfolio](https://brewfolio.app/) — polished journals; label-scan auto-fill.

**Ideas worth stealing:**
1. Method-aware brew forms (Beanwise/Beanconqueror).
2. Roaster-notes vs. my-notes comparison + charting the delta (BeanBook, extended).
3. [SCA Flavor Wheel](https://notbadcoffee.com/flavor-wheel-en/) as the tasting vocabulary → enables charting.
4. LLM bag scanning to auto-fill beans (B{rew}log/Brewfolio) — strong fit given available tooling.
5. Offline-first, data-on-device.

## Leaning stack

**PWA or Capacitor/Ionic** — one codebase, installable on Android, runs in browser, offline-first with local storage. Mirrors Beanconqueror's proven approach. Final call: architect.

## Status

💡 **Idea — named & scaffolded 2026-07-24.** Next: architect blueprint (stack, data model, phased plan), then a "log a brew" screen mockup for the user to react to.
