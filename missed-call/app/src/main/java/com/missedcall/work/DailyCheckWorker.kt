package com.missedcall.work

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.missedcall.data.calllog.CallLogRepository
import com.missedcall.data.db.AppDatabase
import com.missedcall.domain.OverdueCalculator
import com.missedcall.domain.maxOfNullable
import com.missedcall.notify.Notifier

/**
 * The daily check (ARCHITECTURE.md §5.3). PHASE 1 SCOPE: read the call log, fold in the manual
 * stamp to get the effective-last contact, compute overdue, and fire a bare notification for each
 * overdue person. This proves the riskiest primitive end-to-end.
 *
 * Deliberately DEFERRED to Phase 2 (marked inline below, not built here):
 *   - snooze suppression (isSnoozed / snoozeUntil),
 *   - anti-spam dedupe writes (notifiedForLastContactTS via setNotified) so repeated runs don't
 *     re-nag for the same overdue episode,
 *   - contacts snapshot refresh from ContactsContract (refreshSnapshots).
 * The schema and DAO already carry those fields so Phase 2 adds behavior without a migration.
 */
class DailyCheckWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val now = System.currentTimeMillis()
        val dao = AppDatabase.get(applicationContext).trackedContactDao()
        val callLogRepo = CallLogRepository(applicationContext)
        val notifier = Notifier(applicationContext)

        val tracked = dao.getAll()
        if (tracked.isEmpty()) {
            Log.d(TAG, "No tracked contacts; nothing to check.")
            return Result.success()
        }

        // PHASE 2: refreshSnapshots(tracked) from ContactsContract here (if READ_CONTACTS granted).

        val lastCallMap = callLogRepo.lastContactMap(tracked)

        var overdueCount = 0
        for (c in tracked) {
            val callLast = lastCallMap[c.id]                       // null = no qualifying call found
            // Fold in the manual "Caught up" stamp: effective last-contact is the more recent of the
            // call-log signal and the manual stamp (§5.3). Single point where the manual value enters.
            val effectiveLast = maxOfNullable(callLast, c.manualLastContactedTS)

            val overdue = OverdueCalculator.isOverdue(now, effectiveLast, c.cadenceDays)
            if (!overdue) continue
            // PHASE 2: if (isSnoozed(c, now)) continue
            // PHASE 2: if (c.notifiedForLastContactTS == effectiveLast) continue  // already nudged

            notifier.notifyOverdue(c, effectiveLast, now)
            // PHASE 2: dao.setNotified(c.id, effectiveLast)   // key dedupe to this episode
            overdueCount++
        }

        Log.d(TAG, "Daily check complete: ${tracked.size} tracked, $overdueCount overdue nudged.")
        return Result.success()
    }

    companion object {
        private const val TAG = "DailyCheckWorker"
    }
}
