import discord
from discord.ext import commands
import aiohttp
import os
from datetime import datetime, timedelta
import asyncio
import pytz
import csv
import io
from dotenv import load_dotenv

# ------------ VARIABLES D'ENVIRONNEMENT ------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_DOC_URL")
CHANNEL_ID = os.getenv("CHANNEL_ID")
POST_HOUR = 2  # Publication à 02h00

if not TOKEN or not GOOGLE_SHEET_URL or not CHANNEL_ID:
    raise ValueError("DISCORD_TOKEN, GOOGLE_DOC_URL et CHANNEL_ID doivent être définies !")
CHANNEL_ID = int(CHANNEL_ID)
# ---------------------------------------------------

tz = pytz.timezone("Europe/Paris")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ---------- FONCTIONS ----------
async def fetch_google_sheet_csv(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.text()
            reader = csv.reader(io.StringIO(text))
            return list(reader)


def get_today_column(rows):
    today = datetime.now(tz).date()
    header = rows[0]
    for i, date_str in enumerate(header):
        date_str = date_str.strip().replace('"', '')  # enlève les guillemets
        if not date_str:
            continue
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):  # on teste plusieurs formats
            try:
                row_date = datetime.strptime(date_str, fmt).date()
                if row_date == today:
                    return i
                break
            except ValueError:
                continue
    return None



def build_message_from_column(rows, col_index):
    # DJs : lignes 4 à 19 → indices 3 à 18
    dj = []
    for row in rows[3:19]:
        if col_index >= len(row):
            continue
        cell = row[col_index].strip()
        if cell:
            dj.append(cell)

    # Modulox : lignes 21 à 25 → indices 20 à 24
    modulox = []
    for row in rows[20:25]:
        if col_index >= len(row):
            continue
        cell = row[col_index].strip()
        if cell:
            modulox.append(cell)

    message = "**DJ du jour :**\n"
    for item in dj:
        if item in modulox:
            message += f"- **{item}**\n"
        else:
            message += f"- {item}\n"

    message += "**Modulox du jour :**\n"
    for item in modulox:
        if item in dj:
            message += f"- **{item}**\n"
        else:
            message += f"- {item}\n"

    return message
# --------------------------------------------------


# ---------- TÂCHE QUOTIDIENNE ----------
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
            rows = await fetch_google_sheet_csv(GOOGLE_SHEET_URL)
            col_index = get_today_column(rows)
            if col_index is not None:
                msg = build_message_from_column(rows, col_index)
                await channel.send(msg)
            else:
                await channel.send("Aucun DJ/Modulox trouvé pour aujourd'hui !")
# --------------------------------------------------


# ---------- ÉVÉNEMENTS BOT ----------
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    bot.loop.create_task(daily_task())


@bot.command()
async def test(ctx):
    """Commande pour tester le message du jour"""
    rows = await fetch_google_sheet_csv(GOOGLE_SHEET_URL)
    col_index = get_today_column(rows)
    if col_index is not None:
        msg = build_message_from_column(rows, col_index)
        await ctx.send(msg)
    else:
        await ctx.send("Aucun DJ/Modulox trouvé pour aujourd'hui !")
# --------------------------------------------------

bot.run(TOKEN)
