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
            reader = csv.DictReader(io.StringIO(text))
            return list(reader)


def get_today_row(rows):
    today_str = datetime.now(tz).strftime("%d/%m/%Y")  # adapte le format si besoin
    for row in rows:
        if row["Date"] == today_str:  # remplace "Date" par le nom exact de ta colonne date
            return row
    return None


def build_message_from_row(row):
    # Adaptation selon le format exact des colonnes DJ et Modulox
    dj = [item.strip() for item in row["DJ"].split(",")]
    modulox = [item.strip() for item in row["Modulox"].split(",")]

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
            today_row = get_today_row(rows)
            if today_row:
                msg = build_message_from_row(today_row)
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
    today_row = get_today_row(rows)
    if today_row:
        msg = build_message_from_row(today_row)
        await ctx.send(msg)
    else:
        await ctx.send("Aucun DJ/Modulox trouvé pour aujourd'hui !")
# ------------------------------------------------------

bot.run(TOKEN)
