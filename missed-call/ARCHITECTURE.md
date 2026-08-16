# Missed Call — Architecture

_Blueprint v1 (2026-08-15). Reads on top of `README.md` (scope + GitScout prior art). Inherited decisions are locked; this doc turns them into a concrete build plan._

## 1. Goal & constraints (restated)

Build a **personal, single-user, offline Android app** that nudges the user to keep in touch. User tags phonebook contacts with a per-contact cadence; a **daily WorkManager job** reads the device call log, computes the last real contact per tracked person, and fires **one local notification per overdue person**. Tap → dial; or mark caught up; or snooze.

- **Scale:** one user, one device. Dozens of tracked contacts, not thousands. Call log is typically a few thousand rows.
- **Non-goals:** no server, no account, no cloud sync, no analytics, no Play Store, no iOS, no SMS/WhatsApp signal (call log only, v1).
- **Must-haves:** auto-detection from the call log (the wedge), zero maintenance, calm single daily nudge, one-tap call / caught-up / snooze. A manual "Caught up" reset covers connections the call log can't see (IRL, text, other apps).
- **Stack (locked):** Kotlin + Jetpack Compose, Room, WorkManager, native `NotificationManager`. Sideloaded APK.

**Ambiguity flagged, assumption stated:** "how often" is stored in **days** internally (cadence UI can present weeks/months as sugar). Cadence comparison is date-granular, not clock-granular — see §4.

## 2. Module / project shape

Single Gradle module is fine for a solo sideloaded app — don't over-modularize (Monica's multi-module split is overkill here; borrow its Compose conventions only). Package structure:

```
com.missedcall
├── data
│   ├── db          Room: entities, DAOs, database
│   └── calllog     CallLogRepository (raw query + matching)
├── domain          OverdueCalculator (pure, testable)
├── work            DailyCheckWorker, WorkScheduler, BootReceiver
├── notify          Notifier (channel, build 3 actions), CallActionReceiver (caught-up + snooze)
├── ui
│   ├── list        TrackedListScreen + VM
│   ├── add         AddContactScreen (contact picker)
│   └── edit        CadenceEditScreen + VM
└── MainActivity, App
```

Keep `OverdueCalculator` a pure function (no Android deps) so the risky overdue logic is unit-testable on the JVM.

## 3. Room data model

**One entity carries everything.** Because we *derive* `lastContactedTS` from the call log at job time (never persist interaction history), the table only holds: who to track, how often, and transient notification state.

### `TrackedContact`

```kotlin
@Entity(tableName = "tracked_contact")
data class TrackedContact(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,

    // WHY lookup key, not contact _ID: raw contact IDs churn on sync/merge/restore;
    // the lookup key (ContactsContract.Contacts.LOOKUP_KEY) survives those. We resolve
    // the current display name + numbers from ContactsContract at read time.
    val lookupKey: String,

    // Snapshot at add-time, for display + as a fallback if the contact is later deleted.
    val displayName: String,

    // Denormalized number snapshot (comma-joined last-9-digit keys) captured at add-time,
    // refreshed on each daily run. Lets the call-log matcher work without a live contacts
    // read on every job, and degrades gracefully if READ_CONTACTS is later revoked.
    val numberKeys: String,          // e.g. "551234567,505551212"

    val cadenceDays: Int,            // canonical unit is days

    // Manual "Caught up ✓" timestamp. Set to now() when the user marks they've connected
    // by some off-call-log means (IRL, text, WhatsApp/other-app call). THE ONE deliberate
    // exception to "derive, don't log" — see §3 note below. Null = never manually caught up.
    val manualLastContactedTS: Long? = null,

    // --- transient notification state (not relationship data) ---
    // Suppress notifications until this instant. Snooze sets it; null = not snoozed.
    val snoozeUntil: Long? = null,

    // Anti-spam: the lastContactedTS value that we last notified about. If the current
    // computed lastContactedTS is unchanged AND we already notified, don't re-nag.
    // Null = never notified for the current overdue episode.
    val notifiedForLastContactTS: Long? = null,

    val createdAt: Long = System.currentTimeMillis(),
)
```

**Why the `notifiedForLastContactTS` design (vs a plain boolean `notified`):** a boolean needs an explicit reset event. By keying the "already notified" state to the `lastContactedTS` value we notified about, the flag **auto-resets for free** the moment a new call appears (new call → new `lastContactedTS` → mismatch → eligible to notify again). This matches the README's "derive, don't log" principle: the call log is the source of truth, the flag is just a dedupe cursor.

