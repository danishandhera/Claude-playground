# Missed Call

_Name provisional (2026-08-15)._

A light, personal Android app that reminds you to stay in touch with the people who matter — by turning "I haven't spoken to them in ages" from a vague guilt into a specific, timely nudge.

## The idea

Pick people from your phonebook, set how often you want to reach each one (Mom every 3 weeks, a uni friend every 3 months), and let the phone do the remembering. Once a day it quietly checks your **call log**, finds the last time you actually called each tracked person, and if that's older than their cadence it nudges you: *"You haven't called Dad in 5 weeks."* Tap to call them, or snooze.

The name is the whole thesis: it flips the annoyance of a missed call into the point of the product.

## Core insight / motivation

The user is bad at keeping in touch — not from not caring, but from **no ambient signal that time has passed**. The value is closing that loop automatically: the app watches the call log so the user doesn't have to track anything manually. The "magic" is auto-detection, not another to-do list to maintain.

## Strategic priorities

1. **Auto-detection is the wedge.** Reading the real call log (vs. asking the user to log calls) is what makes this effortless. A manual-reset relationship-reminder app already exists a hundred times over; the call-log tie-in is the reason to build.
2. **Zero-friction, zero-maintenance.** No account, no server, no cloud. Everything on-device. If it needs tending, it dies.
3. **Nudge quality over quantity.** One calm, correct notification a day beats a noisy stream. Snooze + "call now" must be one tap.

## Decided constraints (2026-08-15)

- **Platform:** Android only (user carries Android). This is deliberate — iOS gives apps *zero* call-log access, so the core feature is impossible there.
- **Stack:** Native **Kotlin + Jetpack Compose**. Call-log/contacts access is first-class in native; no plugin layer needed.
- **Storage:** **Room** for the tracked list + per-person cadence. **WorkManager** for the daily background check. Native `NotificationManager` for nudges.
- **Distribution:** **Sideload** onto the user's own phone (build APK on the M4 Air, install over USB). Google Play won't approve `READ_CALL_LOG` for a non-dialer app, but that restriction only applies to public distribution — personal use is fine.

## Known gotchas (flagged early, none fatal)

- **Number matching:** call log stores raw numbers, contacts store their own format → normalize both to E.164 so a contact matches their calls.
- **Battery optimization** can delay WorkManager, but a once-a-day nudge tolerates that fine — no real-time requirement.
- **Runtime permissions:** `READ_CONTACTS`, `READ_CALL_LOG`, and (Android 13+) `POST_NOTIFICATIONS`, all granted once on first launch.
- **Local toolchain:** needs the Android SDK on the Mac to build/sign the APK — the one bit of heavier local setup.

## Prior art (GitScout, 2026-08-15)

**Verdict: build it, borrow the two risky parts.** No open-source app combines contacts + call log + cadence reminders — the keep-in-touch apps (Monica, Clay, Garden, Dex) are all manual-log or email/LinkedIn-pull; **none nudge from phone-call frequency**. The auto-detection is a real gap. We're assembling two solved primitives, not cloning a product.

**Borrow #1 — call-log query + number matching** (study, don't copy — it's GPL-3.0): [FossifyOrg/Phone `RecentsHelper.kt`](https://github.com/FossifyOrg/Phone/blob/master/app/src/main/kotlin/org/fossify/phone/helpers/RecentsHelper.kt).
- **Match numbers by comparing the last 9 digits**, not full-string equality — sidesteps country-code/formatting mismatches. (Their `COMPARABLE_PHONE_NUMBER_LENGTH = 9`.) This is the single most important trick; the naive E.164 approach in our earlier notes is fragile by comparison.
- **Android-version split is load-bearing:** on Nougat+ pass the row limit via `Calls.LIMIT_PARAM_KEY` (a Google bug broke `LIMIT` in the sort-order string); pre-Nougat append `LIMIT n`. Getting this wrong silently returns wrong rows.
- Handle blocked/withheld numbers via `NUMBER_PRESENTATION`, the `"-1"` sentinel, and null/blank numbers. Resolve current name from `ContactsContract` at display time — the call log's `CACHED_NAME` goes stale.
- **Decide what counts as "contact made":** filter `Calls.TYPE` — an outgoing call clearly counts; a missed spam call shouldn't reset the timer.

**Borrow #2 — cadence data model** (reference only, no license file): [kirillsmirnov1/Friends-reminder-android](https://github.com/kirillsmirnov1/Friends-reminder-android).
- Store the **contact lookup key**, not a raw contact ID (IDs churn, lookup keys are stable).
- **Derive** `lastContactedTS` from the call log at job time — no need to persist an interaction history table.
- Overdue rule: `now − lastContactedTS > cadenceDays ⇒ due`. A fresh call auto-resets the timer (the whole value prop), so **snooze = suppress-notification-until-date, not a data change**.
- Steal a **`notified`/`ready` flag** as the anti-spam mechanism so the daily job doesn't re-fire the same nudge until the cadence resets.

**Architecture reference (permissive, Apache-2.0):** [teobaranga/monica](https://github.com/teobaranga/monica) — clean Compose feature/core Gradle module split.

**Watch-outs:** OEM battery killers (Xiaomi/Samsung/Oppo) can delay WorkManager → may need a whitelist prompt; last-9-digits matching still fails on short codes/extensions/multi-SIM dups (log unmatched rows in testing); `READ_CALL_LOG` being Play-restricted **confirms** the sideload decision.

## Status

💡 **Idea → scoped, prior art in.** Named, scaffolded, GitScout done. Next: architect blueprint (data model + WorkManager flow + screens), then build.
