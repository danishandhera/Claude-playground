# beanbuds — Architecture

Status: design v1 (2026-08-01). Builds on the README product brief + GitScout prior-art pass. Read the README first; this doc turns it into a concrete build plan.

## 1. Goal & constraints

A **single-user, mobile-first, offline-first** specialty-coffee journal. One bean → many method-aware brews → each brew a structured tasting. The wedge: chart **what the roaster stated** vs. **what the user actually tasted**, sliced by brew method (French press vs. De'Longhi Magnifica). Logging must be fast and one-handed or it won't get used.

Constraints:
- **One user, one phone. No accounts, no server, no multi-tenant.** All data lives on-device.
- **Offline-first is non-negotiable** — full function with no network.
- **Must look nice** — this is a personal tool the user *wants* to open.
- **Method-aware brews must be extensible** — adding a 3rd method (V60, AeroPress…) must not churn the schema.
- **Tasting is structured, not prose** — flavor chips + sliders + rating, so it charts.
- **Curated flavor shortlist in v1** (subset of SCA wheel), expandable — not the full ~110-term wheel.
- **Bag-scanning (photo → LLM auto-fill) deferred to v2** — data model must accept it later without a rewrite.

Assumptions (flag, don't stall): single timezone (Asia/Dubai); one locale (English); grams + Celsius units (add a units toggle only if the user asks); data volume is a few beans/month and a handful of brews/week — tiny, indefinitely. "Looks nice" = clean, warm, coffee-forward palette, big tap targets, the segmented-control brew form from the mockup as the North Star.

## 2. Stack recommendation

**PWA, not Capacitor. React + Vite + TypeScript, styled with Tailwind, data in IndexedDB via Dexie, charts with Recharts, installed to the home screen via a service worker (vite-plugin-pwa / Workbox). No backend, no accounts, no sync in v1.**

| Layer | Choice | Why (one line) |
|---|---|---|
| Shell | **PWA** (installable, offline) | Single user, one phone → no app-store friction, no signing, no native build toolchain; "add to home screen" is enough. |
| Language | TypeScript | Typed brew-parameter unions are the core of the data model; TS makes method-variance safe. |
| Framework | React 18 + Vite | Boring, fast HMR, best-in-class component ecosystem for the chips/sliders/segmented-control UI. |
| Styling | Tailwind | Ship a nice, consistent mobile UI fast without a CSS system to maintain; easy warm/coffee theme via config. |
| Local DB | **IndexedDB via Dexie** | Real indexed queries + large capacity (not localStorage's ~5MB string bucket); Dexie gives a clean typed API and live queries. Offline by definition. |
| Charts | **Recharts** | Declarative React charts; radar (roaster-vs-me flavor overlay) + line (preference over time) cover every v1 chart. |
| Offline/install | vite-plugin-pwa (Workbox) | Precache the app shell → works fully offline; manifest makes it installable. Data is already local, so offline is "free." |
| State | React Query-free; Dexie `useLiveQuery` + local component state | Data lives in Dexie; `useLiveQuery` re-renders on write. No global store needed at this scale. |
| Backup | Manual JSON export/import (v1) | One button dumps the whole DB to a file; the user owns their data and can move phones. Real sync is a v2 decision. |

**Why not Capacitor/Ionic (the Beanconqueror path)?** Beanconqueror is a *published, multi-user, app-store* product — Capacitor earns its keep there (native Bluetooth scales, store distribution). For a solo user on one phone who just needs offline + home-screen install, Capacitor adds a native build pipeline, Xcode/Android Studio, and store overhead we don't need. A PWA delivers offline + install + "looks nice" with a single `vite build` and zero signing. **If** the user later wants a true Play Store listing or native hardware (Bluetooth scale integration), the same React codebase wraps in Capacitor with near-zero rewrite — so this choice is reversible, not a lock-in.

**Why not React Native / Flutter?** Native-grade UI we don't need, and a heavier toolchain for a one-phone tool. Borrow Beanconqueror's *data model* and *method-aware form idea* (below), not its delivery mechanism.

**Why IndexedDB/Dexie over SQLite (Beanconqueror uses SQLite)?** SQLite-in-the-browser (wa-sqlite/absurd-sql) is more setup than this data volume warrants. Dexie over IndexedDB gives indexed queries, is offline-native, and needs no WASM. Our aggregation queries (§4) run over dozens–hundreds of rows in memory — trivially fast.

## 3. Data model

Dexie/IndexedDB stores (the "tables"). Timestamps stored UTC ISO-8601, rendered Asia/Dubai. IDs are UUID strings (stable across export/import; no server to allocate them).

### `beans` (a bag of coffee bought)
| field | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| roaster | string | |
| name | string | the coffee's name/blend |
| origin | string \| null | country/region |
| process | string \| null | washed / natural / honey / … (free string in v1) |
| roastLevel | string \| null | light / medium / dark (curated enum, free-ish) |
| roastDate | string \| null | ISO date |
| price | number \| null | whole AED |
| weightGrams | number \| null | bag size |
| **roasterNotes** | `FlavorTag[]` | **the bag's STATED profile — same tag vocabulary as tastings** (§3 comparison) |
| roasterNotesRaw | string \| null | verbatim text off the bag, for reference / future re-tagging |
| photoBlobId | string \| null | FK → `photos`; the bag photo. **v2 bag-scan writes here + auto-fills the fields above.** |
| notes | string \| null | free notes |
| createdAt | string | |
| archivedAt | string \| null | finished the bag → hide from active pickers without deleting |

Indexes: `roaster`, `createdAt`, `archivedAt`.

### `brews` (one brewing event; method-aware)
The method-variance decision (spelled out below). **A base brew record + a single typed `params` object whose shape is determined by `method`.** Stored as one nested object per brew (IndexedDB stores structured objects natively — no join, no separate table).

| field | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| beanId | string | FK → beans.id |
| **method** | `'french_press' \| 'magnifica'` | the discriminant; extensible enum |
| **params** | `BrewParams` (discriminated union, see below) | method-specific fields live here |
| milk | `{ used: boolean; type?: MilkType; amountMl?: number }` | `MilkType = 'whole'\|'skim'\|'oat'\|'almond'\|…` (curated enum) |
| brewedAt | string | when it was brewed |
| createdAt | string | |

Indexes: `beanId`, `method`, `brewedAt`.

**Method-aware params — the approach & tradeoff.** Three options were on the table:
1. *Wide flat table* — every possible param as a nullable column. Rejected: schema churns every new method; forms guess which columns apply.
2. *Untyped JSON blob* — `params: any`. Rejected: no type safety, no autocomplete, easy to write garbage; charting can't trust field names.
3. **✅ Discriminated union keyed on `method`** — one `params` object, its TypeScript type selected by the `method` literal. **Chosen.** New method = add one variant to the union + one form component; zero changes to `beans`, `tastings`, or existing rows. IndexedDB stores the nested object as-is, so there's no migration. Charts read only the shared fields (rating, tags, sliders in `tastings`), so param-shape divergence never breaks aggregation.

```ts
type FrenchPressParams = {
  doseGrams: number;
  waterGrams: number;      // ratio derived = waterGrams / doseGrams
  waterTempC: number;
  steepSeconds: number;
  grindSetting?: string;   // free label, grinder-specific
};

type MagnificaParams = {
  grindSetting: number;    // De'Longhi dial 1–7ish
  doseGrams: number;       // bean hopper / single-dose
  yieldGrams: number;      // liquid out
  shotSeconds: number;
  // ratio derived = yieldGrams / doseGrams
};

type BrewParams =
  | ({ method: 'french_press' } & FrenchPressParams)
  | ({ method: 'magnifica' }    & MagnificaParams);
// adding V60 later = add `| ({ method: 'v60' } & V60Params)` and one form. Nothing else moves.
```

A tiny **method registry** (`methods.ts`) drives the UI generically: for each method, `{ id, label, fields: FieldSpec[] }`. The segmented control renders from the registry; the form renders fields from `fields`. Adding a method is data, not new form plumbing.

### `tastings` (how a brew actually tasted — the structured, chartable side)
One tasting per brew (1:1 in v1; model as its own store keyed by `brewId` so it can go 1:many later without change).

| field | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| brewId | string | FK → brews.id (unique in v1) |
| **rating** | number | half-star enjoyment, 0.5–5.0 in 0.5 steps |
| **tastedNotes** | `FlavorTag[]` | the chips the user tapped — **same vocabulary as `beans.roasterNotes`** |
| **acidity** | number | slider 0–5 |
| **body** | number | slider 0–5 |
| **sweetness** | number | slider 0–5 |
| bitterness | number \| null | slider 0–5 (optional 4th; espresso-relevant) |
| notes | string \| null | free text (kept, but never the source of charts) |
| photoBlobId | string \| null | FK → `photos` |
| tastedAt | string | |
| createdAt | string | |

Indexes: `brewId`, `rating`, `tastedAt`.

### `photos`
| field | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| blob | Blob | stored directly in IndexedDB (no filesystem, no server) |
| createdAt | string | |

Kept in a separate store so image bytes don't bloat the row scans that charts iterate.

### The comparison model (the wedge)
`beans.roasterNotes` and `tastings.tastedNotes` are **the same type** (`FlavorTag`), drawn from the **same curated taxonomy** (§5). That single decision is what makes "Roaster said → You tasted" a set operation and a chart overlay, not an NLP problem:

- **`FlavorTag` = the taxonomy term id** (e.g. `'berry'`, `'chocolate'`, `'citrus'`), not free text. Stable ids survive taxonomy expansion.
- **Roaster-vs-me comparison strip** (mockup): `matched = roasterNotes ∩ tastedNotes`, `roasterOnly = roasterNotes − tastedNotes`, `youOnly = tastedNotes − roasterNotes`. Pure set math on tag-id arrays.
- **Radar overlay chart:** both note sets projected onto the top-level flavor **families** (§5) → two polygons on one radar (roaster vs. you) per bean or per method.
- Because tags map to SCA families, expanding the vocabulary later refines the chart without changing stored data (old tag ids still map to the same families).

## 4. System design

No server. The whole app is: React UI → Dexie (IndexedDB) → service-worker-cached shell. Everything below runs on-device.

```
[React PWA shell]  ──precached by service worker──▶ works fully offline
      │
      │ useLiveQuery (reactive reads) / db.* (writes)
      ▼
[Dexie]  ──▶  IndexedDB stores: beans · brews · tastings · photos
      │
      ├─ Charting/aggregation: read stores in-memory, group, feed Recharts
      └─ Backup: export all stores → one JSON+blobs file / import restores it
```

### Offline-first storage
- **App shell** (JS/CSS/fonts/icons) is Workbox-precached → cold-launches offline after first load.
- **All data** is already local in IndexedDB; there is no network read path to fail. Offline is the default, not a fallback.
- **Photos** stored as Blobs in IndexedDB → no external asset host, no broken images offline.

### Sync strategy (deliberately deferred)
v1 has **no sync** — it's one phone. The continuity/backup story is **manual JSON export/import**:
- `Export` serializes every store (photos base64-encoded) to a single `beanbuds-backup-<date>.json` the user saves to Files/Drive.
- `Import` restores it (replace or merge-by-id). This covers phone migration and "don't lose my data."
- **If** the user later wants multi-device sync, the clean upgrade path is a per-user store synced via a hosted document DB (e.g. a single-user PocketBase/Supabase table, or Dexie Cloud). UUID PKs and the export schema are already sync-friendly, so this is additive, not a rewrite. **Open decision — see §7.**

### Charting / aggregation
All charts are computed client-side by reading the relevant stores into memory (tens–hundreds of rows) and grouping. Core queries:
- **Preference over time:** `tastings` joined to `brews` (by `brewId`) → series of `rating` vs. `tastedAt`, optionally split by `brews.method`. Line chart.
- **Roaster-vs-me per bean:** for a bean, gather `roasterNotes` and all its brews' `tastedNotes`, project onto flavor families, render radar overlay + the set-diff comparison strip.
- **Method delta:** group tastings by `brews.method` for the same bean → compare mean rating / slider values (does this bean shine on French press vs. Magnifica?). This is the "sliced by brew method" payoff.
- **Slider trends:** mean acidity/body/sweetness over time or per method.

A thin `queries.ts` layer holds these as named functions returning chart-ready arrays, so the Frontend consumes typed data, not raw Dexie.

### Trust boundaries
Minimal — single user, no untrusted input, no network. The only real concern is **data durability**: IndexedDB can be evicted by the OS under storage pressure. Mitigations: call `navigator.storage.persist()` to request persistent storage; nudge the user to export a backup periodically (e.g. a gentle reminder after N new brews). Input validation is just form-level (numeric ranges, required fields) to keep charts clean.

## 5. The curated flavor taxonomy

**Design:** a flat starter list of ~24 terms, each tagged with its **SCA top-level family** (the wheel's inner ring). Charts aggregate by family; chips display individual terms. Every term carries a stable `id` so expanding to the full wheel later never rewrites stored tags. This is the single source of truth shared by `beans.roasterNotes` and `tastings.tastedNotes`.

Shape (`taxonomy.ts`):
```ts
type FlavorTerm = { id: string; label: string; family: FlavorFamily };
type FlavorFamily =
  | 'fruity' | 'floral' | 'sweet' | 'nutty_cocoa'
  | 'spices' | 'roasted' | 'sour_ferment' | 'green_veg';
```

Starter list (v1), grouped by SCA family:

| Family (SCA) | Curated terms (v1 chips) |
|---|---|
| Fruity | Berry, Citrus, Stone Fruit, Tropical, Dried Fruit |
| Floral | Floral, Jasmine |
| Sweet | Caramel, Honey, Brown Sugar, Vanilla |
| Nutty / Cocoa | Chocolate, Cocoa, Nutty, Almond |
| Spices | Cinnamon, Warm Spice |
| Roasted | Roasty, Smoky, Toast |
| Sour / Fermented | Winey, Boozy |
| Green / Vegetative | Herbal, Grassy |

~24 terms — enough range for real specialty notes, few enough to fit the tappable-chip mockup without scrolling fatigue. **Radar axes = the 8 families**, so both roaster and tasted notes always project onto a fixed 8-spoke wheel regardless of how many terms exist.

**Mapping to the SCA wheel for expansion:** each curated term is a node under its SCA family. v2 expansion = add more `FlavorTerm`s under the existing families (e.g. split "Berry" → Blackberry/Raspberry/Blueberry) — a chip drill-down (tap family → see sub-terms). Old tags keep their ids and families, so historical charts stay consistent. The full ~110-term wheel becomes a nested `family → subfamily → term` tree the UI reveals progressively; v1 just ships the flat top layer.

## 6. Phased build plan

**Milestone 0 — Scaffold.** Vite + React + TS + Tailwind app; PWA plugin (manifest + service worker, precache shell, installable + offline); Dexie schema for all four stores; `taxonomy.ts` (the 24 terms) and `methods.ts` (the method registry). *Dependency for everything.* Deliverable: an installable, offline blank shell with a working DB layer.

**Milestone 1 — Beans CRUD.** Add/edit/list/archive a bean, including tapping `roasterNotes` chips from the taxonomy + optional bag photo. Deliverable: the user can log the bags they own.

**Milestone 2 — Method-aware brew logging (the North Star screen).** The mockup screen: bean selector → method segmented control (French press | Magnifica) that swaps the visible params (rendered from the method registry) → milk toggle+type → save a brew. Deliverable: one bean → many method-correct brews.

**Milestone 3 — Structured tasting.** Half-star rating, tappable `tastedNotes` chips, acidity/body/sweetness(/bitterness) sliders, optional photo, attached to a brew. **The "Roaster said → You tasted" comparison strip** (set-diff on tag ids) shown right after logging. Deliverable: the full log-a-cup loop + the wedge visible per brew.

**Milestone 4 — Charts.** `queries.ts` + Recharts: (a) preference (rating) over time, split by method; (b) roaster-vs-me radar overlay per bean; (c) method-delta view for a bean. Deliverable: "chart my preferences + see the gap" — the product thesis, shippable.

**Milestone 5 — Backup.** JSON export/import + `storage.persist()` + a periodic export nudge. Deliverable: data is safe and portable. **v1 ships here.**

**v2 and beyond (deferred, designed-for):**
- **Bag scanning** — bag photo → LLM (Claude, tool-use structured output) → auto-fill bean fields + `roasterNotesRaw` → auto-map to `FlavorTag[]`. Slots into the existing `beans` store + `photos`; the manual bean form becomes the review/confirm step. (Prior art: B{rew}log, Brewfolio.)
- **Full SCA flavor wheel** — expand `taxonomy.ts` to the nested ~110-term tree with chip drill-down. No data migration (ids stable).
- **Richer charts** — per-origin/process preferences, cost-per-good-cup, roast-age vs. rating.
- **New brew methods** — V60, AeroPress, moka: add a union variant + a registry entry. No schema change.
- **Multi-device sync** — Dexie Cloud or a single-user hosted table, if ever wanted.
- **Native wrap** — Capacitor around the same React code if a Play Store listing or a Bluetooth scale is ever wanted.

**Ownership:** this is a solo/one-agent build, but if split — **Frontend** owns the React screens (M1–M4 UI, the segmented-control brew form, chips, sliders, charts); **Backend/data** owns `db.ts` (Dexie schema), `methods.ts`, `taxonomy.ts`, `queries.ts`, and export/import. The contract between them is the typed data model in §3 + the named query functions in §4.

## 7. Risks & mitigations

1. **Data loss via IndexedDB eviction (highest).** Browsers can evict IndexedDB under storage pressure, and there's no server copy. *Mitigation:* request `navigator.storage.persist()` on first run; ship export/import in v1 (M5, not deferred) and nudge periodic backups. This is the single most important non-feature in the build.

2. **Logging friction kills the product.** If capturing a brew is slow, the app dies. *Mitigation:* the method registry + segmented control means the brew form only ever shows the ~4 fields relevant to the current method; sensible defaults (last-used method, remembered ratio/temp) pre-fill; chips + sliders are one-tap. Design for one-handed, few-tap logging — this is the core UX bet, not a nicety.

3. **Taxonomy churn breaking historical charts.** Expanding the flavor list later could orphan old tags. *Mitigation:* tags are stored as **stable ids mapped to fixed families**; charts aggregate on the 8 families, which never change. Adding terms only adds leaves — old data keeps charting correctly. This is why v1 commits to the id+family scheme even though it ships a flat list.

4. (Watch, not v1 blocker) **PWA reversibility.** If the user later needs the Play Store or native hardware, PWA→Capacitor is a near-zero-rewrite wrap of the same React code — so the PWA choice doesn't trap us.

**Prior-art credits:** method-aware brew forms + offline-first data-on-device ← [Beanconqueror](https://github.com/graphefruit/Beanconqueror) (idea/model, not codebase — different delivery); separate parameter sets per method ← Beanwise; roaster-notes vs. my-notes comparison ← BeanBook (extended here into charting the delta); LLM bag-scan auto-fill (v2) ← [B{rew}log](https://github.com/jnsgruk/brewlog) / Brewfolio; flavor vocabulary ← [SCA Flavor Wheel](https://notbadcoffee.com/flavor-wheel-en/) (curated subset in v1).

## 8. Handoff

**What gets built:** a React + TS PWA (Vite, Tailwind, Dexie/IndexedDB, Recharts, Workbox), no backend. Four Dexie stores (`beans`, `brews`, `tastings`, `photos`), a method registry, a curated flavor taxonomy, a query layer for charts, and JSON export/import.

**Data-layer owns:** `db.ts` (schema §3), `methods.ts` (the extensible method registry driving brew forms), `taxonomy.ts` (§5), `queries.ts` (chart-ready aggregations §4), export/import + `storage.persist()`.

**UI owns:** beans CRUD, the method-aware brew screen (segmented control swapping registry-driven params), the structured tasting screen (half-star, chips, sliders) + the roaster-vs-me comparison strip, and the Recharts views.

**Contract between them:** the §3 typed model (especially the `BrewParams` discriminated union and shared `FlavorTag` type) and the named functions in `queries.ts`. Shared truths both must honor: (a) `beans.roasterNotes` and `tastings.tastedNotes` are the **same** `FlavorTag[]` from `taxonomy.ts` — the comparison is set math, never text matching; (b) new brew methods enter only via a `BrewParams` union variant + a `methods.ts` entry, never new columns; (c) charts aggregate on the **8 fixed flavor families**, so taxonomy expansion is additive; (d) timestamps UTC in DB, Asia/Dubai in UI; (e) IDs are UUID strings.

**Open decisions needing the user:**
1. **Sync** — confirm v1 is single-phone with manual export/import (recommended). Multi-device sync only if you actually use two devices — say so and I'll spec Dexie Cloud vs. a hosted table.
2. **Units** — assuming grams + Celsius, no toggle. Confirm, or I'll add a units switch.
3. **Bitterness slider** — include the optional 4th slider in v1 (useful for espresso/Magnifica) or keep to acidity/body/sweetness? Default: include it.
4. **Starter taxonomy** — react to the 24-term list in §5; add/remove any terms you actually use before build (cheap now, stable-id-safe later either way).
5. **Milk types** — confirm the enum (`whole/skim/oat/almond/…`) covers what you use.
