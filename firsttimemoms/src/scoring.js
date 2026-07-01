/* ─── SCORING ─────────────────────────────────────────────────────────────── */
/*
 * scoreMatch(carer, ans) → { total, br, weights }
 *
 *   total   — 0–100 overall match score.
 *   br      — per-factor breakdown (0–100 each) for the score bars in the UI.
 *   weights — the (possibly priority-adjusted) weight used per factor.
 *
 * All weights/thresholds live in SCORING_CONFIG below — no inline magic numbers.
 */

export const SCORING_CONFIG = {
  // Base blend weights. Sum of the five factor weights = 1.0; the language
  // bonus is added on top (capped) rather than being part of the blend.
  weights: {
    tradition:    0.40,
    budget:       0.20,
    location:     0.20,
    availability: 0.15,
    liveIn:       0.05,
  },

  // Tradition-fit sub-scores.
  tradition: {
    exact:        100, // carer explicitly practises the requested tradition
    mixed:         60, // user is open ("mixed") — most carers are a decent fit
    related:       45, // carer practises a culturally adjacent tradition
    unrelated:     15, // no overlap
    noPreference:  70, // user skipped the question
    // Which traditions count as "related" (adjacent) to each other.
    relatedMap: {
      "south-indian": ["north-indian"],
      "north-indian": ["south-indian", "pakistani"],
      "pakistani":    ["north-indian"],
    },
  },

  // Budget buckets. Contiguous — no gap between adjacent buckets, so any
  // mid-range rate (e.g. 4500) lands inside exactly one bucket's [min,max].
  budget: {
    buckets: {
      "<1000":     { min: 0,    max: 1000 },
      "1000-2000": { min: 1000, max: 2000 },
      "2000-3000": { min: 2000, max: 3000 },
      "3000-4000": { min: 3000, max: 4000 },
      "4000-5000": { min: 4000, max: 5000 },
      ">5000":     { min: 5000, max: 99999 },
    },
    defaultBucket: "3000-4000",
    inRange:       100, // carer rate sits inside the chosen bucket
    underBudget:    82, // carer is cheaper than the bucket (a good thing)
    overSmall:      65, // over budget by < overSmallMax
    overMedium:     40, // over budget by < overMediumMax
    overLarge:      15, // over budget beyond that
    overSmallMax:  500,
    overMediumMax: 1000,
  },

  // Location scoring.
  location: {
    sameCity:     100,
    differentCity: 60,
    noPreference:  70,
  },

  // Availability scoring, relative to the due date.
  availability: {
    leadTimeDays:      14,  // we want the carer free ~2 weeks before due date
    windowDays:        14,  // ±window tolerance around the due date
    readyBeforeWindow: 100, // free with time to spare
    readyByDueDate:     70, // free by the due date
    readyWithinWindow:  45, // free within the tolerance window
    late:               20, // not free in time
    noDate:             75, // user skipped the date
  },

  // Live-in preference scoring.
  liveIn: {
    match:        100, // preference and carer capability align
    mismatch:      30,
    noPreference:  70, // "flexible" or skipped
  },

  // Language bonus (added on top of the blend, capped).
  language: {
    perMatch: 5,
    cap:      10,
  },

  // Priorities boost. The intake "what matters most" step (up to 3 picks) maps
  // each chosen priority to a scoring factor; that factor's weight is boosted,
  // then the five factor weights are re-normalised back to sum 1.0 so total
  // stays 0–100. This makes the priorities actually influence ranking:
  // carers strong in the mother's chosen factors rise, weak ones fall.
  priorities: {
    boostPerPick: 0.5, // +50% relative weight to each mapped factor per pick
    // Which scoring factor each priority id reinforces.
    factorMap: {
      cooking:   "tradition",     // traditional cooking ↔ cultural fit
      massage:   "tradition",     // mother massage is tradition-specific
      baby:      "tradition",     // baby care & massage is tradition-specific
      herbal:    "tradition",     // herbal remedies are tradition-specific
      binding:   "tradition",     // belly binding is tradition-specific
      religious: "tradition",     // religious rituals ↔ cultural fit
      night:     "liveIn",        // night support needs live-in capability
      household: "liveIn",        // household help pairs with live-in
      lactation: "availability",  // early, reliable presence matters most
      emotional: "location",      // frequent, nearby presence matters most
    },
  },
};

