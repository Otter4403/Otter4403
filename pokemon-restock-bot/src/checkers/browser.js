const { chromium } = require('playwright');
const { analyzeStockHtml, analyzeListingHtml, analyzeStoreStockHtml } = require('./htmlAnalysis');

// Buttons/links that commonly reveal a "check stock at nearby stores" panel
// after being clicked - the panel's content often isn't in the DOM at all
// until this fires. Best-effort: every site phrases this differently, so
// `watch.checkStockButtonText` can override this per site.
const DEFAULT_CHECK_STOCK_BUTTON_TEXT = /check (in )?store|check stock|store availability|find in store|check availability/i;

// Renders the page in a real (headless) browser first, so it sees whatever
// stock status/listings JavaScript injects after load - unlike generic.js,
// which only sees the server's initial HTML. Needed for headless-commerce /
// React-Next storefronts (common on big-box retailer sites) where the raw
// HTML response has no product content at all.
//
// This is passive monitoring only: it loads the page and reads what's there.
// It does not solve CAPTCHAs, click through interactive bot checks, or try
// to get around a waiting room/queue - sites that require that will just
// fail here, on purpose.

let browserPromise = null;

function getBrowser() {
  if (!browserPromise) {
    browserPromise = chromium.launch({ headless: true });
  }
  return browserPromise;
}

async function closeBrowser() {
  if (!browserPromise) return;
  const browser = await browserPromise;
  browserPromise = null;
  await browser.close();
}

async function withRenderedPage(url, userAgent, interact) {
  const browser = await getBrowser();
  const context = await browser.newContext({ userAgent });
  const page = await context.newPage();
  try {
    // Block heavy assets we don't need - we're only reading text/DOM, not
    // taking screenshots, so this keeps checks fast and light on bandwidth.
    await page.route(/\.(png|jpe?g|gif|webp|svg|woff2?|ttf|mp4)(\?.*)?$/i, (route) => route.abort());

    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20000 });
    // Give client-rendered stock widgets a moment to fetch and paint; fall
    // back gracefully if the page never truly goes idle (some sites keep
    // long-lived connections open, e.g. chat widgets or analytics beacons).
    await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});

    if (interact) await interact(page);

    return await page.content();
  } finally {
    await context.close();
  }
}

async function checkBrowserStock(watch, userAgent) {
  const html = await withRenderedPage(watch.url, userAgent);
  return analyzeStockHtml(html, watch);
}

async function checkBrowserNewReleases(watch, userAgent) {
  const html = await withRenderedPage(watch.url, userAgent);
  return analyzeListingHtml(html, watch);
}

// Per-store stock is frequently hidden behind a "check stock near you"
// button rather than present in the initial render - so unlike the other
// checkers, this one first looks for the target store names as-is, and if
// none of them appear anywhere on the page at all, tries clicking a likely
// "check stock" button once and re-reading before giving up. This is a
// best-effort guess at each site's actual widget - if it doesn't surface
// your stores, pass `watch.checkStockButtonText` with the exact button
// label you see on the page (found via your browser's dev tools).
async function checkBrowserStoreStock(watch, userAgent) {
  const buttonPattern = watch.checkStockButtonText
    ? new RegExp(watch.checkStockButtonText, 'i')
    : DEFAULT_CHECK_STOCK_BUTTON_TEXT;

  const html = await withRenderedPage(watch.url, userAgent, async (page) => {
    const storeNames = watch.storeNames || [];
    const alreadyVisible = await page.evaluate(
      (names) => names.some((n) => document.body.innerText.toLowerCase().includes(n.toLowerCase())),
      storeNames
    );
    if (alreadyVisible) return;

    const button = page.getByText(buttonPattern).first();
    if (await button.count().catch(() => 0)) {
      await button.click({ timeout: 5000 }).catch(() => {});
      await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
    }
  });

  return analyzeStoreStockHtml(html, watch);
}

process.on('SIGINT', () => closeBrowser().finally(() => process.exit(0)));
process.on('SIGTERM', () => closeBrowser().finally(() => process.exit(0)));

module.exports = { checkBrowserStock, checkBrowserNewReleases, checkBrowserStoreStock, closeBrowser };
