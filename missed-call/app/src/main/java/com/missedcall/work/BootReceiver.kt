package com.missedcall.work

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Re-arm the daily worker after reboot (ARCHITECTURE.md §5.2). WorkManager usually persists across
 * reboot, but OEM task-killers are unreliable, so we re-enqueue defensively. ensureScheduled is the
 * same idempotent KEEP enqueue, so this never resets the clock. App.onCreate() does the same on
 * manual launch to heal a dropped schedule.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            WorkScheduler.ensureScheduled(context.applicationContext)
        }
    }
}
