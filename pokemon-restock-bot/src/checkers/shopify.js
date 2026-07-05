const axios = require('axios');

// Many small/medium NZ hobby & game stores run on Shopify, which exposes a
// clean, unauthenticated JSON API - no HTML scraping needed:
//   https://store.com/products/some-product.json      -> single product + variants
//   https://store.com/products.json                    -> whole catalog (paginated)
//   https://store.com/collections/<handle>/products.json -> single collection

function toProductJsonUrl(productUrl) {
  const u = new URL(productUrl);
  u.search = '';
  u.hash = '';
  if (!u.pathname.endsWith('.json')) {
    u.pathname = `${u.pathname.replace(/\/$/, '')}.json`;
  }
  return u.toString();
}

function toCollectionProductsJsonUrl(collectionOrShopUrl) {
  const u = new URL(collectionOrShopUrl);
  const match = u.pathname.match(/\/collections\/[^/]+/);
  const basePath = match ? match[0] : '';
  return `${u.origin}${basePath}/products.json?limit=250`;
}

async function fetchJson(url, userAgent) {
  const res = await axios.get(url, {
    headers: { 'User-Agent': userAgent, Accept: 'application/json' },
    timeout: 15000,
  });
  return res.data;
}

async function checkShopifyStock(watch, userAgent) {
  const jsonUrl = toProductJsonUrl(watch.url);
  const data = await fetchJson(jsonUrl, userAgent);
  const product = data.product;
  if (!product) {
    throw new Error(`No product found at ${jsonUrl}`);
  }
  const variants = product.variants || [];
  const inStock = variants.some((v) => v.available === true);
  return {
    inStock,
    title: product.title,
    detail: inStock
      ? `In stock (${variants.filter((v) => v.available).length}/${variants.length} variants available)`
      : 'Out of stock',
  };
}

async function checkShopifyNewReleases(watch, userAgent) {
  const jsonUrl = toCollectionProductsJsonUrl(watch.url);
  const data = await fetchJson(jsonUrl, userAgent);
  const products = data.products || [];
  return products.map((p) => ({
    id: String(p.id),
    title: p.title,
    tags: Array.isArray(p.tags) ? p.tags : String(p.tags || '').split(',').map((t) => t.trim()),
    url: `${new URL(watch.url).origin}/products/${p.handle}`,
    publishedAt: p.published_at,
  }));
}

module.exports = { checkShopifyStock, checkShopifyNewReleases, toProductJsonUrl, toCollectionProductsJsonUrl };
