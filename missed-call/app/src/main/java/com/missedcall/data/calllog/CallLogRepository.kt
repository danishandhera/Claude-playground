package com.missedcall.data.calllog

import android.content.Context
import android.net.Uri
import android.os.Build
import android.provider.CallLog
import android.util.Log
import com.missedcall.data.db.TrackedContact
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Risk-bearing area #1 (ARCHITECTURE.md §4). This layer is a *pure view of the call log*: given the
 * tracked contacts, it returns each one's most-recent QUALIFYING call timestamp. It knows nothing
 * about cadence, overdue, or the manual "Caught up" stamp — those are folded in later by the caller
 * (OverdueCalculator, §5.4). Keeping this layer narrow keeps the risky matching code testable.
 *
 * Three things must be right here:
 *   1. the number match (last 9 digits — see [PhoneKey]),
 *   2. the Nougat LIMIT split (a Google bug broke LIMIT in the sort string on API 24+),
 *   3. junk / withheld number filtering (restricted, "-1", null/blank).
 */
class CallLogRepository(private val context: Context) {

    companion object {
        private const val TAG = "CallLogRepo"

        /**
         * Scan window: how many newest rows to read. We only need the most-recent qualifying call
         * per tracked person, so a bounded newest-first scan is enough — no full-log read.
         * Edge case (documented, accepted in v1): if a tracked person's last call is older than
         * SCAN_LIMIT rows ago, we won't find it and they read as "never contacted" → overdue, which
         * is the correct nudge anyway. Raise this or add a targeted per-person query if it bites.
         */
        private const val SCAN_LIMIT = 500

        /**
         * What counts as "contact made" — LOCKED (§4.4 / §8.1). Outgoing + incoming reset the
         * timer (a real conversation counts regardless of who dialed); missed & rejected do NOT
         * (ignored/spam calls must not falsely reset the clock).
         */
        private val COUNTING_TYPES = setOf(
            CallLog.Calls.OUTGOING_TYPE,
            CallLog.Calls.INCOMING_TYPE,
        )
    }

    /**
     * Map: tracked contact id -> most-recent qualifying CALL timestamp (epoch millis), or null when
     * no qualifying call was found within the scan window. Call-log signal ONLY (§4.5).
     *
     * Single newest-first pass: for each usable, counting row we resolve its [PhoneKey] and attach
     * it to whichever tracked contact owns that key. Because the cursor is DATE DESC, the FIRST hit
     * per contact is their most-recent call, so once a contact has a timestamp we never overwrite it
     * (we just skip). Every row whose key matches no tracked contact is logged for dev tuning.
     */
    suspend fun lastContactMap(tracked: List<TrackedContact>): Map<Long, Long?> =
        withContext(Dispatchers.IO) {
            // Seed every tracked id with null so contacts with zero matches surface as "never".
            val result = HashMap<Long, Long?>(tracked.size)
            for (c in tracked) result[c.id] = null

            if (tracked.isEmpty()) return@withContext result

            // Build a reverse index: phone key -> tracked contact ids that own it. A key can map to
            // more than one contact in theory (shared/keying collision); we credit the call to all.
            val keyToIds = HashMap<String, MutableList<Long>>()
            for (c in tracked) {
                for (key in c.numberKeys.split(',')) {
                    val k = key.trim()
                    if (k.isEmpty()) continue
                    keyToIds.getOrPut(k) { mutableListOf() }.add(c.id)
                }
            }
            if (keyToIds.isEmpty()) return@withContext result

            // Track which contacts are already resolved so we can short-circuit and stop early once
            // every tracked contact has its most-recent call.
            val remaining = HashSet(tracked.map { it.id })

            val projection = arrayOf(
                CallLog.Calls.NUMBER,               // raw dialed string
                CallLog.Calls.DATE,                 // epoch millis
                CallLog.Calls.TYPE,                 // OUTGOING / INCOMING / MISSED / REJECTED / ...
                CallLog.Calls.NUMBER_PRESENTATION,  // ALLOWED / RESTRICTED / UNKNOWN / PAYPHONE
            )

            val (uri, sortOrder) = buildBoundedQuery(SCAN_LIMIT)

            val cursor = try {
                context.contentResolver.query(uri, projection, null, null, sortOrder)
            } catch (se: SecurityException) {
                // READ_CALL_LOG revoked/not yet granted. Treat as "no data" — everyone reads as
                // never-contacted. The first-run flow (Phase 4) blocks on this permission.
                Log.w(TAG, "READ_CALL_LOG not granted; returning empty last-contact map", se)
                return@withContext result
            } ?: run {
                Log.w(TAG, "Call log query returned null cursor")
                return@withContext result
            }

            cursor.use { cur ->
                val numberIdx = cur.getColumnIndexOrThrow(CallLog.Calls.NUMBER)
                val dateIdx = cur.getColumnIndexOrThrow(CallLog.Calls.DATE)
                val typeIdx = cur.getColumnIndexOrThrow(CallLog.Calls.TYPE)
                val presIdx = cur.getColumnIndexOrThrow(CallLog.Calls.NUMBER_PRESENTATION)

                while (cur.moveToNext()) {
                    if (remaining.isEmpty()) break   // every tracked contact resolved — stop early.

                    val number = cur.getString(numberIdx)
                    val presentation = cur.getInt(presIdx)
                    if (!isUsableRow(number, presentation)) continue

                    val type = cur.getInt(typeIdx)
                    if (type !in COUNTING_TYPES) continue   // missed/rejected/blocked don't count.

                    val key = PhoneKey.of(number) ?: continue
                    val ids = keyToIds[key]
                    if (ids == null) {
                        // Dev-time signal: a real, counting call that matched no tracked contact.
                        // Helps catch systematic matcher misses (short codes, foreign formats, etc).
                        Log.d(TAG, "Unmatched call row key=$key (num masked)")
                        continue
                    }

                    val date = cur.getLong(dateIdx)
                    for (id in ids) {
                        // DATE DESC → first hit per id is newest. Only fill still-null (unresolved).
                        if (id in remaining) {
                            result[id] = date
                            remaining.remove(id)
                        }
                    }
                }
            }

            result
        }

    /**
     * Nougat LIMIT split (§4.1) — LOAD-BEARING. On API 24+ (Nougat) a Google bug broke `LIMIT`
     * embedded in the sort-order string; it silently returns wrong rows. So we pass the limit via
     * the [CallLog.Calls.LIMIT_PARAM_KEY] query parameter there and use a plain sort order. On older
     * platforms we append `LIMIT n` to the sort string the old way. minSdk is 26 so we're always on
     * the N+ branch in practice, but the pre-N branch is kept correct as defensive documentation.
     */
    private fun buildBoundedQuery(limit: Int): Pair<Uri, String> =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            val uri = CallLog.Calls.CONTENT_URI.buildUpon()
                .appendQueryParameter(CallLog.Calls.LIMIT_PARAM_KEY, limit.toString())
                .build()
            uri to "${CallLog.Calls.DATE} DESC"
        } else {
            CallLog.Calls.CONTENT_URI to "${CallLog.Calls.DATE} DESC LIMIT $limit"
        }

    /**
     * Junk / withheld filtering (§4.3). Rows that can't be a real, attributable call are dropped
     * early — free correctness + speed, since withheld/unknown callers can never match a contact.
     */
    private fun isUsableRow(number: String?, presentation: Int): Boolean {
        if (presentation != CallLog.Calls.PRESENTATION_ALLOWED) return false // restricted/unknown/payphone
        if (number.isNullOrBlank()) return false
        if (number.trim() == "-1") return false                              // withheld sentinel
        return true
    }
}
