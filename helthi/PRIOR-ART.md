# helthi — Prior art (GitScout, 2026-07-31)

**Punchline:** don't invent the hard parts. Take three off-the-shelf MIT pieces + one format-reference, glue with our own normalization layer.

## Recommended borrow list

1. **hedgertronic/whoop** (MIT, 100★, active) — the entire **Whoop v2 OAuth + token-refresh + endpoints** layer. Authlib-based: `authorization_url()` → `fetch_token()` → auto-refresh via `offline` scope + `on_token_refresh` persistence callback (exactly what a headless nightly sync needs). Endpoints: `AUTHORIZE_URL=api.prod.whoop.com/oauth/oauth2/auth`, `TOKEN_URL=.../token`; uses `client_secret_post` (creds in body). **This is our Whoop layer.**
2. **sandseb123/Leo-Health-Core** (MIT, 91★, active) — the **architecture template**: helthi minus Hevy/Samsung. Local, zero-network, CSV/Apple-Health → normalized SQLite + folder watcher + local Flask dashboard + Docker. Lift: `source`-tagged tables, per-source `parsers/`, `db/ingest.py`, imports-folder watcher, dedupe, `dashboard.py`. Its Whoop-CSV parser has multi-format date coalescing + header auto-detection (Whoop export is several CSVs with inconsistent headers).
3. **remuzel/hevy-api** (MIT, 29★) — typed Hevy **data models** (Workout/Exercise/Set, paginated responses). Even though we're CSV-only (no Pro), this is the cleanest **schema reference** for our `hevy_*` tables: model `workout → exercise → set` (weight/reps/rpe).
4. **BlackFireAlex/samsung_health_extractor** (⚠️ **no license — format reference only, do NOT copy code**) — Rosetta Stone for the Samsung export dump. Key quirks: first line is a metadata banner (`skiprows=1`); timestamps are epoch **milliseconds**; columns prefixed `com.samsung.shealth.*` (strip); **heart-rate data lives in per-record JSON files** referenced from the CSV, not inline; `time_offset` field must be applied for local time; sport types are integer codes.

## Supporting references (patterns, not dependencies)

- **ErikBjare/quantifiedme** (MIT, 90★) — multi-source QS ETL; `derived/` helpers that merge multiple sources for the same metric (model for HR-overlay + cross-source reconciliation). Notebook toolkit, not a server.
- **davidmosiah/samsung-health-mcp** (MIT, 8★, active Jul 2026) — recent Samsung CSV/ZIP export reader; **cross-check current export shape against this** (BlackFireAlex is from 2022 and may have drifted). Handles CSV-in-folder / single-CSV / zipped variants.
- **drkostas/hevy2garmin** (78★, verify license) — directly does **HR overlay onto strength workouts** — our insight goal #3. Borrow the HR-to-set time-alignment logic.
- **casudo/Hevy-Insights** (MIT, 101★) — mine for **Hevy dashboard/chart choices** (skip the Vue stack).
- **umutkeltek/healthsave-observatory** (⚠️ Elastic-2.0 — ideas only, don't vendor) — Source/Device/Stream identity model, Grafana route if we ever outgrow Flask.

## Skip / dead
ianm199/unofficialWhoopAPI (pre-v2, obsolete), pelo-tech/whoop-api-spec (stale 2022), most whoop-mcp servers (agent plumbing), 0★ Health Connect exporters (immature/no license).

## Watch-outs
- **Whoop rate limits:** 100 req/min, 10k req/day → 429 + backoff. Fine for nightly personal sync; page through collections.
- **Samsung is the trap:** no live API; format drifts between app versions. Build the parser tolerant (prefix-stripping, epoch-ms detection, nested-JSON HR). Need a **real export sample** to finalize.
- **Licensing:** hedgertronic/whoop, Leo-Health-Core, remuzel/hevy-api, quantifiedme, samsung-health-mcp = MIT (safe to lift). healthsave-observatory = Elastic-2.0 (ideas only). BlackFireAlex = no license (format reference only, write our own parser).

Sources: [Whoop rate limits](https://developer.whoop.com/docs/developing/rate-limiting) · [remuzel/hevy-api](https://github.com/remuzel/hevy-api) · [Hevy API docs](https://api.hevyapp.com/docs/)
