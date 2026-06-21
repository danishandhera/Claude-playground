#!/usr/bin/env python3
"""
dubizzle_search.py - Filter dubizzle listings locally and render a visual page.

The whole point of this tool is to AVOID sending pages to an LLM. It fetches a
dubizzle search page once (or reads one you saved from your browser), extracts
the listings with BeautifulSoup, and writes a self-contained results.html that
has its own in-browser search/filter/sort. So you fetch once and then filter as
much as you like with zero tokens and zero re-runs.

Usage examples
--------------
# Fetch a search URL and build the page:
python3 dubizzle_search.py --url "https://uae.dubizzle.com/motors/used-cars/?keywords=corolla" --open

# You got blocked / want zero network: save the page in your browser
# (Cmd+S -> "Web Page, HTML only") then point the script at the file:
python3 dubizzle_search.py --file ~/Downloads/dubizzle.html --open

# Re-filter without re-fetching (uses the cached copy from the last --url run):
python3 dubizzle_search.py --no-fetch --keywords "gcc,2020" --max-price 60000 --open

The keyword / price flags below are optional pre-filters. You usually don't even
need them because the generated page lets you filter live in the browser.
"""

import argparse
import json
import os
import re
import sys
import webbrowser
from html import escape

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_page.html")
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.html")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


# --------------------------------------------------------------------------- #
# Fetch / load
# --------------------------------------------------------------------------- #
def get_html(args):
    if args.file:
        with open(args.file, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    if args.no_fetch:
        if not os.path.exists(CACHE_FILE):
            sys.exit("No cached page found. Run once with --url first.")
        with open(CACHE_FILE, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    if not args.url:
        sys.exit("Provide --url to fetch, --file to read a saved page, or --no-fetch.")

    import requests
    headers = {
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = requests.get(args.url, headers=headers, timeout=30)
    except Exception as e:
        sys.exit(f"Request failed: {e}")
    if resp.status_code != 200:
        print(f"Warning: HTTP {resp.status_code}. The page may be a block/challenge "
              f"page. If results look empty, save the page from your browser and use "
              f"--file instead.", file=sys.stderr)
    html = resp.text
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    return html


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #
def _first(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            return d[k]
    return None


def _looks_like_listing(d):
    if not isinstance(d, dict):
        return False
    has_title = any(k in d for k in ("name", "title", "headline", "subject"))
    has_price = any(k in d for k in ("price", "priceValue", "price_value", "amount"))
    return has_title and has_price


def _norm_price(val):
    if isinstance(val, dict):
        val = _first(val, ("value", "amount", "raw", "formatted")) or ""
    s = re.sub(r"[^\d.]", "", str(val))
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _abs_url(u, base):
    if not u:
        return None
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return base.rstrip("/") + u
    return u


def _base_of(url):
    m = re.match(r"(https?://[^/]+)", url or "")
    return m.group(1) if m else "https://uae.dubizzle.com"


def walk_json(obj, found):
    """Recursively collect listing-like dicts from any embedded JSON blob."""
    if isinstance(obj, dict):
        if _looks_like_listing(obj):
            found.append(obj)
        for v in obj.values():
            walk_json(v, found)
    elif isinstance(obj, list):
        for v in obj:
            walk_json(v, found)


def extract_from_json(soup, base):
    items, raw = [], []
    for tag in soup.find_all("script"):
        txt = tag.string or tag.get_text() or ""
        txt = txt.strip()
        if not txt or "{" not in txt:
            continue
        # __NEXT_DATA__ and most embedded state are plain JSON objects.
        candidates = []
        if tag.get("id") == "__NEXT_DATA__" or tag.get("type") == "application/json":
            candidates.append(txt)
        elif tag.get("type") == "application/ld+json":
            candidates.append(txt)
        else:
            m = re.search(r"\{.*\}", txt, re.DOTALL)
            if m and len(m.group(0)) > 200:
                candidates.append(m.group(0))
        for c in candidates:
            try:
                walk_json(json.loads(c), raw)
            except (ValueError, RecursionError):
                continue

    seen = set()
    for d in raw:
        title = _first(d, ("name", "title", "headline", "subject"))
        if not title or not isinstance(title, str):
            continue
        price = _norm_price(_first(d, ("price", "priceValue", "price_value", "amount")))
        img = _first(d, ("image", "imageUrl", "image_url", "photo", "thumbnail",
                         "coverPhoto", "cover_photo"))
        if isinstance(img, list) and img:
            img = img[0]
        if isinstance(img, dict):
            img = _first(img, ("url", "src", "href", "small", "medium"))
        link = _first(d, ("url", "permalink", "absoluteUrl", "absolute_url", "link",
                          "share_url"))
        if isinstance(link, dict):
            link = _first(link, ("url", "href"))
        loc = _first(d, ("location", "neighbourhood", "city", "area", "address",
                         "site"))
        if isinstance(loc, dict):
            loc = _first(loc, ("name", "label", "city", "area")) or ""
        key = (title.strip(), price)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "title": title.strip(),
            "price": price,
            "image": _abs_url(img if isinstance(img, str) else None, base),
            "link": _abs_url(link if isinstance(link, str) else None, base),
            "location": (loc or "").strip() if isinstance(loc, str) else "",
        })
    return items


def extract_from_html(soup, base):
    """Fallback: read rendered listing cards directly."""
    items, seen = [], set()
    anchors = soup.select('a[href*="/ad/"], a[href*="/listing"], article a[href]')
    for a in anchors:
        href = a.get("href", "")
        if not href:
            continue
        card = a.find_parent("article") or a.find_parent("li") or a
        text = card.get_text(" ", strip=True)
        pm = re.search(r"(AED|EGP|SAR|QAR|BHD|OMR|KWD|\$)\s*([\d,]+)", text)
        price = _norm_price(pm.group(2)) if pm else None
        title = (a.get("title") or a.get("aria-label") or "").strip()
        if not title:
            h = card.find(["h2", "h3"])
            title = h.get_text(strip=True) if h else (a.get_text(strip=True) or "")[:120]
        if not title:
            continue
        img_tag = card.find("img")
        img = None
        if img_tag:
            img = (img_tag.get("src") or img_tag.get("data-src")
                   or img_tag.get("data-lazy-src"))
            srcset = img_tag.get("srcset")
            if (not img or img.startswith("data:")) and srcset:
                img = srcset.split(",")[0].strip().split(" ")[0]
        key = (title, href)
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "title": title,
            "price": price,
            "image": _abs_url(img, base),
            "link": _abs_url(href, base),
            "location": "",
        })
    return items


