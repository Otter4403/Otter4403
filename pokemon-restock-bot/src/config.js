require('dotenv').config();

function required(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

module.exports = {
  discordToken: required('DISCORD_TOKEN'),
  clientId: required('CLIENT_ID'),
  guildId: process.env.GUILD_ID || null,
  ownerUserId: required('OWNER_USER_ID'),
  notifyChannelId: process.env.NOTIFY_CHANNEL_ID || null,
  pollIntervalMinutes: Math.max(3, Number(process.env.POLL_INTERVAL_MINUTES) || 5),
  userAgent: process.env.USER_AGENT || 'PokemonRestockBot/1.0',
  watchesFile: require('path').join(__dirname, '..', 'config', 'watches.json'),
};
