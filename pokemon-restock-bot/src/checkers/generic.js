const axios = require('axios');
const { analyzeStockHtml, analyzeListingHtml } = require('./htmlAnalysis');

// Plain HTTP fetch - fast and cheap, but only sees whatever HTML the server
// sends before any JavaScript runs. Sites that render stock status client-side
// (React/Next/headless-commerce storefronts) won't show up correctly here -
// use the `browser` platform for those instead.

async function fetchHtml(url, userAgent) {
  const res = await axios.get(url, {
    headers: { 'User-Agent': userAgent, Accept: 'text/html' },
    timeout: 15000,
  });
  return res.data;
}

async function checkGenericStock(watch, userAgent) {
  const html = await fetchHtml(watch.url, userAgent);
  return analyzeStockHtml(html, watch);
}

async function checkGenericNewReleases(watch, userAgent) {
  const html = await fetchHtml(watch.url, userAgent);
  return analyzeListingHtml(html, watch);
}

module.exports = { checkGenericStock, checkGenericNewReleases };
