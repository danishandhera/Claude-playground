package com.missedcall.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class OverdueCalculatorTest {

    private val day = OverdueCalculator.MILLIS_PER_DAY
    private val now = 1_000_000_000_000L // fixed reference instant

    @Test fun `never contacted is overdue`() {
        assertTrue(OverdueCalculator.isOverdue(now, last = null, cadenceDays = 21))
    }

    @Test fun `exactly at cadence is not yet overdue`() {
        val last = now - 21 * day // 21 whole days elapsed, cadence 21 → not > 21.
        assertFalse(OverdueCalculator.isOverdue(now, last, cadenceDays = 21))
    }

    @Test fun `one day past cadence is overdue`() {
        val last = now - 22 * day
        assertTrue(OverdueCalculator.isOverdue(now, last, cadenceDays = 21))
    }

    @Test fun `well within cadence is not overdue`() {
        val last = now - 3 * day
        assertFalse(OverdueCalculator.isOverdue(now, last, cadenceDays = 21))
    }

    @Test fun `maxOfNullable folds call and manual signals`() {
        assertNull(maxOfNullable(null, null))
        assertEquals(5L, maxOfNullable(5L, null))
        assertEquals(5L, maxOfNullable(null, 5L))
        assertEquals(9L, maxOfNullable(5L, 9L))
        assertEquals(9L, maxOfNullable(9L, 5L))
    }

    @Test fun `manual stamp can pull a stale call into healthy`() {
        val staleCall = now - 40 * day        // by call log alone → overdue for 21d cadence
        val manual = now - 2 * day            // user marked caught up recently
        val effective = maxOfNullable(staleCall, manual)
        assertFalse(OverdueCalculator.isOverdue(now, effective, cadenceDays = 21))
    }

    @Test fun `newer real call supersedes an older manual stamp`() {
        val recentCall = now - 1 * day
        val manual = now - 30 * day
        val effective = maxOfNullable(recentCall, manual)
        assertEquals(recentCall, effective)
        assertFalse(OverdueCalculator.isOverdue(now, effective, cadenceDays = 21))
    }
}
