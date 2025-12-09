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
    """Récupère le CSV depuis Google Sheets"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"Erreur HTTP: {resp.status}")
                return None
            text = await resp.text()
            reader = csv.reader(io.StringIO(text))
            return list(reader)


def get_today_column(rows):
    """Trouve la colonne correspondant à aujourd'hui"""
    # Format recherché : "Aujourd'hui le 9/12" (jour/mois sans le zéro devant)
    today = datetime.now(tz)
    day = today.day  # Sans zéro devant (ex: 9 au lieu de 09)
    month = today.month  # Sans zéro devant (ex: 12)
    today_format = f"Aujourd'hui le {day}/{month}"
    
    print(f"📅 Date recherchée: {today_format}")
    
    if not rows or len(rows) == 0:
        print("❌ Aucune ligne dans le CSV")
        return None
    
    header = rows[0]
    print(f"📋 En-tête complet: {header}")
    
    for i, date_str in enumerate(header):
        if not date_str:
            continue
        
        # Nettoyage plus robuste
        clean_date = date_str.strip().replace('"', '').replace("'", "")
        print(f"  Colonne {i}: '{date_str}' -> nettoyé: '{clean_date}'")
        
        if clean_date == today_format:
            print(f"✅ Date trouvée à la colonne {i}")
            return i
    
    print(f"❌ Aucune colonne ne correspond à {today_format}")
    return None


def build_embed_from_column(rows, col_index):
    """Construit un embed Discord élégant à partir des données"""
    print(f"📝 Construction de l'embed pour la colonne {col_index}")
    
    # Vérifier qu'il y a assez de lignes
    if len(rows) < 25:
        print(f"⚠️ Seulement {len(rows)} lignes dans le CSV (25 attendues)")
    
    # DJs : lignes 4 à 19 → indices 3 à 18
    dj = []
    for i, row in enumerate(rows[3:19], start=4):
        if col_index >= len(row) or len(row) < 1:
            continue
        
        label = row[0].strip() if len(row) > 0 else ""  # Colonne A
        value = row[col_index].strip() if col_index < len(row) else ""  # Colonne du jour
        
        if value:  # Seulement si la colonne du jour a une valeur
            print(f"  DJ ligne {i}: {label} - {value}")
            dj.append((label, value))

    # Modulox : lignes 21 à 25 → indices 20 à 24
    modulox = []
    for i, row in enumerate(rows[20:25], start=21):
        if col_index >= len(row) or len(row) < 1:
            continue
        
        label = row[0].strip() if len(row) > 0 else ""  # Colonne A
        value = row[col_index].strip() if col_index < len(row) else ""  # Colonne du jour
        
        if value:  # Seulement si la colonne du jour a une valeur
            print(f"  Modulox ligne {i}: {label} - {value}")
            modulox.append((label, value))

    if not dj and not modulox:
        print("⚠️ Aucune donnée trouvée dans cette colonne")
        return None

    # Créer une liste des valeurs Modulox pour vérifier les doublons
    modulox_values = [val for _, val in modulox]
    dj_values = [val for _, val in dj]

    # Créer l'embed
    today = datetime.now(tz)
    today_display = f"{today.day}/{today.month}/{today.year}"
    embed = discord.Embed(
        title="📅 Planning du Jour",
        description=f"Programme pour le **{today_display}**",
        color=discord.Color.blue(),
        timestamp=datetime.now(tz)
    )
    
    # Ajouter le champ DJ
    dj_text = ""
    if dj:
        for label, value in dj:
            if value in modulox_values:
                # En rouge avec emoji étoile si dans les deux
                emoji = "⭐"
                dj_text += f"{emoji} **{label}** : ```diff\n- {value}\n```"
            else:
                # Normal avec emoji manette
                emoji = "🎮"
                dj_text += f"{emoji} **{label}** : {value}\n"
    else:
        dj_text = "Aucun DJ prévu"
    
    embed.add_field(name="🎧 DJs du jour", value=dj_text, inline=False)
    
    # Ajouter le champ Modulox
    modulox_text = ""
    if modulox:
        for label, value in modulox:
            if value in dj_values:
                # En rouge avec emoji étoile si dans les deux
                emoji = "⭐"
                modulox_text += f"{emoji} **{label}** : ```diff\n- {value}\n```"
            else:
                # Normal avec emoji cible
                emoji = "🎯"
                modulox_text += f"{emoji} **{label}** : {value}\n"
    else:
        modulox_text = "Aucun Modulox prévu"
    
    embed.add_field(name="🔮 Modulox du jour", value=modulox_text, inline=False)
    
    # Ajouter un footer
    embed.set_footer(text="Bot Planning • Mise à jour automatique")

    return embed
