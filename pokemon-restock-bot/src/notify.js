const { ownerUserId, notifyChannelId } = require('./config');

async function sendAlert(client, { title, description, url }) {
  const mention = `<@${ownerUserId}>`;
  const embed = {
    title: title.slice(0, 256),
    url,
    description,
    color: 0xffcb05,
    timestamp: new Date().toISOString(),
  };

  if (notifyChannelId) {
    const channel = await client.channels.fetch(notifyChannelId);
    await channel.send({ content: mention, embeds: [embed] });
    return;
  }

  const user = await client.users.fetch(ownerUserId);
  await user.send({ content: mention, embeds: [embed] });
}

module.exports = { sendAlert };
