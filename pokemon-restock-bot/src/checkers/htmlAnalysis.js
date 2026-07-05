const cheerio = require('cheerio');

const OUT_OF_STOCK_PHRASES = [
  'out of stock',
  'sold out',
  'currently unavailable',
  'notify me when available',
  'notify me',
  'unavailable',
  'coming soon',
  'sold-out',
];

const DEFAULT_PRODUCT_LINK_SELECTOR = 'a[href*="/product"]';

const STORE_IN_STOCK_PHRASES = ['in stock', 'available', 'high stock', 'medium stock', 'low stock'];
const STORE_OUT_OF_STOCK_PHRASES = ['out of stock', 'unavailable', 'no stock', 'sold out'];

// Shared by the plain-HTTP (generic.js) and headless-browser (browser.js)
// checkers - both end up with a blob of rendered HTML, they just get it
// differently (axios vs. a real browser executing the page's JS first).

function analyzeStockHtml(html, watch) {
  const $ = cheerio.load(html);
  const pageText = $('body').text().replace(/\s+/g, ' ').toLowerCase();
  const phrases = watch.outOfStockPhrases || OUT_OF_STOCK_PHRASES;
  const matchedPhrase = phrases.find((phrase) => pageText.includes(phrase));
  const title = $('meta[property="og:title"]').attr('content') || $('title').text().trim();
  return {
    inStock: !matchedPhrase,
    title: title || watch.nickname,
    detail: matchedPhrase ? `Found phrase "${matchedPhrase}" on page` : 'No out-of-stock phrasing found',
  };
}

function analyzeListingHtml(html, watch) {
  const $ = cheerio.load(html);
  const selector = watch.selector || DEFAULT_PRODUCT_LINK_SELECTOR;
  const base = new URL(watch.url);
  const seen = new Set();
  const items = [];

  $(selector).each((_, el) => {
    const href = $(el).attr('href');
    if (!href) return;
    let absoluteUrl;
    try {
      absoluteUrl = new URL(href, base).toString();
    } catch {
      return;
    }
    if (seen.has(absoluteUrl)) return;
    seen.add(absoluteUrl);

    const title = $(el).attr('title') || $(el).text().replace(/\s+/g, ' ').trim();
    if (!title) return;
    items.push({ id: absoluteUrl, title, url: absoluteUrl });
  });

  return items;
}

// For "per-store stock" pages (a store-locator/stock-finder view listing
// several physical stores and each one's stock status). Unlike
// analyzeStockHtml, this doesn't look for one global stock signal - the page
// legitimately contains both "in stock" and "out of stock" text at once, one
// per store, so it has to look for status text specifically near each named
// store rather than anywhere on the page.
//
// This is inherently heuristic without knowing the exact markup of a given
// site's stock-finder widget. It splits the page into one "line" per
// block-level element (so store rows don't get flattened into one run-on
// string) and reads a small window of lines around each store name match -
// by default just the matching line, widen with `lineWindow` if a site puts
// the status in a sibling element instead (store name and "In Stock" as
// separate lines). Either way, the window is always clamped so it can never
// cross into another *target* store's own line - otherwise a wide
// `lineWindow` on a densely-packed list would read the next store's status
// instead of this one's. Check `/watch-list`'s reported per-store status
// against the real page if a given site needs `lineWindow` tuned.
function extractLines($) {
  $('br, p, div, li, tr, td, th, h1, h2, h3, h4, h5, h6').after('\n');
  return $('body')
    .text()
    .split('\n')
    .map((line) => line.replace(/\s+/g, ' ').trim())
    .filter(Boolean);
}

function analyzeStoreStockHtml(html, watch) {
  const $ = cheerio.load(html);
  const lines = extractLines($).map((line) => line.toLowerCase());
  const lineWindow = watch.lineWindow ?? 0;
  const inStockPhrases = (watch.inStockPhrases || STORE_IN_STOCK_PHRASES).map((p) => p.toLowerCase());
  const outOfStockPhrases = (watch.outOfStockPhrases || STORE_OUT_OF_STOCK_PHRASES).map((p) => p.toLowerCase());
  const storeNames = watch.storeNames || [];
  const lowerStoreNames = storeNames.map((s) => s.toLowerCase());

  const lineMatchesOtherStore = (line, ownStore) => lowerStoreNames.some((s) => s !== ownStore && line.includes(s));

  const perStore = storeNames.map((store) => {
    const lowerStore = store.toLowerCase();
    const lineIdx = lines.findIndex((line) => line.includes(lowerStore));
    if (lineIdx === -1) {
      return { store, status: 'not found on page' };
    }

    let start = lineIdx;
    while (start > lineIdx - lineWindow && start > 0 && !lineMatchesOtherStore(lines[start - 1], lowerStore)) start--;
    let end = lineIdx;
    while (end < lineIdx + lineWindow && end < lines.length - 1 && !lineMatchesOtherStore(lines[end + 1], lowerStore)) end++;

    const windowText = lines.slice(start, end + 1).join(' | ');
    const hasOutOfStock = outOfStockPhrases.some((p) => windowText.includes(p));
    const hasInStock = !hasOutOfStock && inStockPhrases.some((p) => windowText.includes(p));
    return { store, status: hasInStock ? 'in stock' : hasOutOfStock ? 'out of stock' : 'unclear' };
  });

  return {
    anyInStock: perStore.some((s) => s.status === 'in stock'),
    perStore,
    detail: perStore.map((s) => `${s.store}: ${s.status}`).join('; ') || 'No store names configured',
  };
}

module.exports = {
  analyzeStockHtml,
  analyzeListingHtml,
  analyzeStoreStockHtml,
  OUT_OF_STOCK_PHRASES,
  DEFAULT_PRODUCT_LINK_SELECTOR,
};
