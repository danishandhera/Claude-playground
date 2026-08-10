# helthi

A personal fitness-data consolidator. Pull three separate tracking streams — **Whoop** (sleep, recovery, strain), **Hevy** (strength workouts: exercises, sets, reps, weight), and **Samsung Health** (heart rate via Samsung smartwatch) — into **one local store**, then surface cross-source insight through a local web dashboard.

## The idea

Each app is a silo. Whoop knows how recovered you are but nothing about the barbell. Hevy knows your training volume but nothing about your sleep. Samsung has your heart rate but doesn't tie it to the workout. The value is in the **joins** — recovery vs. training load, sleep vs. next-day performance, HR zones per workout — which no single app can show because none of them holds all three streams.

## Locked scope (user decisions, 2026-07-31)

- **Ingestion — Hybrid.** Auto-pull Whoop via its official API. **Hevy = CSV export only** (user does not have Hevy Pro, so the API is off the table — no paywall dependency). Samsung Health is export-only in practice → user drops CSV exports into a watched folder; the tool ingests whatever's there. So: one API source (Whoop) + two file-drop sources (Hevy, Samsung).
- **Store + interface — Local web dashboard.** Normalize all three sources into one SQLite database; a local dashboard renders charts, trends, and cross-source views.
- **Insight goals (all four prioritized):**
  1. **Recovery vs. training load** — Whoop recovery/strain × Hevy volume (overtraining / under-recovery signal).
  2. **Sleep → performance** — Whoop sleep quality × next-day Hevy output and Samsung HR.
  3. **Heart-rate zones** — Samsung HR merged onto Hevy sessions → effort/zones per workout type.
  4. **Long-term trends** — strength progression, resting HR drift, recovery trend over weeks/months.

## Config decisions (user, 2026-08-01)

- **HR-zone model — Karvonen / heart-rate reserve.** Zones computed from BOTH resting HR (pulled free from Whoop) and max HR, not a flat %HRmax. More personalized; costs nothing extra since resting HR is already ingested.
- **Home timezone — `Asia/Dubai`** (GST, UTC+4). The time-alignment layer localizes Hevy wall-clock timestamps and applies Samsung's `time_offset` against this.

## Data-source reality (research summary)

- **Whoop** — official OAuth API v2: sleep, recovery, strain/cycles, workouts. Also full account CSV export. *Most automatable.*
- **Hevy** — official API at `api.hevyapp.com` requires **Hevy Pro** + API key (workouts, exercises, sets). Fallback: per-account CSV export.
- **Samsung Health** — **no open third-party API** (SDK is partner-only). Practical routes: in-app data export (folder of CSVs like `heart_rate.csv`, `exercise.csv`) or Health Connect bridging on Android. For a Mac-centric workflow → periodic manual export into a watched folder.

## Fit

Light-local + cloud-brained, matches the household tooling pattern (dubizzle-tool, food-compare): local Python + SQLite core, thin dashboard on top. Runs on the M4 MacBook Air.

## Status

💡 Idea → scoped. Next: GitScout prior-art pass, then architect blueprint (schema, normalization layer, ingestion, dashboard stack).
