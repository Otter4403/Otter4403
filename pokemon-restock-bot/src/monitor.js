const cron = require('node-cron');
const { loadWatches, saveWatches } = require('./storage');
const { sendAlert } = require('./notify');
const { userAgent, pollIntervalMinutes } = require('./config');
const { checkShopifyStock, checkShopifyNewReleases } = require('./checkers/shopify');
const { checkGenericStock, checkGenericNewReleases } = require('./checkers/generic');
const { checkBrowserStock, checkBrowserNewReleases } = require('./checkers/browser');

const STOCK_CHECKERS = {
  shopify: checkShopifyStock,
  generic: checkGenericStock,
  browser: checkBrowserStock,
};

const NEW_RELEASE_CHECKERS = {
  shopify: checkShopifyNewReleases,
  generic: checkGenericNewReleases,
  browser: checkBrowserNewReleases,
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function itemMatchesKeywords(item, keywords) {
  if (keywords.length === 0) return true;
  const haystack = [item.title, ...(item.tags || [])].join(' ').toLowerCase();
  return keywords.some((k) => haystack.includes(k));
}

async function checkWatch(client, watch) {
  watch.state = watch.state || {};
  try {
    if (watch.mode === 'stock') {
      const checker = STOCK_CHECKERS[watch.platform];
      if (!checker) throw new Error(`Unknown platform "${watch.platform}"`);
      const result = await checker(watch, userAgent);
      const wasInStock = watch.state.inStock;
      const isFirstCheck = watch.state.lastCheckedAt === undefined;

      watch.state.inStock = result.inStock;
      watch.state.lastTitle = result.title;
      watch.state.lastCheckedAt = new Date().toISOString();
      watch.state.lastError = null;

      // Don't alert on the very first check - that just establishes the baseline.
      if (!isFirstCheck && result.inStock && wasInStock === false) {
        await sendAlert(client, {
          title: `Back in stock: ${result.title || watch.nickname}`,
          description: `${result.detail}\n${watch.url}`,
          url: watch.url,
        });
        return true;
      }
      return false;
    }

    if (watch.mode === 'new-release') {
      const lister = NEW_RELEASE_CHECKERS[watch.platform];
      if (!lister) throw new Error(`Unknown platform "${watch.platform}"`);
      const items = await lister(watch, userAgent);
      const seenIds = new Set(watch.state.seenIds || []);
      const isFirstCheck = watch.state.lastCheckedAt === undefined;
      const keywords = (watch.keywords || []).map((k) => k.toLowerCase());

      const newItems = items.filter((item) => !seenIds.has(item.id));
      watch.state.seenIds = items.map((item) => item.id);
      watch.state.lastCheckedAt = new Date().toISOString();
      watch.state.lastError = null;

      // Don't alert on the very first check - that just establishes the baseline
      // of what's already listed, otherwise every existing product "alerts" once.
      if (isFirstCheck) return false;

      const alertable = newItems.filter((item) => itemMatchesKeywords(item, keywords));
      for (const item of alertable) {
        await sendAlert(client, {
          title: `New listing: ${item.title}`,
          description: `Spotted on ${watch.nickname}\n${item.url}`,
          url: item.url,
        });
      }
      return alertable.length > 0;
    }

    throw new Error(`Unknown watch mode "${watch.mode}"`);
  } catch (err) {
    watch.state.lastError = err.message;
    watch.state.lastCheckedAt = new Date().toISOString();
    console.error(`[watch:${watch.nickname}] check failed: ${err.message}`);
    return false;
  }
}

async function runAllChecks(client) {
  const watches = loadWatches();
  for (const watch of watches) {
    await checkWatch(client, watch);
    // Small stagger between requests so we're not hammering several stores at once.
    await sleep(1500);
  }
  saveWatches(watches);
  return watches;
}

function startScheduler(client) {
  const cronExpression = `*/${pollIntervalMinutes} * * * *`;
  console.log(`Polling every ${pollIntervalMinutes} minute(s) (${cronExpression})`);

  cron.schedule(cronExpression, () => {
    runAllChecks(client).catch((err) => console.error('Scheduled check run failed:', err));
  });
}

module.exports = { startScheduler, runAllChecks, checkWatch };
