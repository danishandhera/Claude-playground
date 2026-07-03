#!/usr/bin/env python3
"""
benchmark.py - guard against parser rot (selectors / hydration-JSON shape drift).

Each fixture pairs a real saved restaurant page with the TRUE checkout total of a
real order placed from it. The benchmark re-parses the page, prices the same
order, and asserts the estimate lands within tolerance of ground truth. Run it
after any parser change; if an app silently restructures its page, this fails
loudly instead of the tool quietly returning wrong prices.

This is intentionally tiny — one script, no framework.

Add a fixture
-------------
1. Save the restaurant page (browser -> "Web Page, HTML Only") into fixtures/.
2. Place a real order on that app and note the exact totals from checkout.
3. Add an entry to fixtures/fixtures.json:

   {
     "app": "talabat",
     "page": "talabat_bombay_chowk.html",
     "order": "Chicken Biryani:2, Garlic Naan:3",
     "ground_truth": { "subtotal": 82.0, "delivery": 7.0, "total": 89.0 },
     "tolerance_pct": 2.0
   }

   Only fields present in ground_truth are checked (so an estimate-mode fixture
   can assert subtotal+delivery while skipping service/small-order fees).

Run:  python3 benchmark.py
"""

import json
import os
import sys

import food_compare as fc

HERE = os.path.dirname(os.path.abspath(__file__))
FIX_DIR = os.path.join(HERE, "fixtures")
FIX_FILE = os.path.join(FIX_DIR, "fixtures.json")


def load_fixtures():
    if not os.path.exists(FIX_FILE):
        return []
    with open(FIX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def run():
    fixtures = load_fixtures()
    if not fixtures:
        print("No fixtures yet — add a real saved order to fixtures/fixtures.json.")
        print("See the docstring in benchmark.py for the format.")
        return 0  # nothing to verify is not a failure

    failures = 0
    for fx in fixtures:
        app = fx["app"]
        page = os.path.join(FIX_DIR, fx["page"])
        if app not in fc.ADAPTERS:
            print(f"SKIP {app}: no adapter")
            continue
        with open(page, "r", encoding="utf-8", errors="replace") as f:
            menu = fc.ADAPTERS[app](f.read())
        order = fc.parse_order(fx["order"])
        result = fc.price_order(menu, order)
        tol = fx.get("tolerance_pct", 2.0)
        gt = fx["ground_truth"]

        print(f"\n=== {app} — {fx['page']} ===")
        ok = True
        if result["missing"]:
            ok = False
            print(f"  FAIL: items not matched: {', '.join(result['missing'])}")
        for field, truth in gt.items():
            got = result.get(field)
            if got is None:
                ok = False
                print(f"  FAIL {field}: parser returned None (expected {truth})")
                continue
            diff_pct = abs(got - truth) / truth * 100 if truth else (0 if got == 0 else 100)
            mark = "ok" if diff_pct <= tol else "FAIL"
            if mark == "FAIL":
                ok = False
            print(f"  {mark} {field}: got {got:.2f} vs truth {truth:.2f} "
                  f"({diff_pct:.1f}% off, tol {tol}%)")
        if not ok:
            failures += 1

    print(f"\n{len(fixtures) - failures}/{len(fixtures)} fixtures passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
