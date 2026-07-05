const axios = require('axios');
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

async function fetchHtml(url, userAgent) {
  const res = await axios.get(url, {
    headers: { 'User-Agent': userAgent, Accept: 'text/html' },
    timeout: 15000,
  });
  return cheerio.load(res.data);
}

// Best-effort heuristic: a lot of storefronts don't expose a clean stock API,
// so this just checks the rendered page text for common out-of-stock phrasing.
// Tune `watch.outOfStockPhrases` per-store if the default gives false positives.
async function checkGenericStock(watch, userAgent) {
  const $ = await fetchHtml(watch.url, userAgent);
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

// For "new-release" mode against a category/search/collection page. Extracts
// product links via a CSS selector (configurable per watch since every site's
// markup differs) and diffs them against previously seen links in monitor.js.
async function checkGenericNewReleases(watch, userAgent) {
  const $ = await fetchHtml(watch.url, userAgent);
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

module.exports = { checkGenericStock, checkGenericNewReleases, OUT_OF_STOCK_PHRASES };
