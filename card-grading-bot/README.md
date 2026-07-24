# Otter Grading

An unofficial web app that estimates a trading card's grade from front/back
photos, modeled on the publicly described condition standards used by
**PSA**, **Beckett Grading Services (BGS)**, **CGC Cards**, **TAG Grading**,
**SGC**, and **HGA** -- so you can see how the same card might come back
from each company before you ever mail it in.

> **Not affiliated with PSA, BGS, CGC, TAG, SGC, or HGA.** None of these companies
> publish their exact internal grading formulas, so every scoring rule here
> is this project's own best-effort approximation built from each
> company's public grading guides and widely documented collector
> knowledge. Treat results as a rough, pre-submission gut check -- not a
> substitute for a real submission, and not proof of what any of these
> companies would actually assign.

## What it does

1. You upload a front and back photo of a card through the web UI.
2. A small computer-vision pipeline (OpenCV):
   - finds the card in the photo and straightens/crops it (`vision/preprocess.py`)
   - measures **centering** by locating the border-to-artwork line on each side of both the front and back photos (`vision/centering.py`)
   - scores **corners** for whitening/wear and tip sharpness (`vision/corners.py`)
   - scores **edges** for whitening/chipping along each side (`vision/edges.py`)
   - scores **surface** for scratches/print defects/stains (`vision/surface.py`)
3. Those four measurements feed independent rule engines for each company
   (`grading/psa.py`, `grading/beckett.py`, `grading/cgc.py`, `grading/tag.py`,
   `grading/sgc.py`, `grading/hga.py`), each applying that company's own
   scale, granularity, and combination logic, described in each module's
   docstring.
4. Each grade also gets rendered as a stylized "slab" mockup
   (`rendering/slabs.py`, using Pillow) showing your actual submitted card
   inside a plastic-holder-style graphic with that company's grade on the
   label, so you can see side by side what each result would look like.
5. The web UI shows all six slabs and grades side by side with the
   underlying subgrades and measurements, so you can compare how each
   company's rules treat the same card.
6. A "Why this grade?" panel (`vision/annotate.py` + `explanations.py`)
   shows exactly what drove the four condition scores: your front and back
   photos with the detected centering border lines, a color-coded bracket
   at each corner and strip along each edge (green/amber/red by score), and
   a highlight over any area flagged as a surface blemish -- plus a
   plain-English sentence per attribute naming the weakest corner/edge and
   how far off centering is, so a 9.5 isn't just a number.
7. Before any of that runs, `vision/quality.py` checks whether each photo
   is actually usable: sharpness (Laplacian variance), resolution, contrast,
   and whether the card's edges could be confidently isolated at all. A
   badly blurry, tiny, or washed-out photo gets rejected with a specific
   "please retake the front/back photo" message instead of silently
   producing a misleading grade; milder issues still get graded but show a
   non-blocking "these photos could be clearer" banner. The web UI also has
   a collapsible photo-taking tips panel (lighting, angle, background,
   focus, resolution) above the upload area.