**The one deliberate exception to "derive, don't log": `manualLastContactedTS`.** The call log is blind to IRL meetings, texts, and WhatsApp/other-app calls, so we let the user manually assert "I connected with them." This is stored, not derived — but it's safe and stays true to the principle:

- It's a **single scalar timestamp per contact**, not an interaction-history table. There's still no log of individual events, no rows to accumulate.
- The overdue rule simply widens its "last contact" input to `max(lastCallTS, manualLastContactedTS)` (§5.4). The call log remains the primary source; the manual stamp only ever *pushes the clock forward*, never rewrites history.
- A subsequent real call still auto-resets everything via the newer `lastCallTS` (which will exceed the manual stamp), so the manual value never "sticks" incorrectly. It's the same self-healing behavior, just seeded from one extra input.

**No history table needed.** Snooze, notified state, and the single manual stamp all live on the row. There is deliberately **no interaction/history table** — the call log *is* the history. If we later want a "who's overdue" dashboard cache, that's a view over this table + a live computation, not new storage.

### DAO sketch

```kotlin
@Dao interface TrackedContactDao {
    @Query("SELECT * FROM tracked_contact ORDER BY displayName")
    fun observeAll(): Flow<List<TrackedContact>>          // UI

    @Query("SELECT * FROM tracked_contact")
    suspend fun getAll(): List<TrackedContact>            // worker

    @Upsert suspend fun upsert(c: TrackedContact): Long
    @Delete suspend fun delete(c: TrackedContact)

    @Query("UPDATE tracked_contact SET snoozeUntil = :until WHERE id = :id")
    suspend fun setSnooze(id: Long, until: Long?)

    // "Caught up ✓" — full-cadence reset. Stamps now() and clears the dedupe cursor so the
    // contact starts a fresh cycle. Distinct from setSnooze (which only defers 3 days).
    @Query("UPDATE tracked_contact SET manualLastContactedTS = :ts, notifiedForLastContactTS = NULL WHERE id = :id")
    suspend fun markCaughtUp(id: Long, ts: Long)

    @Query("UPDATE tracked_contact SET notifiedForLastContactTS = :ts WHERE id = :id")
    suspend fun setNotified(id: Long, ts: Long?)

    @Query("UPDATE tracked_contact SET numberKeys = :keys, displayName = :name WHERE id = :id")
    suspend fun refreshContactSnapshot(id: Long, keys: String, name: String)
}
```

## 4. Call-log read layer

This is risk-bearing area #1. Three things must be right: the **number match** (last 9 digits), the **Nougat LIMIT bug**, and **junk-number filtering**.

### 4.1 The query

```kotlin
// Projection — only what we need.
val projection = arrayOf(
    CallLog.Calls.NUMBER,
    CallLog.Calls.DATE,               // epoch millis
    CallLog.Calls.TYPE,               // OUTGOING / INCOMING / MISSED / REJECTED / BLOCKED
    CallLog.Calls.NUMBER_PRESENTATION // ALLOWED / RESTRICTED / UNKNOWN / PAYPHONE
)

// Sort newest first. We only care about the most-recent qualifying call per person,
// so a bounded, newest-first scan is enough — no need to read the whole log.
```

**Nougat LIMIT split (load-bearing — getting it wrong silently returns wrong rows):**

```kotlin
val limit = 500   // scan window; plenty to find recent calls for tracked people
val uri: Uri; val sortOrder: String
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
    // API 24+: LIMIT in the sort-order string is broken (Google bug). Pass via query param.
    uri = CallLog.Calls.CONTENT_URI.buildUpon()
        .appendQueryParameter(CallLog.Calls.LIMIT_PARAM_KEY, limit.toString())
        .build()
    sortOrder = "${CallLog.Calls.DATE} DESC"
} else {
    uri = CallLog.Calls.CONTENT_URI
    sortOrder = "${CallLog.Calls.DATE} DESC LIMIT $limit"
}
val cursor = contentResolver.query(uri, projection, null, null, sortOrder)
```

> Note: 500 is a generous scan window for finding *recent* calls. Edge case: if a tracked person's last call is older than 500 rows ago (very stale), we won't find it and they'll read as "never contacted" → overdue, which is the correct nudge anyway. If false-never turns out to matter, raise the window or add a per-person targeted query later. Defer.