/**
 * Build the per-factor weights for this request, boosting any factor tied to a
 * chosen priority, then re-normalising the five blend weights back to sum 1.0.
 */
export function resolveWeights(priorities = []) {
  const { weights } = SCORING_CONFIG;
  const { boostPerPick, factorMap } = SCORING_CONFIG.priorities;
  const w = { ...weights };

  for (const p of priorities) {
    const factor = factorMap[p];
    if (factor && w[factor] != null) {
      w[factor] += w[factor] * boostPerPick;
    }
  }

  const sum = Object.values(w).reduce((a, b) => a + b, 0);
  for (const k of Object.keys(w)) w[k] = w[k] / sum;
  return w;
}

export function scoreMatch(carer, ans) {
  const { tradition, budget, city, dueDate, liveIn, languages, priorities } = ans;
  const C = SCORING_CONFIG;
  const br = { tradition: 0, budget: 0, location: 0, availability: 0, liveIn: 0 };

  // ── Tradition ──────────────────────────────────────────────────────────
  if (tradition) {
    if (carer.traditions.includes(tradition)) br.tradition = C.tradition.exact;
    else if (tradition === "mixed") br.tradition = C.tradition.mixed;
    else {
      const related = C.tradition.relatedMap[tradition] || [];
      br.tradition = related.some((t) => carer.traditions.includes(t))
        ? C.tradition.related
        : C.tradition.unrelated;
    }
  } else {
    br.tradition = C.tradition.noPreference;
  }

  // ── Budget ─────────────────────────────────────────────────────────────
  const bk = budget || C.budget.defaultBucket;
  const bucket = C.budget.buckets[bk] || C.budget.buckets[C.budget.defaultBucket];
  if (carer.rate <= bucket.max && carer.rate >= bucket.min) {
    br.budget = C.budget.inRange;
  } else if (carer.rate < bucket.min) {
    br.budget = C.budget.underBudget;
  } else {
    const over = carer.rate - bucket.max;
    br.budget =
      over < C.budget.overSmallMax
        ? C.budget.overSmall
        : over < C.budget.overMediumMax
        ? C.budget.overMedium
        : C.budget.overLarge;
  }

  // ── Location ───────────────────────────────────────────────────────────
  br.location = !city
    ? C.location.noPreference
    : carer.city === city
    ? C.location.sameCity
    : C.location.differentCity;

  // ── Availability ───────────────────────────────────────────────────────
  if (dueDate) {
    const days = Math.round((new Date(dueDate) - Date.now()) / 86400000);
    const needed = days - C.availability.leadTimeDays;
    br.availability =
      carer.availDays <= needed
        ? C.availability.readyBeforeWindow
        : carer.availDays <= days
        ? C.availability.readyByDueDate
        : carer.availDays <= days + C.availability.windowDays
        ? C.availability.readyWithinWindow
        : C.availability.late;
  } else {
    br.availability = C.availability.noDate;
  }

  // ── Live-in ────────────────────────────────────────────────────────────
  if (!liveIn || liveIn === "flexible") {
    br.liveIn = C.liveIn.noPreference;
  } else {
    const aligned =
      (liveIn === "yes" && carer.liveIn) || (liveIn === "no" && !carer.liveIn);
    br.liveIn = aligned ? C.liveIn.match : C.liveIn.mismatch;
  }

  // ── Language bonus ─────────────────────────────────────────────────────
  let langBonus = 0;
  if (languages && languages.length) {
    const matches = languages.filter((l) => carer.langs.includes(l)).length;
    langBonus = Math.min(C.language.cap, matches * C.language.perMatch);
  }

  // ── Blend (with priority-adjusted weights) ─────────────────────────────
  const w = resolveWeights(priorities);
  const total = Math.min(
    100,
    Math.round(
      br.tradition * w.tradition +
        br.budget * w.budget +
        br.location * w.location +
        br.availability * w.availability +
        br.liveIn * w.liveIn +
        langBonus
    )
  );

  return { total, br, weights: w };
}
