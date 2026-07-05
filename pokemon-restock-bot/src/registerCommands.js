const { REST, Routes } = require('discord.js');
const { discordToken, clientId, guildId } = require('./config');
const { commands } = require('./commands');

async function main() {
  const rest = new REST().setToken(discordToken);
  const body = commands.map((c) => c.data.toJSON());

  const route = guildId ? Routes.applicationGuildCommands(clientId, guildId) : Routes.applicationCommands(clientId);

  console.log(`Registering ${body.length} command(s) ${guildId ? `to guild ${guildId}` : 'globally (may take up to an hour to appear)'}...`);
  await rest.put(route, { body });
  console.log('Done.');
}

main().catch((err) => {
  console.error('Failed to register commands:', err);
  process.exit(1);
});