### 4.2 Number matching — last 9 digits (Fossify's trick, re-expressed)

Do **not** do full E.164 string equality. Normalize each side to digits and compare the trailing 9.

```kotlin
const val COMPARABLE_LEN = 9

/** Strip to digits, drop a leading country/trunk prefix by taking the last N. */
fun phoneKey(raw: String?): String? {
    if (raw.isNullOrBlank()) return null
    val digits = raw.filter { it.isDigit() }      // drops +, spaces, dashes, ()
    if (digits.isEmpty()) return null
    return if (digits.length <= COMPARABLE_LEN) digits
           else digits.takeLast(COMPARABLE_LEN)
}
```

Contact numbers get the same `phoneKey()` treatment when we build `numberKeys`. Matching a call row = `phoneKey(callRow.number) in trackedContact.numberKeys`.

**Known failure modes (per README watch-outs — accept, don't fight in v1):** short codes / extensions / multi-SIM duplicates can mis-key. Mitigation: during dev, log every call row whose `phoneKey` doesn't match any tracked contact so we can eyeball false negatives. No runtime handling in v1.

### 4.3 Junk / withheld number filtering

Skip rows that can't be a real, attributable call:

```kotlin
fun isUsableRow(number: String?, presentation: Int): Boolean {
    if (presentation != CallLog.Calls.PRESENTATION_ALLOWED) return false // restricted/unknown/payphone
    if (number.isNullOrBlank()) return false
    if (number.trim() == "-1") return false                              // withheld sentinel
    return true
}
```

Withheld/blocked/unknown callers can never match a tracked contact anyway, so dropping them early is free correctness + speed.

### 4.4 What TYPE counts as "contact made" — LOCKED

**Decided: outgoing + incoming reset the timer; missed & rejected do NOT.** A real conversation counts regardless of who dialed; ignored/spam calls don't falsely reset. Implemented as a fixed set:

```kotlin
val countingTypes = setOf(CallLog.Calls.OUTGOING_TYPE, CallLog.Calls.INCOMING_TYPE)
// row counts only if row.type in countingTypes
```

### 4.5 Output of this layer

```kotlin
// Map from tracked contact id -> most-recent qualifying CALL timestamp (or null = none found).
// Note: this is the call-log signal ONLY. The manual "Caught up" stamp is folded in later,
// in OverdueCalculator (§5.4), not here — this layer stays a pure view of the call log.
suspend fun lastContactMap(tracked: List<TrackedContact>): Map<Long, Long?>
```

Single pass over the (already bounded, newest-first) cursor: for each usable, counting row, resolve its `phoneKey`, and for the first (newest) row that maps to a tracked contact, record its `DATE`. Because the cursor is DATE DESC, the first hit per person is their most-recent call — short-circuit that person.

## 5. Daily check flow

Risk-bearing area #2: making the background job reliable and non-spammy.

### 5.1 Scheduling

```kotlin
// PeriodicWorkRequest, once/day. WorkManager's minimum period is 15 min; we want daily.
val req = PeriodicWorkRequestBuilder<DailyCheckWorker>(24, TimeUnit.HOURS)
    .setInitialDelay(delayUntilNextRunHour(), TimeUnit.MILLISECONDS) // align to notify hour
    .build()
WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
    "daily_check", ExistingPeriodicWorkPolicy.KEEP, req
)
```

- **No network constraint** (fully offline). No charging constraint (nudge must fire regardless).
- `ExistingPeriodicWorkPolicy.KEEP` so re-scheduling on every launch/boot doesn't reset the clock.
- **Notify hour** (default 10:00 local — open decision §8) drives `setInitialDelay`. Battery optimization may drift the actual fire time; acceptable for a daily nudge.

### 5.2 Boot re-enqueue

WorkManager persists across reboot on most devices, but OEM killers are unreliable — re-arm defensively:

```kotlin
// Manifest: RECEIVE_BOOT_COMPLETED permission + receiver for android.intent.action.BOOT_COMPLETED
class BootReceiver : BroadcastReceiver {
    override fun onReceive(ctx, intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) WorkScheduler.ensureScheduled(ctx)
    }
}
```

`ensureScheduled` is the same `enqueueUniquePeriodicWork(..., KEEP, ...)` call — idempotent. Also call it in `App.onCreate()` so a manual launch heals a dropped schedule.

### 5.3 Worker logic

```kotlin
class DailyCheckWorker : CoroutineWorker {
  override suspend fun doWork(): Result {
    val now = System.currentTimeMillis()
    val tracked = dao.getAll()
    // refresh number/name snapshots from ContactsContract if READ_CONTACTS still granted
    refreshSnapshots(tracked)
    val lastMap = callLogRepo.lastContactMap(tracked)

    for (c in tracked) {
        val callLast = lastMap[c.id]                   // null = no qualifying call found
        // Fold in the manual "Caught up" stamp: effective last contact is the more recent
        // of the two signals. This is the single point where the manual value enters.
        val last = maxOfNullable(callLast, c.manualLastContactedTS)
        val overdue = OverdueCalculator.isOverdue(now, last, c.cadenceDays)
        if (!overdue) { dao.setNotified(c.id, null); continue }   // reset dedupe when healthy

        if (isSnoozed(c, now)) continue                // snooze suppresses, no data change
        if (c.notifiedForLastContactTS == last) continue // already nudged for this same episode

        notifier.notifyOverdue(c, last, now)
        dao.setNotified(c.id, last)                    // key dedupe to this effective-last TS
    }
    return Result.success()
  }
}
```

### 5.4 Overdue computation (pure, testable)

```kotlin
object OverdueCalculator {
    // `last` here is the EFFECTIVE last contact = max(callLastTS, manualLastContactedTS),
    // computed by the caller (§5.3). null -> never contacted at all -> overdue.
    fun isOverdue(now: Long, last: Long?, cadenceDays: Int): Boolean {
        if (last == null) return true
        val elapsedDays = (now - last) / MILLIS_PER_DAY
        return elapsedDays > cadenceDays
    }
}

// Null-safe max used to fold call + manual signals. Both null -> null (never contacted).
fun maxOfNullable(a: Long?, b: Long?): Long? = when {
    a == null -> b
    b == null -> a
    else -> maxOf(a, b)
}
```

The Frontend calls `isOverdue` with the same effective-last value (folding in `manualLastContactedTS`) to paint list state, so UI and worker always agree.

### 5.5 Anti-spam, snooze, and "Caught up" semantics (the important bit)

Three distinct reset/suppress mechanisms — keep them straight:

- **Anti-spam** (automatic): `notifiedForLastContactTS == last` means "I already nudged for exactly this overdue episode." Skip. When the user finally connects, a new (call or manual) signal → new effective `last` → mismatch → eligible again next episode. When they become healthy (not overdue) we clear the flag so the *next* episode can notify.
- **Snooze** = "poke me again in 3 days." Write `snoozeUntil = now + snoozeDays`; purely suppresses the notification while `now < snoozeUntil`. **Never** a relationship-data mutation, does **not** touch any last-contact timestamp. The contact is still overdue underneath; snooze just quiets it briefly.
- **Caught up ✓** = "handled, reset the clock a full cycle." Write `manualLastContactedTS = now` (via `dao.markCaughtUp`, which also clears the dedupe cursor). Because overdue = `now − max(callLast, manualLast) > cadenceDays`, stamping `now` makes the contact non-overdue for a **full cadence** (21 days for a 21-day contact, 90 for a 90-day one — NOT a flat 3 days like snooze). A later real call still supersedes it automatically via the newer call timestamp.

Snooze vs Caught up at a glance: snooze defers a *fixed 3 days* and leaves the person overdue; Caught up resets the *full per-contact cadence* and marks them genuinely up to date.

## 6. Notifications

### 6.1 Channel

```kotlin
// One channel, IMPORTANCE_DEFAULT (visible + sound, not intrusive). Created once at App start.
NotificationChannel("nudges", "Keep-in-touch reminders", IMPORTANCE_DEFAULT)
```

### 6.2 The nudge

- Title: `"Time to call ${name}"`; body: `"You haven't called ${name} in ${weeks/days}."` (humanize the elapsed span).
- Content-tap → dialer intent for the contact's primary number.
- **Three actions:** **Call now**, **Caught up ✓**, **Snooze**.

> Android displays up to **3** notification actions, so three fits exactly — no overflow, no layout change needed. If a fourth were ever added it would silently drop, so treat 3 as the ceiling. Keep labels short ("Call", "Caught up", "Snooze") so all three render on narrower devices.

```kotlin
// Call now — go straight to the dialer prefilled (ACTION_DIAL needs no permission;
// ACTION_CALL would but we don't want to auto-place calls). One tap, user hits green.
val dial = Intent(Intent.ACTION_DIAL, Uri.parse("tel:${primaryNumber}"))

// Caught up ✓ — fire CallActionReceiver with ACTION_CAUGHT_UP + contactId. Receiver calls
// dao.markCaughtUp(id, now) (full-cadence reset, §5.5) and cancels the notification.
// Use this when you connected off-call-log (IRL / text / WhatsApp).

// Snooze — fire CallActionReceiver with ACTION_SNOOZE + contactId. Receiver writes
// snoozeUntil = now + 3d and cancels the notification. Defers only, does NOT reset the clock.
```

Both non-call actions are handled by the same `CallActionReceiver` (BroadcastReceiver) keyed on an action string + contact id — off the UI thread, no activity flash. Use a stable notification id per tracked contact (e.g. `c.id.toInt()`) so re-fires replace rather than stack, and either action can cancel by id.

### 6.3 Android 13+ permission

`POST_NOTIFICATIONS` is a runtime permission on API 33+. Requested in the first-run flow (§7). If denied, the app still works but silently — surface a soft banner in the list screen telling the user notifications are off.

## 7. Permissions & first-run flow

Permissions needed:

| Permission | Why | When asked |
|---|---|---|
| `READ_CONTACTS` | resolve names + numbers from lookup key | at add-contact / first run |
| `READ_CALL_LOG` | the entire wedge | first run (before first check) |
| `POST_NOTIFICATIONS` (API 33+) | show nudges | first run |
| `RECEIVE_BOOT_COMPLETED` | re-arm after reboot | install-time (normal, no prompt) |

**First-run flow (a 3-step, skippable-but-nagging intro):**

1. **Why screen** — one sentence on what the app does and that everything stays on the phone. Builds consent context before the system dialogs (permission grant rates jump when you explain first).
2. **Grant permissions** — request `READ_CALL_LOG`, `READ_CONTACTS`, `POST_NOTIFICATIONS` in sequence. Each has a rationale line. If call-log is denied, block with an explainer (app is pointless without it); the others degrade gracefully.
3. **Battery-optimization whitelist prompt** — OEM killers (Xiaomi/Samsung/Oppo/OnePlus) will silently delay/kill WorkManager. Fire `ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` (or route to the OEM autostart settings where available). Frame as "so reminders actually arrive." Make it a soft recommendation, not a hard gate — it can't be re-prompted endlessly.

After first run, schedule the daily worker (`WorkScheduler.ensureScheduled`).

## 8. Product decisions

### 8.1 LOCKED: what counts as "contact made" (resets the timer)

**Decided: outgoing + incoming reset the timer; missed & rejected do NOT.** This models "have we actually been in touch" (a real conversation counts regardless of who dialed) while ignored/spam calls can't falsely reset the clock. Wired as the fixed `countingTypes` set in §4.4. Separately, the manual **"Caught up ✓"** action (§5.5, §6.2) lets the user reset off-call-log contact (IRL / text / WhatsApp) by a full cadence.

### 8.2 Still open (need the user)

- **Default cadence** for a newly added contact. Proposal: **21 days (3 weeks)** — matches the README's "Mom every 3 weeks" anchor. Confirm or set your own default.
- **Notification time-of-day.** Proposal: **10:00 local**. A single daily fire; late-morning avoids both the wake-up rush and late-night. Confirm or pick a time.
- **Snooze length.** Proposal: **3 days** default (single-tap). Do you want a picker (1d / 3d / 1w) or just one fixed snooze? Recommend fixed 3d for v1 simplicity.
- **"Who's overdue" dashboard.** The tracked-list screen already shows per-contact overdue state, which covers this. A separate sorted dashboard is deferrable. Recommend: skip a dedicated dashboard in v1; sort the list by most-overdue-first instead. Confirm.
- **Multiple overdue people = one grouped notification or N separate?** Proposal: **N separate** (one per person) so each carries its own Call/Snooze actions — but cap at, say, 5/day to stay calm, with a "+3 more overdue" summary. Confirm the cap or ask for grouping.

## 9. Phased build plan

Numbered so the build team can execute and hand off between phases. Each phase is a coherent, shippable-to-your-own-phone slice.

**Phase 0 — Scaffold.** Empty Compose app, single module, Room DB with `TrackedContact` + DAO, package skeleton (§2). No UI logic yet. Verify it builds + installs via USB. _(Owner: shared)_

**Phase 1 — Vertical slice (the proof).** Hardcode ONE tracked contact (lookup key + number in code). Build `CallLogRepository` (§4: query + Nougat split + last-9 match + junk filter), `OverdueCalculator` (§4/§5.4), and a bare `Notifier` (§6, no actions yet). A debug button runs the check synchronously and fires a notification if overdue. **This validates the two risky primitives end-to-end before any polish.** _(Owner: Backend)_

**Phase 2 — Real background job.** Wrap Phase 1 in `DailyCheckWorker`, add `WorkScheduler` (§5.1), `BootReceiver` (§5.2), the effective-last fold (`max(callLast, manualLast)`, §5.3), and the anti-spam/notified logic (§5.5). Notification gets all **three** actions — **Call now** + **Caught up ✓** + **Snooze** — via `CallActionReceiver` (§6.2), including the `markCaughtUp` and `setSnooze` DAO paths. _(Owner: Backend)_

**Phase 3 — Contact management UI.** Tracked-list screen (Compose, observes DAO Flow, shows name + last-called/overdue state via `isOverdue` on the effective-last value, sorted most-overdue-first). Each row exposes an in-app **Caught up ✓** action (calls `dao.markCaughtUp`) so the user can reset without waiting for a notification. Add-contact via `ActivityResultContracts.PickContact` → resolve lookup key + numbers from `ContactsContract` → insert. Cadence-edit screen (days, with week/month sugar). Delete. _(Owner: Frontend, against DAO from Phase 0)_

**Phase 4 — First-run & permissions.** The 3-step intro (§7), runtime permission requests, `POST_NOTIFICATIONS`, battery-optimization prompt, and graceful-degradation banners. _(Owner: Frontend)_

**Phase 5 — Polish & field-test.** Humanized elapsed-time copy, notify-hour alignment, snooze length, overdue-count cap, unmatched-call-row logging for tuning the matcher. Install on the real phone and observe for a week. _(Owner: shared)_

**Defer beyond v1:** WhatsApp/SMS signals, per-contact "counts-as" override, export/backup, widget, grouped notifications.

## 10. Risks & mitigations

1. **Number matching false negatives** (short codes, extensions, multi-SIM dupes, foreign formats). Highest-likelihood correctness bug. _Mitigation:_ last-9-digit keying (Fossify-proven) + dev-time logging of every unmatched call row so we catch systematic misses before trusting it. Accept residual edge cases in v1.
2. **OEM battery killers delay/kill the daily job** (Xiaomi/Samsung/Oppo). _Mitigation:_ battery-optimization whitelist prompt (§7), `BOOT_COMPLETED` + on-launch re-arm (idempotent `KEEP`), and the product tolerates drift (a nudge at 11:30 instead of 10:00 is fine). No real-time dependency.
3. **`READ_CALL_LOG` is Play-restricted for non-dialer apps.** Not a build risk — it *confirms* sideload distribution. _Mitigation:_ none needed; documented as the reason we sideload. Don't accidentally try to publish.

## 11. Handoff summary

- **Backend builds:** the call-log read layer (§4 — query, Nougat LIMIT split, last-9 matching, junk filter), `OverdueCalculator` (§4.5/§5.4), `DailyCheckWorker` + `WorkScheduler` + `BootReceiver` + anti-spam/snooze logic (§5), and `Notifier` + `CallActionReceiver` (§6). Owns Phases 1–2.
- **Frontend builds:** the three Compose screens — tracked list, add-contact (PickContact + ContactsContract resolve), cadence edit — plus the first-run/permissions/battery flow (§7). Owns Phases 3–4.
- **Contract between them (the seam):** the `TrackedContactDao` (§3) is the interface. Frontend writes rows (add/edit/delete/snooze/**markCaughtUp**); Backend reads them in the worker and writes only transient state (`snoozeUntil`, `notifiedForLastContactTS`, and `manualLastContactedTS` via the shared `markCaughtUp` from the notification action). Both sides compute the effective last-contact as `max(callLastTS, manualLastContactedTS)` and feed it to `OverdueCalculator.isOverdue(now, last, cadenceDays)` — Frontend to paint list state, Backend to decide notifications — so UI and worker never disagree.
- **Blocked on user:** §8.2 decisions only — default cadence, notify hour, snooze length, "who's overdue" dashboard, and the overdue-count cap. §8.1 (counting types) is now LOCKED to outgoing+incoming; the "Caught up ✓" feature is fully specified, no user input needed.
