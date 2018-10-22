"""Question mark stats bot
Copyright (C) 2018 ed588

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.
"""

import discord
from discord.ext import commands
import logging
import matplotlib.pyplot as plt
from io import BytesIO
from conf import channel_ids, initial_message

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("question")

bot = commands.Bot("!!")

@bot.event
async def on_ready():
    logger.info("Logged in as {0.user}".format(bot))

@bot.event
async def on_command_error(ctx,err):
    await ctx.send(err)

@bot.command()
async def info(ctx):
    """Information about the bot.

    Prints some info about the bot, including its creator, repository, and license.
    """
    text = "\n".join((
        "**Question mark stats bot**",
        "Created by ed588",
        "The source code for this bot is available at https://github.com/ed588/question-mark-stats.",
        "The source code is AGPL3 licensed. Contributions are welcome."
    ))
    await ctx.send(text)

@commands.guild_only()
@commands.cooldown(1, 60)
@bot.command()
async def go(ctx):
    """Go!

    Grabs all the messages, does the maths, makes a pretty(ish) chart, etc etc.
    This does quite a lot of requesting, so it is currently globally cooldown'd to
    only once every 60 seconds.
    """
    ch = bot.get_channel(channel_ids['monitor'])
    ch_rep = bot.get_channel(channel_ids['report'])
    start = await ch.get_message(initial_message)
    count = 0
    by_users = {}
    async for msg in ch.history(limit=None, after=start):
        if msg.content != "?" and msg.type == discord.MessageType.default:
            await report_bad(msg, ch_rep)
        else:
            count += 1
            if msg.author.name not in by_users:
                by_users[msg.author.name] = 1
            else:
                by_users[msg.author.name] += 1
    await ch_rep.send("I found {} messages that are question marks...".format(count))
    await ch_rep.send("Pie chart coming up...")
    with ch_rep.typing():
        by_users = {k:v for k,v in by_users.items() if v > (count/100)}
        labels, values = zip(*sorted(by_users.items(), key=lambda kv: kv[1], reverse=True))
        nowtotal = sum(values)
        labels=list(labels)
        values=list(values)
        labels.append("Other")
        values.append(count-nowtotal)
        fig, ax = plt.subplots()
        ax.pie(values, labels=labels, autopct=lambda p: '{:.0f}'.format(p * sum(values) / 70), startangle=90)
        ax.axis("equal")
        buff = BytesIO()
        fig.savefig(buff, format="png")
        buff.seek(0)
        f = discord.File(buff, "pie.png")
        await ch_rep.send(file=f)
        buff.close()

async def report_bad(msg, ch_rep):
    lstr = "I found a message saying [{0.content}] (by {0.author}, on {0.created_at})".format(msg)
    await ch_rep.send(lstr)
    try:
        await msg.pin()
    except discord.Forbidden:
        await ch_rep.send("I couldn't pin a message!")

token = open("token", "r").read().rstrip()
bot.run(token)
