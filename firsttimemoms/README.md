# firsttimemoms

A UAE/GCC marketplace connecting new parents with **cultural postnatal (confinement) caregivers** across South Asian, East & SE Asian, and Arab diasporas.

The app has four sections:

- **Home** — brand landing, how-it-works, traditions supported.
- **Find a Carer** — a 7-step intake wizard feeding a weighted matching algorithm, then scored results.
- **Wellness Centers** — partner Ayurvedic centers with exclusive discounts.
- **Shop** — hard-to-find postnatal ingredients sourced from origin.

## Stack

- [Vite](https://vitejs.dev/) + [React 18](https://react.dev/)
- Styling is 100% inline style objects driven by a central design token module (`src/theme.js`). No CSS framework.

## Run

```bash
npm install      # install dependencies
npm run dev      # start the dev server (http://localhost:5173)
npm run build    # production build to dist/
npm run preview  # preview the production build
npm run lint     # run ESLint
```

## Project structure

```
src/
  main.jsx            React entry
  App.jsx             Root: nav + page routing + footer
  theme.js            Design tokens: P (palette), F (fonts), CSS_VARS
  scoring.js          scoreMatch() + SCORING_CONFIG (weights/thresholds)
  components/
    ui.jsx            Stars, Tag, Btn
    CalendarPicker.jsx
    Nav.jsx
  data/
    caregivers.js     CAREGIVERS mock data
    centers.js        CENTERS mock data
    products.js       PRODUCTS mock data
    locations.js      LOCATIONS cascading city/district/area
    hooks.js          useCaregivers / useCenters / useProducts (data-loading layer)
  pages/
    HomePage.jsx
    FindPage.jsx      intake wizard + ResultsView
    CentersPage.jsx
    ShopPage.jsx
```

## Data-loading layer

Mock data is served through hooks in `src/data/hooks.js` (`useCaregivers`, `useCenters`,
`useProducts`). They return `{ data, loading }` today from the local arrays. Swapping to a
real API later means changing only those hooks — no page/render code changes.

## Matching algorithm

`src/scoring.js` exports `scoreMatch(carer, ans)` and a `SCORING_CONFIG` object holding all
weights and thresholds (no inline magic numbers). Factors: tradition fit, budget, location,
availability, live-in preference, and a language bonus. The intake **priorities** ("what
matters most", up to 3) boost the weights of their mapped factors — see
`PRIORITY_FACTOR_MAP` in `scoring.js`.

## Known seams / not yet built (for the backend team)

- **No real API/backend.** All data is local mock arrays behind `src/data/hooks.js`.
- **No auth.**
- **Dead CTAs.** "Request booking", "Send message", "Book with discount", "Call center",
  "Add to bag" (cart is local-only) have no handlers — these are the booking/messaging/
  checkout seams.
- **Accessibility** needs a pass before public launch (keyboard nav, ARIA on the custom
  select/calendar/card controls, focus states, contrast audit). Deliberately out of scope now.
- **No tests.**
