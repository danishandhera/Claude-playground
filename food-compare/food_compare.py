#!/usr/bin/env python3
"""
food_compare.py - Compare the cost of the same order across UAE food-delivery
apps (Talabat first; Deliveroo / Careem / Noon / Smiles / Keeta to follow),
entirely on your own machine.

Why this exists
---------------
Every delivery app prices the same restaurant differently once you add up item
prices + delivery fee + service fee. Normally you'd add the same items to a cart
in each app to find the cheapest. This tool removes that: you save each app's
restaurant page once (the apps bot-block plain scripts, so we use the browser's
"Save Page As" like the dubizzle tool), it extracts the menu + fees locally, and
then you define your order ONCE and it prints the cheapest app.

No page contents are ever sent to an LLM, so using it costs zero tokens.

Workflow
--------
1. Parse a saved restaurant page into a local menu (per app):

     python3 food_compare.py parse --app talabat --file ~/Downloads/talabat.html

   (repeat for each app once you have more adapters; same restaurant)

2. List what was parsed so you can see exact item names:

     python3 food_compare.py menu --app talabat

3. Compare an order across every app you've parsed:

     python3 food_compare.py compare --items "Chicken Biryani:2, Garlic Naan:3, Coke"
     python3 food_compare.py compare --items @order.txt --open

Item names are fuzzy-matched to the menu, so you don't have to type them exactly.
Quantity defaults to 1; use "name:qty".

This is an ESTIMATE tool (item prices + delivery fee). App-specific service fees,
small-order fees, promo codes and subscription discounts (Talabat Pro etc.) are
only visible at checkout and are added later via an exact-total mode.
"""

import argparse
import difflib
import json
import os
import re
import sys
import webbrowser
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
MENU_DIR = os.path.join(HERE, "menus")
CACHE_DIR = os.path.join(HERE, ".cache")
DEFAULT_OUT = os.path.join(HERE, "comparison.html")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

PRICE_RE = re.compile(r"(?:AED|aed|د\.إ|dhs?)?\s*([0-9]+(?:\.[0-9]{1,2})?)", re.I)


