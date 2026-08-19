# Home-Server Workflow — iMac as the always-on brain

**Decided 2026-08-16. Status: PLAN (not yet built).** Do the hands-on iMac setup later; this is the blueprint.

## Goal
All computation runs on an always-on **iMac** (the "brain"). The user drives conversations + work from the **MacBook** or **phone**, which are thin clients attaching to the *same live session* over Tailscale. One conversation, carried between devices, no syncing.

## Topology
```
iMac (always-on)
 ├─ Claude Code in a persistent tmux session   ← the conversation lives here
 ├─ canonical repo + ~/.claude memory           ← source of truth
 ├─ project services: Stash API + mobile UI, helthi, enrichment/cron jobs
 └─ git → GitHub (off-box backup)
        ⇅  Tailscale (private encrypted mesh; works home or away)
 MacBook: ssh imac → tmux attach        Phone: Blink/mosh → tmux attach
                                         + project web UIs in the browser
```

**Why one conversation everywhere:** Claude runs inside one `tmux` session on the iMac. Detach on the laptop, reattach from the phone → same process, same context. Beats the cloud (claude.ai/code) route because the same box also hosts the compute and local services.

## Setup — 5 phases
1. **Backup + relocate home:** push all commits; clone repo + move `~/.claude` memory onto the iMac as the new canonical copy. Laptop keeps a working clone.
2. **Tailscale** on iMac + MacBook + phone → private mesh, stable `imac` hostname, no port-forwarding.
3. **iMac as server:** enable Remote Login (SSH); set Energy Saver to never sleep (+ wake-on-network); install toolchain — git, node, python, `gh` (auth), whisper.cpp, Claude Code.
4. **Persistent session:** `tmux` (+ `mosh` for the phone, survives network drops); auto-start on boot; project services under `launchd` to self-restart.
5. **Clients:** MacBook `ssh imac` alias; phone installs **Blink Shell** (supports mosh) → attach.

## Intel-iMac tuning (this machine is an Intel iMac)
- Fine as an always-on server. No Apple Neural Engine → Whisper runs on CPU/GPU (Metal on the discrete GPU if present), slower than Apple Silicon.
- For **Stash** enrichment: prefer smaller Whisper models (`base.en`/`tiny.en`); let the always-on box grind the backfill overnight (it's a one-time, cached, resumable job — speed matters little).
- OCR: Apple Vision still works on Intel; Tesseract is the cross-platform fallback.

## Tradeoff to accept
Typing long prompts on a phone keyboard over SSH is fine for **steering / approvals / quick work** (remote control), not luxurious for heavy drafting. MacBook stays the comfortable seat; phone is the nudge/approve device. `mosh` keeps the phone session alive across networks.

## Security
SSH + all services exposed **only over Tailscale**, never the public internet. Repo still pushes to GitHub as off-box backup.
