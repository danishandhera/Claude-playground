package com.missedcall.data.db

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Query
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

/**
 * The seam between Backend and Frontend (ARCHITECTURE.md §11). Frontend writes rows
 * (add/edit/delete/snooze/markCaughtUp); Backend reads them in the worker and writes only
 * transient state. The full DAO is declared now so both sides build against a stable contract —
 * the snooze / caught-up / setNotified mutations are Phase 2 write paths but harmless to expose.
 */
@Dao
interface TrackedContactDao {

    /** UI stream of all tracked contacts. */
    @Query("SELECT * FROM tracked_contact ORDER BY displayName")
    fun observeAll(): Flow<List<TrackedContact>>

    /** Worker snapshot read. */
    @Query("SELECT * FROM tracked_contact")
    suspend fun getAll(): List<TrackedContact>

    @Query("SELECT * FROM tracked_contact WHERE id = :id")
    suspend fun getById(id: Long): TrackedContact?

    @Upsert
    suspend fun upsert(c: TrackedContact): Long

    @Delete
    suspend fun delete(c: TrackedContact)

    /** Snooze: defer notifications until [until]. Pure suppression, no relationship-data change. */
    @Query("UPDATE tracked_contact SET snoozeUntil = :until WHERE id = :id")
    suspend fun setSnooze(id: Long, until: Long?)

    /**
     * "Caught up" — full-cadence reset. Stamps now() into manualLastContactedTS and clears the
     * dedupe cursor so a fresh cycle starts. Distinct from setSnooze (which only defers). Phase 2.
     */
    @Query("UPDATE tracked_contact SET manualLastContactedTS = :ts, notifiedForLastContactTS = NULL WHERE id = :id")
    suspend fun markCaughtUp(id: Long, ts: Long)

    /** Anti-spam cursor write: remember the effective-last value we just notified about. */
    @Query("UPDATE tracked_contact SET notifiedForLastContactTS = :ts WHERE id = :id")
    suspend fun setNotified(id: Long, ts: Long?)

    /** Refresh the denormalized name + number snapshot from ContactsContract on each daily run. */
    @Query("UPDATE tracked_contact SET numberKeys = :keys, displayName = :name WHERE id = :id")
    suspend fun refreshContactSnapshot(id: Long, keys: String, name: String)
}
