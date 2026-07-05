# Pokemon Restock Bot

A small Discord bot that polls retailer product pages and pings you the
moment something restocks or a store lists a new set (e.g. a 30th
Anniversary product line). Three watch modes:

- **`stock`** - watch a single product page, get pinged when it flips from
  out-of-stock to in-stock (anywhere the retailer ships).
- **`new-release`** - watch a collection/category/search page, get pinged
  when a new product shows up there, optionally filtered to titles/tags
  matching keywords (e.g. `"30th anniversary"`).
- **`store-stock`** - watch a specific product's per-physical-store stock
  page and get pinged only when one of *your* named nearby stores shows it
  available - for when you actually want to walk in and buy it, not just
  order online. See "Store-stock mode" below - this one needs more setup
  and is more fragile than the other two, since it depends on scraping a
  store-locator widget whose markup varies a lot site to site.

It supports three ways of checking a page:

- **`shopify`** - a lot of small-to-mid NZ hobby, game and collectibles
  stores run on Shopify, which exposes clean, unauthenticated JSON:
  `https://store.com/products/<handle>.json` and
  `https://store.com/collections/<handle>/products.json`. No scraping,
  very reliable. Use this whenever the store qualifies - it's the fastest
  and least fragile option.
- **`browser`** - loads the page in a real headless Chromium (via
  Playwright), then reads the fully-rendered page. Use this for sites
  that build the page with client-side JavaScript (React/Next/headless
  storefronts - common on big-box retailer sites), where a plain HTTP
  fetch gets back HTML with no actual product content in it. Slower
  (a few seconds per check, since it's a real browser) and heavier, but
  works on far more sites than `generic`.
- **`generic`** - a plain HTTP fetch that looks for common "out of stock"
  phrasing in the raw server-rendered HTML (or, for new-release mode,
  extracts product links via a CSS selector). Fast and cheap, but only
  useful for sites that don't need JavaScript to show stock/listing
  content. This is a heuristic either way - tune `outOfStockPhrases` /
  `selector` per site, and expect occasional adjustment when a store
  redesigns its page.

**What this doesn't do, on purpose:** solve CAPTCHAs, or get you past a
bot-check/waiting-room queue (e.g. Cloudflare Waiting Room, which some
retailers run for hyped drops). Those exist specifically to verify a human
is present or to enforce arrival order - automating past them isn't "checking
a page faster" anymore, it's a different (and more legally/ethically dicey)
thing than passive monitoring. If a site has one of those in front of the
page you want to watch, this bot will fail to see through it, and that's
deliberate rather than a bug. For sites like that you're on your own for the
"is it live" moment, same as everyone else in the queue - this bot can still
watch a level below the queue (e.g. flag when a collection page lists the
new product at all) as an early heads-up.

## 1. Create the Discord application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**.
2. **Bot** tab → Reset/copy the token → this is `DISCORD_TOKEN`.
3. **OAuth2 → General** → copy the **Application ID** → this is `CLIENT_ID`.
4. **OAuth2 → URL Generator**: scopes `bot` + `applications.commands`,
   permissions `Send Messages`, `Embed Links`. Open the generated URL and
   invite the bot to a server you control (can be a private server with
   just you in it).
5. Turn on Developer Mode in Discord (User Settings → Advanced), then
   right-click your own username to **Copy User ID** → this is
   `OWNER_USER_ID`. Right-click a channel the same way for
   `NOTIFY_CHANNEL_ID` if you want alerts in a channel instead of a DM.
6. Right-click the server icon → **Copy Server ID** → this is `GUILD_ID`
   (only needed for instant command registration during setup; global
   registration works too but takes up to an hour to propagate).

## 2. Configure

```bash
cd pokemon-restock-bot
cp .env.example .env
# fill in DISCORD_TOKEN, CLIENT_ID, GUILD_ID, OWNER_USER_ID, NOTIFY_CHANNEL_ID
cp config/watches.example.json config/watches.json
# edit config/watches.json - see below, or just use /watch-add once the bot is running
npm install
npx playwright install chromium   # only needed if you'll use the `browser` platform
```

## 3. Register slash commands and run

```bash
npm run register-commands   # one-off, re-run whenever commands.js changes
npm start
```

You should see `Logged in as <botname>` in the console. In Discord, use
`/watch-add`, `/watch-list`, `/watch-remove`, `/watch-check`,
`/watch-test`. Run `/watch-test` right after startup - it sends a fake
alert immediately so you can confirm your DM/channel notification setup
actually works, without waiting for a real restock.

### Starter watches for common NZ retailers

`config/watches.example.json` ships with 15 pre-built watches - for each
of Kmart NZ, The Warehouse NZ, Mighty Ape NZ, Hobby Lords NZ, and
Farmers NZ: a new-release watch on the Pokemon TCG category page, one
example stock watch on a specific product, and a new-release watch on
the site's **homepage**.

**Note: EB Games NZ is not in this list.** EB Games closed all 38 New
Zealand stores on 31 January 2026 (multi-million dollar losses) - by
the time you're reading this it's been shut for months, so I removed
the watches I'd previously added for it. NZ customers can still buy
online via `ebgames.com.au`, but that's a different (Australian) retailer
with no NZ physical stores, so it's not relevant to store-level stock
anyway.

The homepage watches exist because a big drop (like a 30th Anniversary
set) sometimes shows up as a homepage banner or dedicated campaign page
before it's properly filed under the Pokemon category - watching the
homepage too catches that earlier. They're filtered to `keywords:
["pokemon"]` since a homepage links to everything the store sells, not
just Pokemon products - without that filter you'd get pinged for every
new mattress and lawnmower too. Two limitations worth knowing: (1) the
new-release matcher only looks at link text/title attributes, so a
banner that's just a bare image link with no "Pokemon" text won't match
even if it's promoting a drop - and (2) `outOfStockPhrases`/keyword
matching against a homepage will inherently be noisier than a dedicated
category page, so expect to tune the keyword list or selector if a
particular store's homepage watch turns out too chatty (or too quiet).

A few things to know before you rely on them:

- **I sourced these URLs via web search, not by live-fetching the sites**
  (this environment's outbound web access is sandboxed) - so treat them
  as a strong starting point, not guaranteed-current. Run `/watch-check`
  after adding them and look at `/watch-list` for `lastError` to confirm
  each one is actually resolving before you trust it.
- **The category/collection URLs are the durable part** - those should
  keep working as the store's catalog changes. **The specific product
  URLs are just examples** of "how to point a stock watch at one item" -
  that exact product may sell out and get delisted entirely (not just
  marked out of stock), at which point the watch will start erroring.
  Swap in whatever product you actually want to track via `/watch-add`.
- All five are set to `platform: "browser"` since none of them are
  Shopify: Kmart NZ runs on commercetools (a headless/JS-rendered
  platform - definitely needs `browser`), Farmers NZ runs on SAP
  Commerce, and the others are custom platforms where `browser` is the
  safe default even if `generic` might also work. If you confirm one of
  them can be scraped with plain HTTP (view-source shows real stock
  text), switch that watch to `generic` for lower overhead.
- Farmers' dedicated Pokemon brand page
  (`farmers.co.nz/brand/pokemon-trading-card`) was showing a maintenance
  message when I searched, so the new-release watch instead points at
  their toy search sorted newest-first
  (`SortingAttribute-ArrivalDate-desc?SearchTerm=Pokemon+Trading+Cards`)
  - which is arguably better for catching new listings anyway, but
  double-check the brand page yourself and switch back to it once it's
  working if you prefer a narrower page.
- Hobby Lords' URLs (`/collections/...`, `/products/single/...`) look
  like they might be a Shopify-based or Shopify-adjacent platform, but I
  couldn't confirm it. Try `https://www.hobbylords.co.nz/products.json` -
  if that returns JSON, switch its watches to `platform: "shopify"`,
  which will be faster and more reliable than `browser`.
- `keywords` are left empty on all the new-release watches, so you'll
  get pinged for *every* new listing on each category page, not just
  ones matching "anniversary" - add keywords via `/watch-add` or by
  editing the JSON if that's too noisy for a given store.

### Specialty TCG/hobby stores

Beyond the big-box retailers, `config/watches.example.json` also
includes 11 watches across 9 NZ trading-card specialty stores: Toyworld,
The Game Tree NZ, Cardtopia, TCG Collector NZ, Card Merchant, Card
Masters, TCG Culture, Collect All Day, and BayDragon. These are
generally a *better* bet than the big-box stores for actually landing a
booster box/ETB - they're TCG-focused, often get direct allocations, and
(being small businesses) are far more likely to run Shopify, which is
the fast/reliable checker path.

Confidence varies by store - worth knowing before you lean on them:

- **Confirmed Shopify**: Toyworld (replatformed to Shopify Plus), The
  Game Tree NZ, and Cardtopia (they announced their own move to Shopify
  publicly). Set to `platform: "shopify"`.
- **Presumed Shopify from URL structure** (`/collections/...`,
  `/products/...`) **but not independently confirmed**: TCG Collector
  NZ, Card Merchant, Card Masters, TCG Culture. Also set to `"shopify"` -
  if a watch on one of these errors immediately, check
  `https://<store>/products.json` in a browser; if that 404s, it's not
  actually Shopify and you should switch that watch to `"browser"`.
- **Collect All Day** uses a URL structure that doesn't look like
  Shopify (no `/collections/` prefix) - set to `"browser"` as a safe
  default rather than guessed as Shopify.
- **BayDragon** runs on a different, Java-style platform whose product
  links embed a `jsessionid` that changes per visit. That breaks
  new-release detection (every link would look "new" on every poll,
  since the "id" this bot tracks is the URL itself) - so BayDragon only
  gets a `stock` watch here, no new-release/listing watch. If you add
  more BayDragon watches yourself, stick to `mode: "stock"` for the same
  reason.
- I sourced all of these via web search rather than a live fetch, same
  caveat as the big-box list above - verify with `/watch-check` before
  trusting them, and treat the specific product URLs as swappable
  examples rather than permanent.
- This isn't an exhaustive list of NZ Pokemon TCG sellers - if you shop
  somewhere not listed here, `/watch-add` it yourself; the "is it
  Shopify" check in the next section takes under a minute.

### Store-stock mode

This checks a specific product's "which physical stores have this"
page and only alerts when one of the store names *you* configured shows
up as available - so you find out "go to Sylvia Park now" instead of
just "it's in stock online somewhere."

**Current state, being upfront about it:**

- **Farmers** confirmed to have a real "Check in Store" tool on product
  pages - `config/watches.example.json` includes one example watch for
  it (`farmers-terapagos-ex-upc-auckland-stores`), targeting Sylvia
  Park, Botany, Manukau, St Lukes, Newmarket, and Queen Street. I could
  not inspect the widget's actual markup from this environment (its
  outbound web access is sandboxed), so this is a best-effort
  implementation - see below for how to verify/fix it.
