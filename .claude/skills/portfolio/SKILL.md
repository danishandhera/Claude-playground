---
name: portfolio
description: GM cockpit — roll up every project in the Claude-playground repo into one status view (at-a-glance, needs-attention, waiting-on-you, next action). Use when the user asks "where are we?", "portfolio status", "state of everything", runs /portfolio, or wants a cross-project review. Also cross-checks STATUS.md against real repo activity to catch stale/drifted projects, and can refresh STATUS.md.
---

# Portfolio — GM cockpit

One-screen "state of the empire" for the GM operating model. `STATUS.md` is the source of truth; this skill reads it, cross-checks it against **actual repo activity**, and surfaces what needs attention. Keep the output tight — it's a dashboard, not a report. Use the GM voice: brief, one clear recommendation, don't option-dump.

## Steps

1. **Freshness scan (deterministic, ~0 tokens).** Run:
   ```
   bash <this-skill-dir>/scan.sh
   ```
   It auto-locates the repo (works from Claude-home or from inside the repo). If it errors, pass the repo path: `bash <skill-dir>/scan.sh /Users/danishroshan/Claude-home/Claude-playground`.
   Output per project: last commit date + days ago, last file-edit date + days ago, and DIRTY = count of uncommitted changes.

2. **Read `STATUS.md`** at the repo root. This is the only file you read — do not open individual project files. (Repo is `.../Claude-home/Claude-playground`.)

3. **Produce the cockpit** using the format below, merging STATUS.md (the narrative) with scan.sh (the ground truth).

## Output format

Open with the date and a one-line headline, e.g. `2026-08-01 · 7 projects · 2 waiting on you · 1 stale · 1 drifted`.

**① At a glance** — the STATUS.md table: Project · Phase · Next action · Blocker.

**② ⚠️ Needs attention** — *computed*, not copied from STATUS:
- **Stale** — any project in an active phase (🔨 building / 🧪 validating / 📐 design) with **both** no commit AND no file edit in **7+ days** (from scan). State the day count.
- **Drift** — scan and STATUS disagree: DIRTY > 0 but STATUS says "shipped/pushed/on GitHub"; or STATUS "Last updated" predates the newest commit → STATUS is behind reality; or a scanned folder has **no entry in STATUS** → untracked project.
- **Blocked** — projects carrying a blocker in STATUS.
If this section is empty, say so in one line ("Nothing stale or drifted — STATUS matches the repo").

**③ ⏳ Waiting on you** — every item only the user can unblock: the "Open decisions awaiting user" list plus any next action whose Owner is **User**. This is the section the user acts on most — make it a clean checklist.

**④ ▶️ Highest-leverage next move** — pick the single best next action across the whole portfolio and recommend it. One rec, with a one-line why.

## Refresh mode

If invoked as `/portfolio refresh`, or the user asks to update status:
- Update STATUS.md **Last updated** to today.
- Reconcile drift the scan surfaced (e.g. bump a phase, clear a resolved blocker). **Do not rewrite project narratives without asking** — flag substantive changes and confirm first.
- **Do not git commit or push** — that's the GM's job and held until the user says "go" (per CONTEXT.md operating model).

## Notes
- Token efficiency: lean on scan.sh for freshness; read only STATUS.md.
- New projects appear in the scan automatically (auto-discovered folders), so they surface as "untracked in STATUS" before anyone writes them up.
