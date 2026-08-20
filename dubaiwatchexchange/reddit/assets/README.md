# Brand assets

Pastel desert-oasis palette — soft green on brown (locked 2026-08-19).

- `icon.svg` — square subreddit icon/avatar. Reddit crops to a circle; the design is safe for that.
- `banner.svg` — desktop banner (1920×384).
- `banner-mobile.svg` — mobile banner (1080×360, 3:1). The Reddit app overlays the community avatar bottom-left, so that corner is deliberately kept clear and the watch is left to the icon rather than duplicated.

## Export to PNG (Reddit needs raster)
Reddit's appearance settings take PNG/JPG. From this folder:

**`banner.png` (1920x384), `banner-mobile.png` (1080x360) and `icon.png` (512x512) are already exported in this folder** — upload those to Reddit directly. Only re-run the steps below if you change the SVGs.

### No-install method (built into macOS)

`qlmanage` renders it and `sips` fixes the padding. Both ship with macOS — nothing to install:

```bash
qlmanage -t -s 1920 -o . banner.svg && sips -c 384 1920 banner.svg.png --out banner.png && rm banner.svg.png
```

```bash
qlmanage -t -s 1080 -o . banner-mobile.svg && sips -c 360 1080 banner-mobile.svg.png --out banner-mobile.png && rm banner-mobile.svg.png
```

```bash
qlmanage -t -s 512 -o . icon.svg && mv icon.svg.png icon.png
```

The catch `qlmanage` has on its own: it pads output to a square, so a 1920x384 banner comes out 1920x1920 with white bars. The `sips -c 384 1920` crop above removes them (it crops centred, which lands exactly on the artwork). Square sources like the icon need no crop.

### If you'd rather use a real renderer

```bash
brew install librsvg
rsvg-convert -w 512  -h 512 icon.svg   -o icon.png
rsvg-convert -w 1920 -h 384 banner.svg -o banner.png
```

Better fidelity on gradients and text, but it is an install. Neither `rsvg-convert` nor ImageMagick was present as of 2026-08-20.

**Fonts:** the banner uses `Avenir Next` → `Helvetica Neue` → Arial. Both Avenir Next and Helvetica Neue ship with macOS, so it renders as designed here. If you ever export on another machine and the spacing looks off, it fell back to Arial — install the font or convert the text to outlines first.

## Where they go in Reddit
Mod Tools → Community Appearance:
- **Avatar / community icon** → `icon.png`
- **Banner (desktop)** → `banner.png`
- **Banner (mobile)** → `banner-mobile.png`  — confirm the size Reddit's uploader asks for; 1080x360 is the common recommendation but Reddit has changed it before
- **Colors** → base/header `#402D1D`, highlight `#7FA968`

Sizes recommended by Reddit shift over time; if it wants a taller banner, re-export at the requested height — the SVG scales cleanly.
