# Pokemon Restock Bot

A small Discord bot that polls retailer product pages and pings you the
moment something restocks or a store lists a new set (e.g. a 30th
Anniversary product line). Two watch modes:

- **`stock`** - watch a single product page, get pinged when it flips from
  out-of-stock to in-stock.
- **`new-release`** - watch a collection/category/search page, get pinged
  when a new product shows up there, optionally filtered to titles/tags
  matching keywords (e.g. `"30th anniversary"`).

It supports two ways of checking a page:

- **`shopify`** - a lot of small-to-mid NZ hobby, game and collectibles
  stores run on Shopify, which exposes clean, unauthenticated JSON:
  `https://store.com/products/<handle>.json` and
  `https://store.com/collections/<handle>/products.json`. No scraping,
  very reliable.
- **`generic`** - for everything else. It fetches the HTML and looks for
  common "out of stock" phrasing (or, for new-release mode, extracts
  product links via a CSS selector). This is a heuristic - tune it per
  site, and expect it to need occasional adjustment when a store
  redesigns its page.

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
```

## 3. Register slash commands and run

```bash
npm run register-commands   # one-off, re-run whenever commands.js changes
npm start
```

You should see `Logged in as <botname>` in the console. In Discord, use
`/watch-add`, `/watch-list`, `/watch-remove`, `/watch-check`.

### Finding real watch targets

- **Is a store on Shopify?** Visit `https://<store>/products.json` in a
  browser - if you get JSON back, it's Shopify. Also try appending
  `.json` to any product page URL.
- **Collection handle for new-release mode:** open the store's Pokemon
  TCG category page, the URL is usually
  `https://<store>/collections/<handle>`.
- **Generic sites:** open the product page, use your browser's dev tools
  to find the phrase that appears when it's sold out (e.g. "Sold Out",
  "Notify Me"), and put it in `outOfStockPhrases` if it differs from the
  defaults. For new-release mode, find a CSS selector that matches each
  product card's link and pass it as `selector` in `/watch-add`.

### Watch JSON schema (for hand-editing `config/watches.json`)

```jsonc
{
  "id": "any-unique-string",
  "nickname": "short-name",           // shown in alerts, must be unique
  "url": "https://...",               // product page (stock mode) or collection/category page (new-release mode)
  "platform": "shopify" | "generic",
  "mode": "stock" | "new-release",
  "keywords": ["30th anniversary"],   // new-release mode only; empty array = alert on every new listing
  "selector": "a.product-card",       // generic + new-release mode only; CSS selector for product links
  "outOfStockPhrases": ["sold out"],  // generic + stock mode only; overrides the built-in phrase list
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
  cart. You still have to actually buy the thing fast; this just saves
  you from manually refreshing tabs all day.
- The `generic` stock check is a heuristic based on page text. Some
  storefronts render stock status client-side via JavaScript that a
  plain HTTP fetch won't execute - if a `generic` watch seems to always
  report "in stock" or never flips, that store may need a headless
  browser (out of scope here, but `playwright` could be swapped in for
  that specific checker if needed).
