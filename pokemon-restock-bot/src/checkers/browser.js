const { chromium } = require('playwright');
const { analyzeStockHtml, analyzeListingHtml } = require('./htmlAnalysis');

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

async function fetchRenderedHtml(url, userAgent) {
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

    return await page.content();
  } finally {
    await context.close();
  }
}

async function checkBrowserStock(watch, userAgent) {
  const html = await fetchRenderedHtml(watch.url, userAgent);
  return analyzeStockHtml(html, watch);
}

async function checkBrowserNewReleases(watch, userAgent) {
  const html = await fetchRenderedHtml(watch.url, userAgent);
  return analyzeListingHtml(html, watch);
}

process.on('SIGINT', () => closeBrowser().finally(() => process.exit(0)));
process.on('SIGTERM', () => closeBrowser().finally(() => process.exit(0)));

module.exports = { checkBrowserStock, checkBrowserNewReleases, closeBrowser };
