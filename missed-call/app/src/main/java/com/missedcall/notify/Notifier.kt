package com.missedcall.notify

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.missedcall.R
import com.missedcall.data.db.TrackedContact
import com.missedcall.domain.OverdueCalculator
import kotlin.math.max

/**
 * Native notifications (ARCHITECTURE.md §6). Phase 1 is a BARE nudge: title/body + content-tap to
 * the dialer, no action buttons (Call now / Caught up / Snooze come in Phase 2 via
 * CallActionReceiver). The channel + POST_NOTIFICATIONS handling are wired correctly now so Phase 2
 * only adds actions.
 */
class Notifier(private val context: Context) {

    companion object {
        const val CHANNEL_ID = "nudges"
        private const val CHANNEL_NAME = "Keep-in-touch reminders"
        private const val TAG = "Notifier"
    }

    /** Create the single channel once. Safe to call repeatedly (idempotent). Called from App. */
    fun ensureChannel() {
        // NotificationChannel exists on O+; minSdk is 26 so it's always present, but guard anyway.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                // DEFAULT = visible + sound, not intrusive. One calm daily nudge.
                NotificationManager.IMPORTANCE_DEFAULT,
            ).apply {
                description = "Reminders to reach out to people you're tracking."
            }
            val mgr = context.getSystemService(NotificationManager::class.java)
            mgr.createNotificationChannel(channel)
        }
    }

    /**
     * Post one overdue nudge for [contact]. Stable notification id = contact.id so a re-fire
     * replaces rather than stacks.
     *
     * @param effectiveLast effective last-contact TS (max of call + manual), null = never.
     * @param now current time, for humanizing the elapsed span.
     */
    fun notifyOverdue(contact: TrackedContact, effectiveLast: Long?, now: Long) {
        if (!hasPostPermission()) {
            // On API 33+ posting silently no-ops without the runtime grant. Log so debug builds
            // make the missing permission obvious; the list-screen soft banner (Phase 4) surfaces it.
            Log.w(TAG, "POST_NOTIFICATIONS not granted; skipping nudge for ${contact.displayName}")
            return
        }

        val name = contact.displayName
        val body = "You haven't called $name in ${humanizeElapsed(effectiveLast, now)}."

        // Content-tap → ACTION_DIAL (needs no permission; we never auto-place calls). Prefill the
        // contact's primary number if we have one from the snapshot.
        val primary = primaryDialString(contact)
        val dialIntent = Intent(Intent.ACTION_DIAL).apply {
            if (primary != null) data = Uri.parse("tel:$primary")
        }
        val contentPi = PendingIntent.getActivity(
            context,
            contact.id.toInt(),
            dialIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("Time to call $name")
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(contentPi)
            .setAutoCancel(true)
            .setCategory(NotificationCompat.CATEGORY_REMINDER)
            .build()

        NotificationManagerCompat.from(context).notify(contact.id.toInt(), notification)
    }

    private fun hasPostPermission(): Boolean {
        // Runtime permission only exists on API 33+. Below that it's implicitly granted.
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return true
        return ContextCompat.checkSelfPermission(
            context, Manifest.permission.POST_NOTIFICATIONS,
        ) == PackageManager.PERMISSION_GRANTED
    }

    /**
     * Phase 1 uses the first stored number key as the dial target. This is a last-9-digits key, not
     * a full E.164 number, so it may drop the country code — acceptable for a local-dial nudge in
     * the slice. Phase 3 resolves the real primary number from ContactsContract at add-time.
     */
    private fun primaryDialString(contact: TrackedContact): String? =
        contact.numberKeys.split(',').firstOrNull { it.isNotBlank() }?.trim()

    /** Humanize elapsed span: weeks when >= 2 weeks, else days. null → "a while". */
    private fun humanizeElapsed(last: Long?, now: Long): String {
        if (last == null) return "a while"
        val days = max(0L, (now - last) / OverdueCalculator.MILLIS_PER_DAY)
        return when {
            days >= 14 -> "${days / 7} weeks"
            days >= 7 -> "1 week"
            days <= 1 -> "a day"
            else -> "$days days"
        }
    }
}