def extract(html, base):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = extract_from_json(soup, base)
    if len(items) < 3:                       # JSON path thin -> try the DOM
        html_items = extract_from_html(soup, base)
        if len(html_items) > len(items):
            items = html_items
    return items


# --------------------------------------------------------------------------- #
# Optional CLI pre-filters
# --------------------------------------------------------------------------- #
def apply_filters(items, args):
    kws = [k.strip().lower() for k in (args.keywords or "").split(",") if k.strip()]
    excl = [k.strip().lower() for k in (args.exclude or "").split(",") if k.strip()]
    out = []
    for it in items:
        blob = (it["title"] + " " + it["location"]).lower()
        if kws and not all(k in blob for k in kws):
            continue
        if excl and any(k in blob for k in excl):
            continue
        if args.min_price is not None and (it["price"] is None or it["price"] < args.min_price):
            continue
        if args.max_price is not None and (it["price"] is None or it["price"] > args.max_price):
            continue
        out.append(it)
    return out


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dubizzle results ({count})</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0;
         background: #f5f6f8; color: #1a1a1a; }}
  header {{ position: sticky; top: 0; background: #e2231a; color: #fff;
            padding: 14px 18px; box-shadow: 0 2px 6px rgba(0,0,0,.15); z-index: 5; }}
  header h1 {{ margin: 0 0 8px; font-size: 18px; }}
  .controls {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
  .controls input, .controls select {{ padding: 7px 10px; border: 0; border-radius: 6px;
            font-size: 14px; }}
  .controls input[type=text] {{ flex: 1 1 240px; }}
  .controls input[type=number] {{ width: 110px; }}
  #count {{ font-size: 13px; opacity: .9; margin-left: auto; }}
  main {{ display: grid; gap: 14px; padding: 16px;
          grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); }}
  .card {{ background: #fff; border-radius: 10px; overflow: hidden; text-decoration: none;
           color: inherit; box-shadow: 0 1px 4px rgba(0,0,0,.1); display: flex;
           flex-direction: column; transition: transform .08s; }}
  .card:hover {{ transform: translateY(-2px); }}
  .thumb {{ width: 100%; aspect-ratio: 4/3; object-fit: cover; background: #ddd; }}
  .noimg {{ display: flex; align-items: center; justify-content: center; color: #999;
            font-size: 13px; }}
  .body {{ padding: 10px 12px 12px; }}
  .price {{ font-weight: 700; font-size: 16px; color: #e2231a; }}
  .title {{ font-size: 14px; margin: 4px 0; line-height: 1.3;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
            overflow: hidden; }}
  .loc {{ font-size: 12px; color: #777; }}
  .empty {{ padding: 40px; text-align: center; color: #777; grid-column: 1/-1; }}
</style></head>
<body>
<header>
  <h1>Dubizzle results — filtered locally, no tokens</h1>
  <div class="controls">
    <input id="q" type="text" placeholder="Search title / location…">
    <input id="min" type="number" placeholder="Min price">
    <input id="max" type="number" placeholder="Max price">
    <select id="sort">
      <option value="0">Sort: default</option>
      <option value="asc">Price: low → high</option>
      <option value="desc">Price: high → low</option>
    </select>
    <span id="count"></span>
  </div>
</header>
<main id="grid"></main>
<script>
const DATA = {data};
const grid = document.getElementById('grid');
const q = document.getElementById('q'), mn = document.getElementById('min'),
      mx = document.getElementById('max'), sort = document.getElementById('sort'),
      countEl = document.getElementById('count');
const fmt = n => n == null ? '—' : n.toLocaleString();
function render() {{
  const term = q.value.trim().toLowerCase();
  const lo = mn.value ? +mn.value : null, hi = mx.value ? +mx.value : null;
  let rows = DATA.filter(d => {{
    const blob = (d.title + ' ' + (d.location||'')).toLowerCase();
    if (term && !term.split(/\\s+/).every(t => blob.includes(t))) return false;
    if (lo != null && (d.price == null || d.price < lo)) return false;
    if (hi != null && (d.price == null || d.price > hi)) return false;
    return true;
  }});
  if (sort.value === 'asc') rows.sort((a,b)=>(a.price??1e15)-(b.price??1e15));
  if (sort.value === 'desc') rows.sort((a,b)=>(b.price??-1)-(a.price??-1));
  countEl.textContent = rows.length + ' / ' + DATA.length + ' shown';
  grid.innerHTML = rows.length ? rows.map(card).join('') :
    '<div class="empty">No matches. Loosen your filters.</div>';
}}
function card(d) {{
  const img = d.image
    ? `<img class="thumb" loading="lazy" src="${{d.image}}" onerror="this.replaceWith(Object.assign(document.createElement('div'),{{className:'thumb noimg',textContent:'no image'}}))">`
    : `<div class="thumb noimg">no image</div>`;
  const price = d.price != null ? 'AED ' + fmt(d.price) : 'Price n/a';
  return `<a class="card" href="${{d.link||'#'}}" target="_blank" rel="noopener">
    ${{img}}<div class="body"><div class="price">${{price}}</div>
    <div class="title">${{esc(d.title)}}</div>
    <div class="loc">${{esc(d.location||'')}}</div></div></a>`;
}}
function esc(s) {{ const e = document.createElement('div'); e.textContent = s||''; return e.innerHTML; }}
[q, mn, mx, sort].forEach(el => el.addEventListener('input', render));
render();
</script>
</body></html>"""


def render(items, out_path):
    data = json.dumps(items, ensure_ascii=False)
    html = PAGE.format(count=len(items), data=data)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(description="Filter dubizzle listings locally.")
    src = p.add_argument_group("source (pick one)")
    src.add_argument("--url", help="dubizzle search URL to fetch")
    src.add_argument("--file", help="path to an HTML page saved from your browser")
    src.add_argument("--no-fetch", action="store_true",
                     help="reuse the last fetched page (no network)")
    flt = p.add_argument_group("optional pre-filters")
    flt.add_argument("--keywords", help="comma list; ALL must appear in title/location")
    flt.add_argument("--exclude", help="comma list; drop items containing any of these")
    flt.add_argument("--min-price", type=float)
    flt.add_argument("--max-price", type=float)
    p.add_argument("--out", default=DEFAULT_OUT, help="output HTML path")
    p.add_argument("--open", action="store_true", help="open the page when done")
    args = p.parse_args()

    html = get_html(args)
    base = _base_of(args.url or "")
    items = extract(html, base)
    if not items:
        print("No listings found. dubizzle likely returned a challenge/JS page.\n"
              "Open the search in your browser, save it (Web Page, HTML only), then:\n"
              "  python3 dubizzle_search.py --file /path/to/saved.html --open",
              file=sys.stderr)
    filtered = apply_filters(items, args)
    render(filtered, args.out)
    print(f"Extracted {len(items)} listings, {len(filtered)} after filters.")
    print(f"Wrote {args.out}")
    if args.open:
        webbrowser.open("file://" + os.path.abspath(args.out))


if __name__ == "__main__":
    main()
