# food-compare — UAE delivery price comparison (local, zero-token)

Compare the cost of the **same order across delivery apps** (Talabat first;
Deliveroo / Careem / Noon / Smiles / Keeta to follow) without adding items to a
cart in each app. Everything runs on your machine; no page is sent to an LLM, so
using it costs **zero tokens** — same idea as the dubizzle tool.

It's an **estimate**: item prices + delivery fee. Service fees, small-order fees,
promo codes and subscription discounts (Talabat Pro etc.) show up only at
checkout and are added later in an exact-total mode.

## Setup (one time)

```bash
python3 -m pip install --user beautifulsoup4 requests
```

## How it works

The apps bot-block plain scripts, so you grab each page from the browser where
it already loads (exactly like the dubizzle tool):

1. **Parse a restaurant** — open the restaurant on the app, scroll so the menu
   loads, then **File → Save Page As… → "Web Page, HTML Only"** and run:

   ```bash
   python3 food_compare.py parse --app talabat --file ~/Downloads/talabat.html
   ```

2. **Check what it extracted** (so you know the exact item names):

   ```bash
   python3 food_compare.py menu --app talabat
   ```

3. **Compare an order** across every app you've parsed for that restaurant:

   ```bash
   python3 food_compare.py compare --items "Chicken Biryani:2, Garlic Naan:3, Coke" --open
   ```

   - `name:qty` (qty defaults to 1). Item names are **fuzzy-matched**, so
     near-enough spelling works; `⚠️fuzzy` marks low-confidence matches.
   - `--items @order.txt` reads the order from a file (one item per line).
   - `--open` also writes and opens `comparison.html` (a visual side-by-side).

To get a real comparison, parse the **same restaurant** on a second app once more
adapters exist.

## Status

| App | Adapter |
|-----|---------|
| Talabat | ✅ (verify selectors against a real saved page) |
| Deliveroo | ⏳ next |
| Careem / Noon / Smiles / Keeta | ⏳ planned |

The Talabat parser reads the page's embedded Next.js hydration JSON first
(richest: names, prices, fees) and falls back to scraping the rendered DOM. It
needs verifying against one real saved page to lock the selectors.
