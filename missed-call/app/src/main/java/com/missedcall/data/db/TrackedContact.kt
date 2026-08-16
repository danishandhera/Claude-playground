package com.missedcall.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * The single entity that carries everything: who to track, how often, and transient notification
 * state. We *derive* the last-contacted timestamp from the call log at job time and never persist
 * an interaction history — the call log IS the history. The one deliberate stored exception is
 * [manualLastContactedTS] (see ARCHITECTURE.md §3).
 *
 * Schema is written to the full v1 spec now (including [manualLastContactedTS], [snoozeUntil] and
 * the [notifiedForLastContactTS] dedupe cursor) even though the Phase 1 slice only exercises the
 * read + overdue + notify path — this way Phase 2 needs no migration.
 */
@Entity(tableName = "tracked_contact")
data class TrackedContact(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,

    // WHY lookup key, not the raw contact _ID: raw ids churn on sync/merge/restore; the
    // LOOKUP_KEY survives those. We resolve the current display name + numbers from
    // ContactsContract at read time (Phase 2's refreshSnapshots).
    val lookupKey: String,

    // Snapshot at add-time, for display + as a fallback if the contact is later deleted.
    val displayName: String,

    // Denormalized number snapshot: comma-joined last-9-digit phone keys captured at add-time and
    // refreshed on each daily run. Lets the matcher run without a live contacts read every job and
    // degrades gracefully if READ_CONTACTS is later revoked. e.g. "551234567,505551212".
    val numberKeys: String,

    // Canonical cadence unit is DAYS (UI may present weeks/months as sugar).
    val cadenceDays: Int,

    // Manual "Caught up" timestamp — the one deliberate stored value. Set to now() when the user
    // asserts they connected off the call log (IRL / text / other app). Only ever pushes the
    // effective last-contact clock forward; a later real call supersedes it. Null = never.
    // Written by Phase 2's markCaughtUp; carried in the schema now to avoid a later migration.
    val manualLastContactedTS: Long? = null,

    // --- transient notification state (not relationship data) ---

    // Suppress notifications until this instant. Snooze sets it; null = not snoozed. (Phase 2.)
    val snoozeUntil: Long? = null,

    // Anti-spam dedupe cursor: the effective-last value we last notified about. If the current
    // computed value is unchanged AND we already notified, don't re-nag. Auto-resets for free when
    // a new call appears (new last value → mismatch → eligible again). (Wired fully in Phase 2.)
    val notifiedForLastContactTS: Long? = null,

    val createdAt: Long = System.currentTimeMillis(),
)
