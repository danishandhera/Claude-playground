# Brand assets

Pastel desert-oasis palette — soft green on brown (locked 2026-08-19).

- `icon.svg` — square subreddit icon/avatar. Reddit crops to a circle; the design is safe for that.
- `banner.svg` — wide banner (10:2.5 ratio, 1920×384).

## Export to PNG (Reddit needs raster)
Reddit's appearance settings take PNG/JPG. From this folder:

```bash
# with rsvg-convert (brew install librsvg)
rsvg-convert -w 512  -h 512 icon.svg   > icon.png
rsvg-convert -w 1920 -h 384 banner.svg > banner.png

# or with ImageMagick
magick -background none icon.svg   -resize 512x512  icon.png
magick -background none banner.svg -resize 1920x384 banner.png
```

No tools installed? Open the `.svg` in a browser and screenshot, or drop it into any online SVG→PNG converter.

## Where they go in Reddit
Mod Tools → Community Appearance:
- **Avatar / community icon** → `icon.png`
- **Banner (desktop)** → `banner.png`  (also set the mobile banner image)
- **Colors** → base/header `#402D1D`, highlight `#7FA968`

Sizes recommended by Reddit shift over time; if it wants a taller banner, re-export at the requested height — the SVG scales cleanly.
