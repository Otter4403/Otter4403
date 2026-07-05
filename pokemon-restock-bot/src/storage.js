const fs = require('fs');
const path = require('path');
const { watchesFile } = require('./config');

function ensureFile() {
  if (!fs.existsSync(watchesFile)) {
    fs.mkdirSync(path.dirname(watchesFile), { recursive: true });
    fs.writeFileSync(watchesFile, '[]');
  }
}

function loadWatches() {
  ensureFile();
  const raw = fs.readFileSync(watchesFile, 'utf8');
  try {
    return JSON.parse(raw);
  } catch (err) {
    throw new Error(`config/watches.json is not valid JSON: ${err.message}`);
  }
}

function saveWatches(watches) {
  ensureFile();
  const tmpFile = `${watchesFile}.tmp`;
  fs.writeFileSync(tmpFile, JSON.stringify(watches, null, 2));
  fs.renameSync(tmpFile, watchesFile);
}

module.exports = { loadWatches, saveWatches };