- **Kmart** does not appear to have a public *website* per-store stock
  checker - every source I could find (their own FAQ, forums, third-party
  stock-tracker sites) points to this being an **app-only** feature
  (their iOS/Android app), or something you have to phone a store to ask
  about. I didn't build a Kmart store-stock watch rather than fabricate
  a URL that doesn't exist. If you find one (open a Kmart product page
  yourself, look for a "check stock" / "find in store" link, and check
  your browser's dev tools Network tab for an XHR request when you use
  it), send me the request URL and I'll wire it up properly.

**How it actually works:** the `store-stock` checker (in
`src/checkers/htmlAnalysis.js`, function `analyzeStoreStockHtml`) loads
the page, splits it into one "line" of text per block-level element (so
store rows don't run together), then for each name in `storeNames`
looks at that store's line (and, if you set `lineWindow` above 0, a
bounded number of neighboring lines - bounded so it can never bleed into
the *next* store's row) for in-stock/out-of-stock phrasing. It alerts
once, the moment *any* configured store flips from none-available to
at least one available.

**Verifying/fixing a store-stock watch once it's running:**

1. Run `/watch-check`, then `/watch-list`. For a `store-stock` watch you'll
   see something like `Sylvia Park: in stock, Botany: not found on page,
   Manukau: out of stock`.
2. `not found on page` for every store usually means the stock panel
   isn't in the initial page load - it's behind a button click. The
   `browser` checker already tries clicking anything matching "check
   stock"/"check in store"/"find in store" once before giving up; if
   your store's button says something else, set
   `watch.checkStockButtonText` to a regex matching the actual button
   text (view it with dev tools).
3. If a store name shows a status but it's *wrong* compared to what the
   real page says, the line-window heuristic is misreading the markup -
   try `lineWindow: 1` (checks one line before/after the store name too,
   for sites that put the name and status in separate sibling elements)
   and compare again.
4. Matching is a case-insensitive substring check, so `"Sylvia Park"`
   will match a page that renders `"Farmers Sylvia Park"` - but it has to
   actually be a substring, so double-check spelling against what the
   site displays.

This mode only supports `platform: "browser"` or `"generic"` -
`"shopify"` is excluded because Shopify's product JSON only exposes
aggregate stock across all locations, not a per-store breakdown.

### Finding real watch targets

- **Is a store on Shopify?** Visit `https://<store>/products.json` in a
  browser - if you get JSON back, it's Shopify. Also try appending
  `.json` to any product page URL.
- **Collection handle for new-release mode:** open the store's Pokemon
  TCG category page, the URL is usually
  `https://<store>/collections/<handle>`.
- **Not Shopify - does it need `browser` or will `generic` do?** Load the
  product page, then view-source (or disable JavaScript and reload). If
  the stock status / "Add to cart" button is still there, `generic` will
  work and is cheaper. If the page is mostly empty without JS (common on
  React/Next/headless-commerce storefronts), use `browser` instead.
- **Tuning the phrase/selector:** open the product page, use your
  browser's dev tools to find the phrase that appears when it's sold out
  (e.g. "Sold Out", "Notify Me"), and put it in `outOfStockPhrases` if it
  differs from the defaults. For new-release mode, find a CSS selector
  that matches each product card's link and pass it as `selector` in
  `/watch-add`. Both work the same way for `generic` and `browser` - the
  only difference is whether JS has run before the page is read.

### Watch JSON schema (for hand-editing `config/watches.json`)

```jsonc
{
  "id": "any-unique-string",
  "nickname": "short-name",           // shown in alerts, must be unique
  "url": "https://...",               // product page (stock mode) or collection/category page (new-release mode)
  "platform": "shopify" | "browser" | "generic",
  "mode": "stock" | "new-release" | "store-stock",
  "keywords": ["30th anniversary"],   // new-release mode only; empty array = alert on every new listing
  "selector": "a.product-card",       // browser/generic + new-release mode only; CSS selector for product links
  "outOfStockPhrases": ["sold out"],  // stock or store-stock mode; overrides the built-in phrase list
  "storeNames": ["Sylvia Park"],      // store-stock mode only (required); store names to track
  "lineWindow": 0,                    // store-stock mode only; how many neighboring lines to also check (default 0 = same line only)
  "checkStockButtonText": "check.*stock", // store-stock + browser platform only; regex for the button that reveals the stock panel
  "state": {}                         // managed by the bot, leave as {} for new watches
}
```

The **first** check after adding a watch only records a baseline (what's
currently in stock / currently listed) - it won't fire an alert, so you
don't get spammed for everything that already existed.

## 4. Keep it running

This is a long-lived process - it needs to stay up to actually catch a
restock. Options:

- **A machine you leave on** (desktop, Raspberry Pi): run with
  [pm2](https://pm2.keymetrics.io/) (`npx pm2 start src/index.js --name pokemon-bot`)
  or a systemd service so it restarts on crash/reboot.
- **A small VPS** (e.g. a $5/mo box): same as above.
- **A PaaS** (Railway, Render, Fly.io): push this folder as a Node
  service, set the env vars in their dashboard, start command `npm start`.

## Notes on politeness / reliability

- Default poll interval is 5 minutes (`POLL_INTERVAL_MINUTES`), with a
  1.5s stagger between checking each watch, so you're not hammering
  several stores at once. Don't drop this much below 3-5 minutes -
  aggressive polling risks getting your IP rate-limited or blocked.
- Set a real contact email in `USER_AGENT` so a store operator can reach
  you if your traffic looks like a problem.
- This bot only *alerts you* - it doesn't auto-checkout or auto-add to
  cart, solve CAPTCHAs, or bypass bot-check/waiting-room queues. You
  still have to actually buy the thing fast and get through whatever
  human-verification the store puts in front of you; this just saves
  you from manually refreshing tabs all day.
- Both `generic` and `browser` stock checks are heuristics based on page
  text (`outOfStockPhrases`) - they can false-positive/negative if a
  store's wording doesn't match the defaults, so tune per site and treat
  `/watch-list`'s reported status as a hint, not gospel.
- `browser` still won't work against a page that requires solving an
  interactive challenge (a real CAPTCHA, "click and hold" verification,
  etc.) before showing content - Playwright renders JS, but it doesn't
  pretend to be a human passing a human-verification test. That's an
  intentional limit, not a bug to file.
