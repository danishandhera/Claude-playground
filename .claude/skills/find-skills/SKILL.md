---
name: find-skills
description: Discover reusable Claude skills from public GitHub registries by task keywords, evaluate fit, and install the best one. Use when the user asks "is there a skill for X?", "find a skill for [task]", "search for skills", or starts work in a new tool/framework that a community skill might already cover. Provider-neutral; uses gh/curl only.
---

# Find Skills

Search public Claude-skill registries for a community skill matching the user's task, evaluate the candidates, and install the best fit. No special CLI required — uses `gh` (or `curl`) against GitHub.

## Registries to search (in order)
1. **buildwithclaude** — `davepoon/buildwithclaude` (the largest hub: `plugins/all-skills/skills/*`).
2. **vercel-labs/skills** — `vercel-labs/skills`.
3. Broad GitHub code search for `filename:SKILL.md` matching the task keywords.

## Workflow
1. **Frame the need** in one sentence (task + toolchain/framework/platform).
2. **Search** by keyword. Useful commands:
   ```bash
   # List the big hub's skill catalogue, then grep locally:
   gh api "repos/davepoon/buildwithclaude/git/trees/HEAD?recursive=1" \
     | python3 -c 'import sys,json;[print(t["path"]) for t in json.load(sys.stdin)["tree"] if t["path"].endswith("SKILL.md")]' \
     | grep -i "<keyword>"

   # Broad code search across GitHub by skill frontmatter name:
   gh api -X GET search/code -f q='"name: <keyword>" filename:SKILL.md'
   ```
3. **Evaluate** each candidate — read its `SKILL.md` frontmatter (`description`) and body. For each, note: what it does, required tools/deps, any hooks or network calls, and license. **Flag anything that installs hooks, runs a background service, or requires a proprietary CLI** — those aren't drop-in and need explicit user sign-off.
4. **Recommend one** best-fit skill (and one fallback), in the GM voice — one clear pick with a one-line why.
5. **Install** on user OK: copy the skill folder into `Claude-playground/.claude/skills/<name>/` (travels to mobile via the repo) and symlink it into `~/.claude/skills/<name>/` for laptop use. Verify the raw `SKILL.md` before writing — never install code blind.

## Output format
```
NEED: <one-line task>
CANDIDATES
- <name> (<repo>) — <what it does> · deps: <...> · ⚠️ <hooks/network/license flags or "clean drop-in">
RECOMMENDATION: <name> — <why>
```

## Notes
- Prefer clean, prompt-only skills. De-brand product-locked copies (skills hardwired to a specific CLI/product) before installing, or find a neutral variant.
- After installing, tell the user the trigger phrase from the skill's `description` so they know how to invoke it.
