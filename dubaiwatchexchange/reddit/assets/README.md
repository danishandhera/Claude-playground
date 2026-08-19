# Brand assets

Pastel desert-oasis palette — soft green on brown (locked 2026-08-19).

- `icon.svg` — square subreddit icon/avatar. Reddit crops to a circle; the design is safe for that.
- `banner.svg` — wide banner (10:2.5 ratio, 1920×384).

## Export to PNG (Reddit needs raster)
Reddit's appearance settings take PNG/JPG. From this folder:

**Nothing suitable is installed on this Mac yet** (checked 2026-08-19 — no `rsvg-convert`, no ImageMagick). Install one first:

```bash
brew install librsvg          # smallest, best SVG fidelity

rsvg-convert -w 512  -h 512 icon.svg   -o icon.png
rsvg-convert -w 1920 -h 384 banner.svg -o banner.png
```

Alternative if you'd rather not install anything: open the `.svg` in Chrome/Safari, or use any online SVG→PNG converter.

⚠️ **Don't use `qlmanage` for the final export.** It works for a quick preview but pads output to a square (a 1920×384 banner comes out 1920×1920 with white bars), which Reddit will letterbox.

**Fonts:** the banner uses `Avenir Next` → `Helvetica Neue` → Arial. Both Avenir Next and Helvetica Neue ship with macOS, so it renders as designed here. If you ever export on another machine and the spacing looks off, it fell back to Arial — install the font or convert the text to outlines first.

## Where they go in Reddit
Mod Tools → Community Appearance:
- **Avatar / community icon** → `icon.png`
- **Banner (desktop)** → `banner.png`  (also set the mobile banner image)
- **Colors** → base/header `#402D1D`, highlight `#7FA968`

Sizes recommended by Reddit shift over time; if it wants a taller banner, re-export at the requested height — the SVG scales cleanly.
