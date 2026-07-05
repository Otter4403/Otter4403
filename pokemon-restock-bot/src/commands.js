const { SlashCommandBuilder } = require('discord.js');
const { randomUUID } = require('crypto');
const { loadWatches, saveWatches } = require('./storage');
const { runAllChecks } = require('./monitor');
const { ownerUserId } = require('./config');

function isOwner(interaction) {
  return interaction.user.id === ownerUserId;
}

const commands = [
  {
    data: new SlashCommandBuilder()
      .setName('watch-add')
      .setDescription('Track a product or listing page for restocks / new releases')
      .addStringOption((o) => o.setName('nickname').setDescription('Short name for this watch').setRequired(true))
      .addStringOption((o) => o.setName('url').setDescription('Product page or collection/category page URL').setRequired(true))
      .addStringOption((o) =>
        o
          .setName('platform')
          .setDescription('Does the store run on Shopify?')
          .setRequired(true)
          .addChoices({ name: 'Shopify', value: 'shopify' }, { name: 'Generic / other', value: 'generic' })
      )
      .addStringOption((o) =>
        o
          .setName('mode')
          .setDescription('Watch a single product for restock, or a page for new listings')
          .setRequired(true)
          .addChoices({ name: 'Restock alert (single product)', value: 'stock' }, { name: 'New release alert (collection/category page)', value: 'new-release' })
      )
      .addStringOption((o) => o.setName('keywords').setDescription('Comma-separated keywords to match, e.g. "30th anniversary,scarlet & violet" (new-release mode only)'))
      .addStringOption((o) => o.setName('selector').setDescription('Advanced: CSS selector for product links (generic + new-release mode only)')),
    async execute(interaction) {
      if (!isOwner(interaction)) {
        return interaction.reply({ content: "This bot is configured for one owner and that's not you.", ephemeral: true });
      }
      const nickname = interaction.options.getString('nickname');
      const url = interaction.options.getString('url');
      const platform = interaction.options.getString('platform');
      const mode = interaction.options.getString('mode');
      const keywordsRaw = interaction.options.getString('keywords');
      const selector = interaction.options.getString('selector');

      try {
        new URL(url);
      } catch {
        return interaction.reply({ content: `"${url}" doesn't look like a valid URL.`, ephemeral: true });
      }

      const watches = loadWatches();
      if (watches.some((w) => w.nickname.toLowerCase() === nickname.toLowerCase())) {
        return interaction.reply({ content: `A watch named "${nickname}" already exists. Pick another nickname or remove it first.`, ephemeral: true });
      }

      const watch = {
        id: randomUUID(),
        nickname,
        url,
        platform,
        mode,
        keywords: keywordsRaw ? keywordsRaw.split(',').map((k) => k.trim()).filter(Boolean) : [],
        selector: selector || undefined,
        state: {},
      };
      watches.push(watch);
      saveWatches(watches);

      await interaction.reply({
        content: `Added watch **${nickname}** (${platform}/${mode}) for ${url}. It'll be checked on the next poll and baselined (no alert on the first check).`,
        ephemeral: true,
      });
    },
  },
  {
    data: new SlashCommandBuilder()
      .setName('watch-remove')
      .setDescription('Stop tracking a watch')
      .addStringOption((o) => o.setName('nickname').setDescription('Nickname of the watch to remove').setRequired(true)),
    async execute(interaction) {
      if (!isOwner(interaction)) {
        return interaction.reply({ content: "This bot is configured for one owner and that's not you.", ephemeral: true });
      }
      const nickname = interaction.options.getString('nickname');
      const watches = loadWatches();
      const remaining = watches.filter((w) => w.nickname.toLowerCase() !== nickname.toLowerCase());
      if (remaining.length === watches.length) {
        return interaction.reply({ content: `No watch named "${nickname}" found.`, ephemeral: true });
      }
      saveWatches(remaining);
      await interaction.reply({ content: `Removed watch **${nickname}**.`, ephemeral: true });
    },
  },
  {
    data: new SlashCommandBuilder().setName('watch-list').setDescription('List all tracked watches and their last known state'),
    async execute(interaction) {
      const watches = loadWatches();
      if (watches.length === 0) {
        return interaction.reply({ content: 'No watches configured yet. Add one with /watch-add.', ephemeral: true });
      }
      const lines = watches.map((w) => {
        const state = w.state || {};
        let status;
        if (state.lastError) status = `error: ${state.lastError}`;
        else if (w.mode === 'stock') status = state.inStock === undefined ? 'not yet checked' : state.inStock ? 'in stock' : 'out of stock';
        else status = `${(state.seenIds || []).length} items seen`;
        return `**${w.nickname}** (${w.platform}/${w.mode}) - ${status}\n${w.url}`;
      });
      await interaction.reply({ content: lines.join('\n\n').slice(0, 1900), ephemeral: true });
    },
  },
  {
    data: new SlashCommandBuilder().setName('watch-check').setDescription('Run all checks right now instead of waiting for the next poll'),
    async execute(interaction) {
      if (!isOwner(interaction)) {
        return interaction.reply({ content: "This bot is configured for one owner and that's not you.", ephemeral: true });
      }
      await interaction.deferReply({ ephemeral: true });
      const watches = await runAllChecks(interaction.client);
      await interaction.editReply(`Checked ${watches.length} watch(es). Any alerts have been sent separately.`);
    },
  },
];

module.exports = { commands };
