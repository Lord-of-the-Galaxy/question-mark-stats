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
import matplotlib
# force matplotlib to not use any kind of Xwindows backend - allows use on headless systems
matplotlib.use("Agg")
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
    logger.error(str(err), exc_info=err)
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

async def check_and_get_all():
    """Crawls the given channel, looking for ? messages.
    It checks them and then returns all of them.

    The idea is that this gets called for *any* command that needs the messages,
    and therefore the messages will be checked whenever any command is run.
    """
    channel = bot.get_channel(channel_ids['monitor'])
    start = await channel.get_message(initial_message)
    messages = []
    async for msg in channel.history(limit=None, after=start):
        # TODO: more checks on the message here
        if msg.content != "?" and msg.type == discord.MessageType.default:
            await report_bad(msg, ch_rep)
        else:
            messages.append(msg)
    return messages

async def send_figure(fig, ch):
    """Sends a matplotlib figure to a given channel."""
    buff = BytesIO()
    fig.savefig(buff, format="png")
    buff.seek(0)
    f = discord.File(buff, "plot.png")
    await ch.send(file=f)
    buff.close()


@commands.guild_only()
@commands.cooldown(1, 60)
@bot.command()
async def go(ctx):
    """Go!

    Grabs all the messages, does the maths, makes a pretty(ish) chart, etc etc.
    This does quite a lot of requesting, so it is currently globally cooldown'd to
    only once every 60 seconds.

    Note: this command is going to be removed in the future and replaced with several
    different commands.
    """
    ch_rep = bot.get_channel(channel_ids['report'])
    async with ch_rep.typing():
        messages = await check_and_get_all()
        by_users = {}
        for msg in messages:
            if msg.author.name not in by_users:
                by_users[msg.author.name] = 1
            else:
                by_users[msg.author.name] += 1
        await ch_rep.send("I found {} messages that are question marks...".format(len(messages)))
        await ch_rep.send("Pie chart coming up...")
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
        await send_figure(fig, ch_rep)

async def report_bad(msg, ch_rep):
    lstr = "I found a message saying [{0.content}] (by {0.author}, on {0.created_at})".format(msg)
    await ch_rep.send(lstr)
    try:
        await msg.pin()
    except discord.Forbidden:
        await ch_rep.send("I couldn't pin a message!")


@commands.guild_only()
@commands.cooldown(1, 60)
@bot.command()
async def history(ctx, *, opt="14"):
    """Shows activity over time.

    By default, shows activity over the last 14 days. Pass a different number as an argument
    to override this. Pass "all" as an argument to get all history.
    """
    print(opt)
    from datetime import date, timedelta
    ch_rep = bot.get_channel(channel_ids['report'])
    async with ch_rep.typing():
        messages = await check_and_get_all()
        dates = {}
        for msg in messages:
            date = msg.created_at.date()
            if date not in dates:
                dates[date] = 1
            else:
                dates[date] += 1
        items=dates.items()
        if opt != "all":
            try:
                days = int(opt)
            except ValueError:
                days = 7
            # TODO: make check_and_get_all have a `since` argument to avoid needing this here
            items = [i for i in items if i[0] > (date.today() - timedelta(days=days))]
        dates_only = [i[0] for i in items]
        counts = [i[1] for i in items]
        fig, ax = plt.subplots()
        ax.plot_date(dates_only, counts, 'b-')
        await send_figure(fig, ch_rep)


token = open("token", "r").read().rstrip()
bot.run(token)
