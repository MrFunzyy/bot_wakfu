import discord
from discord.ext import commands
import aiohttp
import os
from datetime import datetime, timedelta
import asyncio
import pytz
from dotenv import load_dotenv
load_dotenv()

# ------------ CONFIGURATION ------------
TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_DOC_URL = os.getenv("GOOGLE_DOC_URL")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
POST_HOUR = 2  # Publication à 02h00 heure française
# ----------------------------------------

tz = pytz.timezone("Europe/Paris")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

async def fetch_google_doc_text(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()

def parse_dj_modulox(text: str):
    dj = []
    modulox = []
    current = None

    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("dj"):
            current = "dj"
            continue
        if line.lower().startswith("modulox"):
            current = "modulox"
            continue

        if line.startswith("-") or line.startswith("*"):
            item = line[1:].strip()
            if current == "dj":
                dj.append(item)
            elif current == "modulox":
                modulox.append(item)

    return dj, modulox

def build_message(dj, modulox):
    message = "**DJ du jour :**"
    for item in dj:
        if item in modulox:
            message += f"- **{item}**"
        else:
            message += f"- {item}"

    message += "**Modulox du jour :**"
    for item in modulox:
        if item in dj:
            message += f"- **{item}**"
        else:
            message += f"- {item}"

    return message

async def daily_task():
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = datetime.now(tz)
        target = now.replace(hour=POST_HOUR, minute=0, second=0, microsecond=0)

        if now > target:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        print(f"Prochaine publication dans {wait_seconds/3600:.2f} heures")

        await asyncio.sleep(wait_seconds)

        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            text = await fetch_google_doc_text(GOOGLE_DOC_URL)
            dj, modulox = parse_dj_modulox(text)
            msg = build_message(dj, modulox)
            await channel.send(msg)

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    bot.loop.create_task(daily_task())

@bot.command()
async def test(ctx):
    text = await fetch_google_doc_text(GOOGLE_DOC_URL)
    dj, modulox = parse_dj_modulox(text)
    msg = build_message(dj, modulox)
    await ctx.send(msg)

bot.run(TOKEN)
