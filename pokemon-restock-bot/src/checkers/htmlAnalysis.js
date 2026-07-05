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

module.exports = { analyzeStockHtml, analyzeListingHtml, OUT_OF_STOCK_PHRASES, DEFAULT_PRODUCT_LINK_SELECTOR };
