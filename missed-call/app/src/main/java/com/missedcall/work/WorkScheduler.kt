package com.missedcall.work

import android.content.Context
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.Calendar
import java.util.concurrent.TimeUnit

/**
 * Scheduling for the daily check (ARCHITECTURE.md §5.1). Idempotent by design: every launch and
 * every boot calls [ensureScheduled], and ExistingPeriodicWorkPolicy.KEEP means re-arming never
 * resets the clock. No network/charging constraints — the nudge must fire offline, regardless of
 * charge state.
 */
object WorkScheduler {

    private const val DAILY_WORK_NAME = "daily_check"
    private const val ONESHOT_WORK_NAME = "daily_check_now"

    /** Default notify hour, local time (§8.2 proposal — 10:00). Confirm with user before ship. */
    private const val NOTIFY_HOUR = 10

    /**
     * Ensure the daily periodic worker is scheduled. Safe to call repeatedly. Aligns the first run
     * to the next NOTIFY_HOUR; battery optimization may drift the actual fire time — acceptable for
     * a daily nudge.
     */
    fun ensureScheduled(context: Context) {
        val req = PeriodicWorkRequestBuilder<DailyCheckWorker>(24, TimeUnit.HOURS)
            .setInitialDelay(delayUntilNextNotifyHourMillis(), TimeUnit.MILLISECONDS)
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            DAILY_WORK_NAME,
            ExistingPeriodicWorkPolicy.KEEP,
            req,
        )
    }

    /**
     * Fire the check immediately, once — the debug/manual trigger so the Phase 1 slice is verifiable
     * without waiting a day. Does not touch the periodic schedule.
     */
    fun runNow(context: Context) {
        val req = OneTimeWorkRequestBuilder<DailyCheckWorker>().build()
        WorkManager.getInstance(context).enqueueUniqueWork(
            ONESHOT_WORK_NAME,
            androidx.work.ExistingWorkPolicy.REPLACE,
            req,
        )
    }

    private fun delayUntilNextNotifyHourMillis(): Long {
        val now = Calendar.getInstance()
        val next = (now.clone() as Calendar).apply {
            set(Calendar.HOUR_OF_DAY, NOTIFY_HOUR)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }
        if (!next.after(now)) next.add(Calendar.DAY_OF_MONTH, 1) // already past today → tomorrow.
        return next.timeInMillis - now.timeInMillis
    }
}
