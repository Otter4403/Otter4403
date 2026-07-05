const { Client, GatewayIntentBits } = require('discord.js');
const { discordToken } = require('./config');
const { commands } = require('./commands');
const { startScheduler, runAllChecks } = require('./monitor');

const client = new Client({ intents: [GatewayIntentBits.Guilds] });
const commandsByName = new Map(commands.map((c) => [c.data.name, c]));

client.once('ready', async () => {
  console.log(`Logged in as ${client.user.tag}`);
  startScheduler(client);
  // Run one check immediately on startup so watches don't sit idle until the first poll interval.
  runAllChecks(client).catch((err) => console.error('Startup check run failed:', err));
});

client.on('interactionCreate', async (interaction) => {
  if (!interaction.isChatInputCommand()) return;
  const command = commandsByName.get(interaction.commandName);
  if (!command) return;
  try {
    await command.execute(interaction);
  } catch (err) {
    console.error(`Command ${interaction.commandName} failed:`, err);
    const payload = { content: 'Something went wrong running that command.', ephemeral: true };
    if (interaction.deferred || interaction.replied) {
      await interaction.editReply(payload);
    } else {
      await interaction.reply(payload);
    }
  }
});

client.login(discordToken);
