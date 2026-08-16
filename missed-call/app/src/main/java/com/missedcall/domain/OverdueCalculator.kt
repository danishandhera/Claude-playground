package com.missedcall.domain

/**
 * Pure, Android-free overdue logic (ARCHITECTURE.md §5.4) so the risky comparison is unit-testable
 * on the plain JVM. Both the worker (to decide notifications) and the Frontend list (to paint
 * state) call [isOverdue] with the SAME effective-last value, so UI and worker never disagree.
 */
object OverdueCalculator {

    const val MILLIS_PER_DAY = 24L * 60L * 60L * 1000L

    /**
     * @param last the EFFECTIVE last-contact timestamp = max(callLastTS, manualLastContactedTS),
     *   folded by the caller (§5.3). null means never contacted at all → always overdue.
     * @return true when more than [cadenceDays] whole days have elapsed since [last].
     *
     * Date-granular by design (§1): we compare elapsed whole days to the cadence, so a 21-day
     * contact becomes overdue on day 22, not on the exact clock-instant 21 days later.
     */
    fun isOverdue(now: Long, last: Long?, cadenceDays: Int): Boolean {
        if (last == null) return true
        val elapsedDays = (now - last) / MILLIS_PER_DAY
        return elapsedDays > cadenceDays
    }
}

/**
 * Null-safe max used to fold the call-log signal and the manual "Caught up" stamp into one
 * effective-last value. Both null → null (never contacted). The manual stamp can only push the
 * clock forward; a newer real call automatically supersedes it.
 */
fun maxOfNullable(a: Long?, b: Long?): Long? = when {
    a == null -> b
    b == null -> a
    else -> maxOf(a, b)
}