# --------------------------------------------------------------------------- #
# Page loading (mirrors the dubizzle tool: --file is the reliable path)
# --------------------------------------------------------------------------- #
def load_html(args):
    if args.file:
        with open(args.file, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    if args.url:
        import requests
        headers = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
        try:
            r = requests.get(args.url, headers=headers, timeout=30)
            return r.text
        except Exception as e:  # noqa: BLE001
            sys.exit(f"Fetch failed ({e}). Save the page in your browser and use --file.")
    sys.exit("Provide --file (recommended) or --url.")


# --------------------------------------------------------------------------- #
# Generic helpers
# --------------------------------------------------------------------------- #
def to_number(val):
    """Coerce a price-ish value (int/float/str) to a float, or None."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        m = PRICE_RE.search(val)
        if m:
            return float(m.group(1))
    return None


def norm(name):
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


# --------------------------------------------------------------------------- #
# Adapter: Talabat
# --------------------------------------------------------------------------- #
# Strategy: Talabat is a Next.js app, so the richest source is the hydration
# JSON embedded in the page (__NEXT_DATA__ / __APOLLO_STATE__ / window state).
# We walk that JSON for objects that look like menu items {name, price}. If no
# usable JSON is found we fall back to scraping the rendered DOM.

ITEM_NAME_KEYS = ("name", "title", "itemname", "displayname", "productname")
ITEM_PRICE_KEYS = ("price", "unitprice", "originalprice", "baseprice",
                    "amount", "value", "discountedprice")


def _iter_json_blobs(html):
    """Yield parsed JSON objects embedded in <script> tags."""
    # __NEXT_DATA__
    for m in re.finditer(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html, re.S | re.I,
    ):
        try:
            yield json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            pass
    # generic application/json scripts and common window assignments
    for m in re.finditer(
        r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
        html, re.S | re.I,
    ):
        try:
            yield json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            pass
    for m in re.finditer(
        r'window\.__[A-Z_]+__\s*=\s*({.*?})\s*;?\s*</script>', html, re.S,
    ):
        try:
            yield json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            pass


def _walk_items(obj, found):
    """Recursively collect {name, price} dicts from a JSON structure."""
    if isinstance(obj, dict):
        lower = {k.lower(): k for k in obj.keys()}
        name_key = next((lower[k] for k in ITEM_NAME_KEYS if k in lower), None)
        price_key = next((lower[k] for k in ITEM_PRICE_KEYS if k in lower), None)
        if name_key and price_key:
            name = obj[name_key]
            price = to_number(obj[price_key])
            if isinstance(name, str) and name.strip() and price and price > 0:
                found.append((name.strip(), price))
        for v in obj.values():
            _walk_items(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _walk_items(v, found)


def _find_fees(html, blobs):
    """Best-effort delivery fee / minimum order extraction."""
    delivery = None
    minimum = None
    text = re.sub(r"<[^>]+>", " ", html)
    m = re.search(r"deliver\w*\s*(?:fee|charge)[^0-9]{0,20}(AED)?\s*([0-9]+(?:\.[0-9]+)?)",
                  text, re.I)
    if m:
        delivery = float(m.group(2))
    elif re.search(r"free\s+deliver", text, re.I):
        delivery = 0.0
    m = re.search(r"min\w*\s*(?:order)?[^0-9]{0,20}(AED)?\s*([0-9]+(?:\.[0-9]+)?)",
                  text, re.I)
    if m:
        minimum = float(m.group(2))
    return delivery, minimum


def parse_talabat(html):
    items = {}
    # 1) JSON hydration (preferred)
    for blob in _iter_json_blobs(html):
        found = []
        _walk_items(blob, found)
        for name, price in found:
            key = norm(name)
            # keep the first/cheapest seen for a given name
            if key not in items or price < items[key]["price"]:
                items[key] = {"name": name, "price": price}

    # 2) DOM fallback if JSON yielded nothing useful
    if not items:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            sys.exit("pip install --user beautifulsoup4")
        soup = BeautifulSoup(html, "html.parser")
        for el in soup.find_all(string=PRICE_RE):
            price = to_number(str(el))
            if not price or price <= 0:
                continue
            # walk up to a container, find a plausible name nearby
            container = el.parent
            for _ in range(3):
                if container is None:
                    break
                name = None
                for tag in container.find_all(["h2", "h3", "h4", "p", "span", "div"]):
                    t = tag.get_text(" ", strip=True)
                    if t and not PRICE_RE.fullmatch(t) and 2 < len(t) < 80:
                        name = t
                        break
                if name:
                    key = norm(name)
                    if key not in items:
                        items[key] = {"name": name, "price": price}
                    break
                container = container.parent

    restaurant = _restaurant_name(html)
    delivery, minimum = _find_fees(html, None)
    return {
        "app": "talabat",
        "restaurant": restaurant,
        "delivery_fee": delivery,
        "min_order": minimum,
        "items": sorted(items.values(), key=lambda x: x["name"].lower()),
    }


def _restaurant_name(html):
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    if m:
        return re.split(r"[|\-–]", m.group(1))[0].strip()
    return "Unknown restaurant"


ADAPTERS = {
    "talabat": parse_talabat,
    # "deliveroo": parse_deliveroo,   # next
    # "careem": parse_careem,
    # "noon": parse_noon,
    # "smiles": parse_smiles,
    # "keeta": parse_keeta,
}


# --------------------------------------------------------------------------- #
# Menu cache
# --------------------------------------------------------------------------- #
def menu_path(app):
    return os.path.join(MENU_DIR, f"{app}.json")


def save_menu(menu):
    os.makedirs(MENU_DIR, exist_ok=True)
    with open(menu_path(menu["app"]), "w", encoding="utf-8") as f:
        json.dump(menu, f, ensure_ascii=False, indent=2)


def load_menu(app):
    p = menu_path(app)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def all_menus():
    if not os.path.isdir(MENU_DIR):
        return []
    out = []
    for fn in sorted(os.listdir(MENU_DIR)):
        if fn.endswith(".json"):
            with open(os.path.join(MENU_DIR, fn), "r", encoding="utf-8") as f:
                out.append(json.load(f))
    return out


# --------------------------------------------------------------------------- #
# Order parsing + matching
# --------------------------------------------------------------------------- #
def parse_order(spec):
    """'Biryani:2, Coke' or '@file' -> [(name, qty), ...]"""
    if spec.startswith("@"):
        with open(os.path.expanduser(spec[1:]), "r", encoding="utf-8") as f:
            spec = f.read()
    out = []
    for chunk in re.split(r"[,\n]", spec):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            name, qty = chunk.rsplit(":", 1)
            try:
                qty = int(qty.strip())
            except ValueError:
                name, qty = chunk, 1
        else:
            name, qty = chunk, 1
        out.append((name.strip(), qty))
    return out


def match_item(name, menu_items):
    """Fuzzy-match a requested name to a menu item. Returns (item, score)."""
    names = [it["name"] for it in menu_items]
    keys = [norm(n) for n in names]
    target = norm(name)
    # exact / substring first
    for i, k in enumerate(keys):
        if k == target or target in k or k in target:
            return menu_items[i], 1.0
    close = difflib.get_close_matches(target, keys, n=1, cutoff=0.6)
    if close:
        i = keys.index(close[0])
        score = difflib.SequenceMatcher(None, target, close[0]).ratio()
        return menu_items[i], score
    return None, 0.0


def price_order(menu, order):
    rows = []
    subtotal = 0.0
    missing = []
    for name, qty in order:
        item, score = match_item(name, menu["items"])
        if item:
            line = item["price"] * qty
            subtotal += line
            rows.append({"req": name, "matched": item["name"], "qty": qty,
                         "unit": item["price"], "line": line, "score": score})
        else:
            missing.append(name)
            rows.append({"req": name, "matched": None, "qty": qty,
                         "unit": None, "line": None, "score": 0})
    delivery = menu.get("delivery_fee")
    total = subtotal + (delivery or 0.0)
    return {
        "app": menu["app"],
        "restaurant": menu.get("restaurant"),
        "rows": rows,
        "subtotal": subtotal,
        "delivery": delivery,
        "total": total,
        "missing": missing,
        "min_order": menu.get("min_order"),
    }


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def fmt(v):
    return "—" if v is None else f"{v:.2f}"


def print_compare(results):
    results = sorted(results, key=lambda r: r["total"])
    # Only crown a winner among apps that matched the WHOLE order — an app that
    # silently dropped an item would otherwise look "cheapest" unfairly.
    complete = [r for r in results if not r["missing"]]
    cheapest = complete[0]["total"] if complete else None
    print()
    for r in results:
        tag = "  ✅ CHEAPEST" if (not r["missing"] and r["total"] == cheapest) else ""
        print(f"=== {r['app'].upper()} — {r['restaurant']} ==={tag}")
        for row in r["rows"]:
            if row["matched"]:
                warn = "  ⚠️fuzzy" if row["score"] < 0.85 else ""
                print(f"   {row['qty']}× {row['matched']:<32} "
                      f"AED {fmt(row['unit'])}  = {fmt(row['line'])}{warn}")
            else:
                print(f"   {row['qty']}× {row['req']:<32} NOT FOUND")
        print(f"   {'Subtotal':<40} AED {fmt(r['subtotal'])}")
        print(f"   {'Delivery':<40} AED {fmt(r['delivery'])}")
        print(f"   {'TOTAL':<40} AED {fmt(r['total'])}")
        if r["min_order"] and r["subtotal"] < r["min_order"]:
            print(f"   ⚠️ below minimum order (AED {fmt(r['min_order'])})")
        if r["missing"]:
            print(f"   ⚠️ not found: {', '.join(r['missing'])}")
        print()
    if len(results) > 1:
        if cheapest is not None:
            winner = next(r for r in complete if r["total"] == cheapest)
            save = complete[-1]["total"] - cheapest
            print(f"Cheapest (full order): {winner['app'].upper()} at "
                  f"AED {fmt(cheapest)} (saves AED {fmt(save)} vs priciest).")
        if len(complete) < len(results):
            incomplete = [r["app"].upper() for r in results if r["missing"]]
            print(f"⚠️ Totals NOT directly comparable — {', '.join(incomplete)} "
                  "missing item(s). Fix names with `menu --app <app>`, then re-run.")


def write_html(results, out):
    results = sorted(results, key=lambda r: r["total"])
    rows = []
    for i, r in enumerate(results):
        cls = "cheap" if i == 0 else ""
        items = "".join(
            f"<tr><td>{row['qty']}× {escape(row['matched'] or row['req'])}</td>"
            f"<td class='r'>{fmt(row['unit'])}</td>"
            f"<td class='r'>{fmt(row['line'])}</td></tr>"
            for row in r["rows"]
        )
        rows.append(f"""
        <div class="card {cls}">
          <h2>{escape(r['app'].upper())} <small>{escape(r['restaurant'] or '')}</small></h2>
          <table>{items}
            <tr class="sep"><td>Subtotal</td><td></td><td class="r">{fmt(r['subtotal'])}</td></tr>
            <tr><td>Delivery</td><td></td><td class="r">{fmt(r['delivery'])}</td></tr>
            <tr class="tot"><td>TOTAL (AED)</td><td></td><td class="r">{fmt(r['total'])}</td></tr>
          </table>
        </div>""")
    html = f"""<!doctype html><meta charset=utf-8><title>Food price comparison</title>
<style>
 body{{font:15px -apple-system,system-ui,sans-serif;background:#0f1115;color:#e6e6e6;margin:0;padding:24px}}
 .wrap{{display:flex;gap:16px;flex-wrap:wrap}}
 .card{{background:#1a1d24;border:1px solid #2a2f3a;border-radius:12px;padding:16px;min-width:300px;flex:1}}
 .card.cheap{{border-color:#3ddc84;box-shadow:0 0 0 1px #3ddc84}}
 h2{{margin:0 0 10px;font-size:17px}} small{{color:#8b93a7;font-weight:400}}
 table{{width:100%;border-collapse:collapse}} td{{padding:4px 0}}
 .r{{text-align:right;font-variant-numeric:tabular-nums}}
 .sep td{{border-top:1px solid #2a2f3a;padding-top:8px;color:#8b93a7}}
 .tot td{{font-weight:700;font-size:16px;padding-top:6px}}
 .card.cheap .tot td{{color:#3ddc84}}
</style>
<h1>Order comparison</h1><div class="wrap">{''.join(rows)}</div>"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def cmd_parse(args):
    if args.app not in ADAPTERS:
        sys.exit(f"No adapter for '{args.app}'. Available: {', '.join(ADAPTERS)}")
    html = load_html(args)
    menu = ADAPTERS[args.app](html)
    if not menu["items"]:
        sys.exit("No menu items found. Make sure you saved the restaurant menu "
                 "page (scrolled so items loaded) as 'Web Page, HTML Only'.")
    save_menu(menu)
    print(f"Parsed {len(menu['items'])} items from {menu['restaurant']} "
          f"({args.app}). Delivery fee: {fmt(menu['delivery_fee'])}.")
    print(f"Saved -> {menu_path(args.app)}")
    print("Review with:  python3 food_compare.py menu --app", args.app)


def cmd_menu(args):
    menu = load_menu(args.app)
    if not menu:
        sys.exit(f"No parsed menu for '{args.app}'. Run 'parse' first.")
    print(f"{menu['restaurant']} ({args.app}) — {len(menu['items'])} items, "
          f"delivery {fmt(menu['delivery_fee'])}")
    for it in menu["items"]:
        print(f"  AED {it['price']:>7.2f}  {it['name']}")


def cmd_compare(args):
    menus = all_menus()
    if not menus:
        sys.exit("No parsed menus yet. Run 'parse' for at least one app first.")
    order = parse_order(args.items)
    if not order:
        sys.exit("Empty order. Use --items 'Name:qty, Name'")
    results = [price_order(m, order) for m in menus]
    print_compare(results)
    if args.open or args.out:
        out = write_html(results, args.out or DEFAULT_OUT)
        print(f"\nWrote {out}")
        if args.open:
            webbrowser.open(f"file://{out}")
    if len(menus) == 1:
        print(f"\n(Only '{menus[0]['app']}' parsed so far — parse another app's "
              "page for the same restaurant to get a real comparison.)")


def main():
    p = argparse.ArgumentParser(description="Compare food-delivery prices locally.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("parse", help="parse a saved restaurant page into a menu")
    pp.add_argument("--app", required=True, help="talabat (more coming)")
    pp.add_argument("--file", help="saved HTML page (recommended)")
    pp.add_argument("--url", help="try a direct fetch (usually bot-blocked)")
    pp.set_defaults(func=cmd_parse)

    pm = sub.add_parser("menu", help="list parsed items for an app")
    pm.add_argument("--app", required=True)
    pm.set_defaults(func=cmd_menu)

    pc = sub.add_parser("compare", help="price an order across all parsed apps")
    pc.add_argument("--items", required=True,
                    help="'Biryani:2, Naan:3, Coke' or @order.txt")
    pc.add_argument("--out", help="HTML output path")
    pc.add_argument("--open", action="store_true", help="open the HTML result")
    pc.set_defaults(func=cmd_compare)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
