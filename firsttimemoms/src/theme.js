/* ─── BRAND & PALETTE ─────────────────────────────────────────────────────── */
// firsttimemoms — warm, inclusive, cross-cultural, soothing sage + blush
export const P = {
  sage:     "#6B8F71",  // primary — calming sage green
  sageL:    "#EFF5F0",  // sage light bg
  sageM:    "#C8DBC9",  // sage mid
  blush:    "#E8A598",  // warm accent — nurturing blush
  blushL:   "#FDF1EE",  // blush light bg
  blushM:   "#F2C4BA",  // blush mid
  cream:    "#FAF7F2",  // page background
  parchment:"#F3EDE3",  // card surface
  sand:     "#E5DDD0",  // border
  bark:     "#7A6352",  // text secondary
  ink:      "#2A2118",  // text primary
  white:    "#FFFFFF",
  gold:     "#C09A5B",  // premium accent
  goldL:    "#FBF5E9",
};

export const F = {
  display: "'Playfair Display', Georgia, serif",
  body:    "'Lato', 'Helvetica Neue', sans-serif",
};

export const CSS_VARS = `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=Lato:wght@300;400;700&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: ${P.cream}; }
  select { appearance: none; -webkit-appearance: none; cursor: pointer; }
  input[type=range] { accent-color: ${P.sage}; }
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-thumb { background: ${P.sageM}; border-radius: 2px; }
  @keyframes fadeUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.5; } }
  .fade-up { animation: fadeUp .5s ease both; }
`;
