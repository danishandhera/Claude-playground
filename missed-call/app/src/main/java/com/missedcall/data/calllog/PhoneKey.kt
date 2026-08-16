package com.missedcall.data.calllog

/**
 * Last-9-digits number matching (ARCHITECTURE.md §4.2, README "Borrow #1").
 *
 * We deliberately do NOT do full E.164 string equality — the call log stores raw dialed strings
 * ("+971 55 123 4567", "055 123 4567", "0551234567") while contacts store their own format, so
 * exact matches are fragile across country codes and trunk prefixes. Instead we strip every side
 * to digits and compare only the trailing [COMPARABLE_LEN] digits. This is our own re-expression
 * of Fossify's proven trick (their code is GPL-3.0 — studied, not copied).
 *
 * Known residual failure modes we accept in v1: short codes, extensions, and multi-SIM duplicates
 * can mis-key. During dev we log unmatched call rows to eyeball systematic misses (see repository).
 */
object PhoneKey {

    /** Fossify's COMPARABLE_PHONE_NUMBER_LENGTH. 9 trailing digits uniquely identify a subscriber
     * within a country while ignoring country code + trunk-prefix noise. */
    const val COMPARABLE_LEN = 9

    /**
     * Normalize a raw phone string to its comparable key.
     *
     * @return the last [COMPARABLE_LEN] digits (or all digits if shorter), or null when the input
     *   has no usable digits at all (null/blank/symbols-only, or the "-1" withheld sentinel which
     *   filters to no digits' worth of a real number — handled upstream in isUsableRow too).
     */
    fun of(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        // filter { isDigit } drops '+', spaces, dashes, parentheses, and any other formatting.
        val digits = raw.filter { it.isDigit() }
        if (digits.isEmpty()) return null
        return if (digits.length <= COMPARABLE_LEN) digits else digits.takeLast(COMPARABLE_LEN)
    }
}
