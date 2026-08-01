# Stash

A personal, searchable home for everything you've saved on Instagram — so the movies, songs, workouts, Dubai food spots, travel spots, and anime you bookmark actually get used.

## Problem
Hundreds/thousands of Instagram saves across shareable collections that are impossible to search or act on inside the app.

## Approach (two phases)

### Phase 1 — Organize & search  *(current)*
- **Source:** Instagram's official **"Download Your Information"** export (JSON). Gives every saved post as a URL, grouped by the collection it was filed in, with save dates. Legit, complete, token-free.
- **Build:** parser → local dataset → a **mobile web app**: filter by collection/category, full-text search, clickable links, sorted by date saved.
- **Leverages:** the user already categorized saves into collections, so category is mostly free from folder labels.

### Phase 2 — Understand & recommend  *(later, if Phase 1 proves out)*
- Enrich each save with caption/content via `instaloader` (user's own session), rate-limited + cached forever.
- Cheap-LLM tagging + summaries → "summarize my anime saves / what should I watch next."
- ToS-gray + token cost → deliberately deferred behind Phase 1.

## Access
Mobile-accessible web app (plugs into the cross-device claude.ai/code + repo setup).

## Status
💡 Scaffolded 2026-08-01. **Blocked on:** user requesting the Instagram data export (JSON, "Saved" only, All time). Parser is built once we have a real export sample to see the exact schema.