# --------------------------------------------------


# ---------- TÂCHE QUOTIDIENNE ----------
async def daily_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now(tz)
        target = now.replace(hour=POST_HOUR, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        print(f"⏰ Prochaine publication dans {wait_seconds/3600:.2f} heures")
        await asyncio.sleep(wait_seconds)

        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            try:
                rows = await fetch_google_sheet_csv(GOOGLE_SHEET_URL)
                if rows is None:
                    await channel.send("❌ Erreur lors de la récupération du Google Sheet")
                    continue
                    
                col_index = get_today_column(rows)
                if col_index is not None:
                    embed = build_embed_from_column(rows, col_index)
                    if embed:
                        await channel.send(embed=embed)
                    else:
                        await channel.send("⚠️ Colonne trouvée mais aucune donnée disponible")
                else:
                    await channel.send("❌ Aucune colonne ne correspond à aujourd'hui")
            except Exception as e:
                print(f"❌ Erreur dans daily_task: {e}")
                await channel.send(f"❌ Erreur: {e}")
        else:
            print(f"❌ Canal {CHANNEL_ID} introuvable")
# --------------------------------------------------


# ---------- ÉVÉNEMENTS BOT ----------
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    bot.loop.create_task(daily_task())


@bot.command()
async def test(ctx):
    """Commande pour tester le message du jour"""
    print(f"\n🧪 Test lancé par {ctx.author}")
    try:
        rows = await fetch_google_sheet_csv(GOOGLE_SHEET_URL)
        if rows is None:
            await ctx.send("❌ Erreur lors de la récupération du Google Sheet")
            return
            
        col_index = get_today_column(rows)
        if col_index is not None:
            embed = build_embed_from_column(rows, col_index)
            if embed:
                await ctx.send(embed=embed)
            else:
                await ctx.send("⚠️ Colonne trouvée mais aucune donnée disponible")
        else:
            await ctx.send("❌ Aucune colonne ne correspond à aujourd'hui")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        await ctx.send(f"❌ Erreur: {e}")


@bot.command()
async def debug(ctx):
    """Affiche les premières lignes du CSV pour déboguer"""
    try:
        rows = await fetch_google_sheet_csv(GOOGLE_SHEET_URL)
        if rows is None:
            await ctx.send("❌ Erreur lors de la récupération du Google Sheet")
            return
        
        today = datetime.now(tz)
        today_search = f"Aujourd'hui le {today.day}/{today.month}"
        
        debug_msg = f"**Debug CSV:**\n"
        debug_msg += f"Nombre de lignes: {len(rows)}\n"
        debug_msg += f"Date du jour recherchée: {today_search}\n\n"
        debug_msg += f"**Première ligne (dates):**\n"
        
        if rows:
            for i, cell in enumerate(rows[0][:10]):  # Affiche les 10 premières colonnes
                debug_msg += f"Col {i}: `{cell}`\n"
        
        await ctx.send(debug_msg)
    except Exception as e:
        await ctx.send(f"❌ Erreur: {e}")
# --------------------------------------------------

bot.run(TOKEN)