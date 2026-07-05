# Pokemon Restock Bot

A small Discord bot that polls retailer product pages and pings you the
moment something restocks or a store lists a new set (e.g. a 30th
Anniversary product line). Two watch modes:

- **`stock`** - watch a single product page, get pinged when it flips from
  out-of-stock to in-stock.
- **`new-release`** - watch a collection/category/search page, get pinged
  when a new product shows up there, optionally filtered to titles/tags
  matching keywords (e.g. `"30th anniversary"`).

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
`/watch-add`, `/watch-list`, `/watch-remove`, `/watch-check`.

### Starter watches for common NZ retailers

`config/watches.example.json` ships with 10 pre-built watches (a
new-release watch on the Pokemon TCG category page, plus one example
stock watch on a specific product) for: Kmart NZ, The Warehouse NZ,
Mighty Ape NZ, EB Games NZ, and Hobby Lords NZ.

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
  platform - definitely needs `browser`), and the others are custom
  platforms where `browser` is the safe default even if `generic` might
  also work. If you confirm one of them can be scraped with plain HTTP
  (view-source shows real stock text), switch that watch to `generic`
  for lower overhead.
- Hobby Lords' URLs (`/collections/...`, `/products/single/...`) look
  like they might be a Shopify-based or Shopify-adjacent platform, but I
  couldn't confirm it. Try `https://www.hobbylords.co.nz/products.json` -
  if that returns JSON, switch its watches to `platform: "shopify"`,
  which will be faster and more reliable than `browser`.
- EB Games in particular is worth watching closely for `lastError` -
  their AU sibling site runs a Cloudflare Waiting Room and Riskified
  fraud detection for hyped drops, so even passive `browser` polling
  could get rate-limited or blocked during a high-demand release. Normal
  category browsing should be fine most of the time.
- `keywords` are left empty on all the new-release watches, so you'll
  get pinged for *every* new listing on each category page, not just
  ones matching "anniversary" - add keywords via `/watch-add` or by
  editing the JSON if that's too noisy for a given store.

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
  "mode": "stock" | "new-release",
  "keywords": ["30th anniversary"],   // new-release mode only; empty array = alert on every new listing
  "selector": "a.product-card",       // browser/generic + new-release mode only; CSS selector for product links
  "outOfStockPhrases": ["sold out"],  // browser/generic + stock mode only; overrides the built-in phrase list
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
