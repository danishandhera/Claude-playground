---
name: task-observer
description: Meta-skill that watches your work sessions, captures corrections and judgment calls, and turns them into skill improvements automatically. Use during any task-oriented session to build and improve your skill library over time. Activates automatically when you begin multi-step work.
---

# Task Observer

A meta-skill that runs quietly alongside your work, notices what's working and what isn't, and produces structured improvement recommendations for your entire skill library — including itself.

## What It Does

During any work session, the observer watches for three signals:

1. **Corrections** — when you redirect, rephrase, or override Claude's output, that's a signal a skill could be clearer
2. **Gaps** — when you do something manually that could be systematised, that's a candidate for a new skill
3. **Blind spots** — when the observer itself misses something, it logs that too

At the end of each session, it produces a structured observation log with specific, actionable improvement suggestions.

## How to Use

No setup required. Simply work normally. At the end of a session, say:

> "Summarise your observations from this session."

The observer will produce a log like:

```
OBSERVATION LOG — [date]
Session type: [e.g., content writing, code review, research]

CORRECTIONS NOTICED
- [Skill affected]: [What was corrected] → [Suggested improvement]

GAPS IDENTIFIED
- [Task pattern]: [Description] → [Candidate skill name + draft]

SELF-IMPROVEMENTS
- [Observer methodology note]
```

## Modes

**Cowork / Claude Code**: Observer writes logs to the filesystem so improvements persist between sessions.

**Claude.ai web**: Observer produces a handoff document at session end. Copy it and use it to update your skills manually.

## Review Process

The observer never modifies skills directly. Review each suggestion and apply only the ones you agree with. You stay in control.

## Examples

**Correction detected:**
> User asked for a formal email, corrected Claude's casual opener → Observer notes: `internal-comms` skill needs a tone selector.

**Gap detected:**
> User manually formatted a table three times → Observer drafts a `table-formatter` skill candidate.

**Self-improvement:**
> Observer triggered too eagerly on a simple Q&A → Adds note to only activate during task-oriented sessions with 3+ steps.

## Tips

- Run the observer during complex, multi-step tasks for the richest observations
- Review the log at the end of every session, not once a week — recency matters
- When the observer drafts a new skill candidate, use `skill-creator` to polish it before uploading

## Credits

Inspired by [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all). Licensed CC BY 4.0.