8. Card identification reads the card itself off the front photo -- year,
   set/brand, player or character name, card number, and any
   parallel/variation -- and shows it the way a real grading label would
   (e.g. "2023 TOPPS CHROME SHOHEI OHTANI #27 REFRACTOR"), both above the
   results and on each slab mockup. Two ways this can work, tried in order:
   - `identification.py`: Claude's vision API, works for any card type.
     Needs an `ANTHROPIC_API_KEY` environment variable (see below); without
     one, this step is skipped.
   - `pokemon_lookup.py`: a free fallback used whenever the Claude step
     doesn't run (no key configured) or fails. It OCRs the card's name with
     Tesseract and matches it against the public
     [pokemontcg.io](https://pokemontcg.io) database -- no API key, no
     cost, but it only recognizes Pokemon cards and is less reliable than
     vision AI since it depends on OCR reading the name text cleanly.

   Either way, it's a best-effort read, not guaranteed correct -- the UI
   always says so and flags low-confidence reads. With neither path
   available (no key and no Pokemon match), grading works exactly the
   same, just without this line.

The slab images are original artwork, not reproductions of any company's
actual holder design, logo, hologram, or barcode. What they do borrow are
broad, industry-wide *conventions* that aren't anyone's exclusive
property -- PSA and CGC show the grade in a bordered badge, Beckett/TAG/HGA
are known for publishing a 4-attribute subgrade grid (centering, corners,
edges, surface) so those get one, SGC gets a plain banner. Every slab is
watermarked "UNOFFICIAL" with a fake, clearly non-real certification
number.

## How each company's rules are approximated

| Company | Scale | Combination logic (our approximation) |
|---|---|---|
| PSA | 1-10, whole numbers | "Weakest link": overall = min(centering, corners, edges, surface), matching PSA's public grade descriptions where a single flaw caps the grade. |
| Beckett (BGS) | 1-10, half points | Weighted average of the four subgrades, capped at (lowest subgrade + 1.0); a Black Label 10 requires all four subgrades to be a perfect 10. |
| CGC | 1-10, half points | Evenly-weighted average of the four subgrades, capped at (lowest subgrade + 1.5), approximating CGC's holistic "eye appeal" review process. |
| TAG | 1.0-10.0, half points, **no 9.5** | Weighted composite across centering, all 4 individual corner subgrades, all 4 individual edge subgrades, and surface, computed as a 100-1000 internal "TAG Score" then banded down to the public grade -- 950-989 shows as "10 (Gem Mint)" and 990-1000 as "10 (Pristine)", mirroring TAG's own published two-layer scale. |
| SGC | 10-100, SGC's public number line (10s, then 2-point steps from 80-100) | "Weakest link" like PSA: the worst of centering/corners/edges/surface is looked up against SGC's published grade tiers. |
| HGA | 1.00-10.00, hundredth points | Same weighted-composite structure as TAG (all 4 corners, all 4 edges individually) but at hundredth-of-a-point precision, leaning slightly more on surface -- mirroring HGA's imaging-based marketing. |

Because the scales have different granularity and combination rules, the
same card can land on a perfect 10 under the coarser scales (PSA, BGS, CGC)
while SGC, TAG, or HGA -- which resolve finer differences or have stricter
top-end tolerances -- show the small imperfection instead. That divergence
is the point: it's meant to show how differently companies could grade an
identical card.

### Centering: grounded in each company's published numbers

Every company measures centering on **both** the front and back photo (back
is graded more leniently), and every company we could find public numbers
for anchors its scoring to specific worst-side percentages rather than a
single generic curve. Where we found a company's own published breakpoint,
we use it as an anchor and linearly interpolate between anchors (see
`grading/base.py:piecewise_centering_score` and each company's module
docstring for exactly which numbers are confirmed vs. our own
extrapolation beyond them):

| Company | Front 10 | Front 9(.5) | Front lower | Back |
|---|---|---|---|---|
| PSA | 55/45 | 60/40 (9) | 65/35 (8), 70/30 (7), 80/20 (6), 85/15 (5) | 75/25 for 10, 90/10 floor through grade 7 |
| Beckett (BGS) | 55/45 | -- | (extrapolated below the 10 anchor) | 70/30 for 10 |
| CGC | 55/45 | 60/40 (9.5), 65/35 (9) | (extrapolated) | 60/40 for 10, ~75/25 ceiling |
| SGC | 50/50 (=100) | 55/45 (=98), 60/40 (=96) | (extrapolated) | not separately published; single measurement used |
| TAG | ~51/49 (Pristine) | ~55/45 (Gem Mint) | (extrapolated) | ~54.5/45.5 (Pristine), ~70/30 (Gem Mint), sports-card tolerances |
| HGA | no published numbers found | -- | -- | generic fallback curve used for both sides |

HGA is the one company where we couldn't find published centering
breakpoints, so it still uses a generic linear model (50/50=10 down to
95/5=1) as a fallback -- clearly noted in its module and in the app's
explanations.

We do **not** claim these tables are complete or that any company would
reproduce them exactly; they're drawn from each company's own public
grading-scale pages and widely-cited secondary sources, and the gaps
between confirmed anchors are our own linear interpolation.

## Running it locally

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/` in a browser, upload a front and back
photo, and click **Grade My Card**.

### Optional: card identification

**Any card, via Claude's vision API (costs a tiny amount per request):**
set an environment variable before starting the server:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # from https://console.anthropic.com/
```

On Railway, add it as a variable on the service (Settings → Variables).
Each grading request that includes identification costs a small fraction
of a cent (it uses Haiku by default; override with `CARD_ID_MODEL` if you
want a different model).

**Pokemon cards only, for free, no key needed:** as long as the
`tesseract-ocr` system binary is installed (already set up for this repo's
Railway deployment via `nixpacks.toml`; for local runs, `apt install
tesseract-ocr` or `brew install tesseract`) and `pytesseract` is in
`requirements.txt` (it already is), `pokemon_lookup.py` runs automatically
whenever the Claude step above doesn't produce a result -- either because
`ANTHROPIC_API_KEY` isn't set, or the card wasn't a good match for it.

Leave both unconfigured and grading still works exactly the same, just
without the identified card name showing up.

## Deploying (Railway)

This is a real server (FastAPI doing OpenCV/Pillow image processing), not
a static site, so it needs a host that runs a persistent Python process.
`backend/Procfile` and `backend/railway.json` are set up for
[Railway](https://railway.app):

1. Create a new Railway service from this repo.
2. Since the app lives in a subdirectory of this repo, set the service's
   **root directory** to `card-grading-bot/backend` in its settings.
3. Railway's Nixpacks builder auto-detects `requirements.txt`, installs
   dependencies, and uses the `startCommand` in `railway.json`
   (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`) to run it.
4. No environment variables or database are required.

## Running the tests

```bash
cd backend
python3 -m pytest tests/ -v
```

The grading-rule tests are pure unit tests (no images needed). The vision
tests use small synthetic images (solid-color rectangles standing in for a
card and its border) so they run fast and don't require real card photos.
The slab-rendering tests check that every company renders a valid PNG and
that long names/labels get truncated instead of overlapping other text.
The annotation and explanation tests check that the diagnostic overlay
renders for edge cases (missing corner/edge data, an empty blemish mask,
no centering measurement for the back photo) and that the generated
sentences correctly name the weakest corner/edge/side. The quality-check
tests verify the blur/resolution/contrast thresholds trigger correctly in
both directions (a sharp, well-lit synthetic photo passes clean; a heavily
blurred, tiny, or flat/dark one blocks) without needing real card photos.
The identification tests mock the Anthropic client entirely (no network
calls, no API key needed) to check the no-key/no-package/API-error fail
-soft paths and the label-line formatting. The Pokemon lookup tests mock
`pytesseract` and `httpx` the same way (one test also runs the real
Tesseract binary against a synthetic image to confirm the OCR integration
itself works, separate from the mocked unit tests).

## Project layout

```
card-grading-bot/
  backend/
    app/
      main.py            FastAPI app, /api/grade endpoint, serves the frontend
      models.py           Pydantic request/response schemas
      explanations.py      Builds the plain-English "why this grade" text per attribute
      identification.py     Optional Claude-vision card identification (year/set/player/#)
      grading/            Per-company rule engines (pure functions, no images involved)
      vision/              OpenCV pipeline: card detection, centering, corners, edges, surface,
                           plus annotate.py for the diagnostic overlay and quality.py for the
                           blur/resolution/contrast checks
      rendering/           Pillow-based slab mockup generator
      fonts/                Bundled DejaVu Sans/Bold, shared by rendering/ and vision/annotate.py
    tests/                 pytest unit tests for grading rules, vision helpers, slab rendering,
                           annotation, explanations, photo quality checks, and identification
    requirements.txt
  frontend/
    index.html / style.css / app.js   Drag-and-drop upload UI, no build step
```

## Known limitations

- Photo quality, lighting, angle, and background contrast all affect
  detection accuracy -- a well-lit photo directly above the card on a
  plain, contrasting background works best.
- The corner/edge/surface heuristics look for whitening and texture
  anomalies; they can be fooled by cards with naturally light borders/art
  or by glare, reflections, and sleeves/toploaders in the photo.
- The company rule engines are deliberately transparent approximations,
  not reverse-engineered proprietary algorithms -- expect real submissions
  to disagree with this tool sometimes.
