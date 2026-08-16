package com.missedcall

import android.app.Application
import com.missedcall.notify.Notifier
import com.missedcall.work.WorkScheduler

/**
 * Process entry point. Creates the notification channel once and ensures the daily worker is
 * scheduled (idempotent KEEP — heals a dropped schedule on every launch, §5.2).
 */
class App : Application() {
    override fun onCreate() {
        super.onCreate()
        Notifier(this).ensureChannel()
        WorkScheduler.ensureScheduled(this)
    }
}
