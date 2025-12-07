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

# ------------ CHARGEMENT DES VARIABLES D'ENVIRONNEMENT ------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_DOC_URL")
CHANNEL_ID = os.getenv("CHANNEL_ID")
POST_HOUR = 2  # Publication à 02h00 heure française

if not TOKEN or not GOOGLE_SHEET_URL or not CHANNEL_ID:
    raise ValueError("Les variables d'environnement DISCORD_TOKEN, GOOGLE_DOC_URL et CHANNEL_ID doivent être définies !")
CHANNEL_ID = int(CHANNEL_ID)
# ------------------------------------------------------------------

tz = pytz.timezone("Europe/Paris")

intents = discord.Intents.default()
intents.message_content = True  # nécessaire pour les commandes prefixées
bot = commands.Bot(command_prefix="!", intents=intents)


# ---------- FONCTIONS POUR LE GOOGLE SHEET ----------
async def fetch_google_sheet_csv(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.text()
            reader = csv.reader(io.StringIO(text))
            return list(reader)


def get_today_column(rows):
    today = datetime.now(tz).date()
    header = rows[0]  # Ligne 1 = dates
    col_index = None
    for i, date_str in enumerate(header):
        try:
            date_str = date_str.strip()
            if "-" in date_str:
                row_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            elif "/" in date_str:
                row_date = datetime.strptime(date_str, "%d/%m/%Y").date()
            else:
                continue
            if row_date == today:
                col_index = i
                break
        except Exception:
            continue
    return col_index


def build_message_from_column(rows, col_index):
    # DJs : lignes 4 à 19 → indices 3 à 18
    dj = []
    for row in rows[3:19]:
        cell = row[col_index].strip()
        if cell:
            dj.extend([item.strip() for item in cell.split(",")])

    # Modulox : lignes 21 à 25 → indices 20 à 24
    modulox = []
    for row in rows[20:25]:
        cell = row[col_index].strip()
        if cell:
            modulox.extend([item.strip() for item in cell.split(",")])

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

# ------------------------------------------------------


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
# ------------------------------------------------------


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
# ------------------------------------------------------

bot.run(TOKEN)
