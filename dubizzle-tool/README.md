# dubizzle local search filter

Filter dubizzle listings **on your own machine** and view them as a visual grid
with images. No LLM is involved while you use it, so it costs **zero tokens**.

## How it works

1. `dubizzle_search.py` reads a dubizzle search page (fetched, or one you saved
   from your browser), extracts every listing with BeautifulSoup
   (title, price, image, location, link).
2. It writes a self-contained **`results.html`** that embeds the listings and
   has its own **live search / price filter / sort** running in your browser.

So you grab the page once, then filter as much as you want with no re-runs and
no tokens.

## Setup (one time)

```bash
python3 -m pip install --user beautifulsoup4 requests
```

## Everyday use (recommended — always works)

dubizzle blocks plain scripts with a bot challenge, so the reliable path is to
save the page from the browser where it already loads for you:

1. Open your dubizzle search in the browser and scroll so the items you want are
   loaded.
2. **File → Save Page As… → "Web Page, HTML Only"** (or press ⌘S).
3. Run:

```bash
python3 dubizzle_search.py --file ~/Downloads/your-saved-page.html --open
```

`--open` launches `results.html`. Use the search box, min/max price, and sort —
all instant, all local.

## Trying a direct fetch (may be blocked)

```bash
python3 dubizzle_search.py --url "https://uae.dubizzle.com/motors/used-cars/toyota/corolla/" --open
```

If it prints "No listings found", dubizzle served a challenge page — use the
`--file` method above instead. The last fetched page is cached, so you can
re-filter it offline with `--no-fetch`.

## Optional command-line pre-filters

You usually don't need these (filter in the browser instead), but they exist:

| Flag | Meaning |
|------|---------|
| `--keywords "gcc,2020"` | keep only items whose title/location contain ALL terms |
| `--exclude "salvage,accident"` | drop items containing any of these |
| `--min-price 40000` / `--max-price 60000` | price bounds |
| `--out path.html` | output file (default `results.html`) |
| `--no-fetch` | reuse the last fetched page, no network |

Example:

```bash
python3 dubizzle_search.py --file saved.html --keywords "corolla,gcc" --max-price 60000 --open
```
