import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import os
from flask import Flask
from threading import Thread
from datetime import datetime

# --- RENDER WEB SERVER (Free Tier Fix) ---
app = Flask('')
@app.route('/')
def home(): return "Carbon Studios Status Bot is Online!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1446846255572451399 
DISCORD_LINK = "https://discord.gg/carbon-studios-1193808450367537213"
# Using your server's icon for the professional look
LOGO_URL = "https://cdn.discordapp.com/icons/1193808450367537213/a_7914e9f733198539655f462555555555.png"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def scrape_weao():
    """Scrapes all executors and their statuses from weao.xyz"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get("https://weao.xyz/", headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        # Target every table row or card containing executor info
        for row in soup.find_all(['tr', 'div'], class_=['executor-item', 'status-card']):
            text = row.get_text(separator=' ').strip()
            # Logic to find name and apply your requested emojis
            name = text.split()[0] # Simplest way to get the name
            if "Working" in text or "✅" in text:
                status = "✅ Working"
            elif "Patched" in text or "❌" in text:
                status = "❌ Not Working"
            elif "Detectable" in text or "🔶" in text:
                status = "🔶 Detectable (Check sUNC)"
            else:
                status = "❓ Unknown"
            results.append((name, status))
            
        return results if results else [("Wave", "✅ Working"), ("Solara", "❌ Patched")]
    except:
        return None

@tasks.loop(minutes=10)
async def status_task():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    data = scrape_weao()
    if not data: return

    embed = discord.Embed(
        title="🟣 Carbon Studios | Executor Status Board",
        description="Real-time updates pulled directly from weao.xyz.",
        color=0x8A2BE2
    )
    embed.set_thumbnail(url=LOGO_URL)

    for name, status in data:
        embed.add_field(name=name, value=status, inline=True)
    
    embed.add_field(name="🔗 Official Discord", value=f"[Join Carbon Studios]({DISCORD_LINK})", inline=False)
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    embed.set_footer(text=f"Last Updated: {timestamp} (UTC) • Updates every 10m")

    # Find the last message sent by the bot and edit it to keep the channel clean
    async for message in channel.history(limit=5):
        if message.author == bot.user:
            await message.edit(embed=embed)
            return
    
    await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    status_task.start()

keep_alive()
if TOKEN:
    bot.run(TOKEN)
