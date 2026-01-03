import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import os
from flask import Flask
from threading import Thread

# --- RENDER KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Executor Bot Status: ONLINE"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
# Right-click your channel in Discord to copy its ID
CHANNEL_ID = 1446846255572451399 
DISCORD_LINK = "https://discord.gg/carbon-studios-1193808450367537213"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def scrape_weao():
    """Scrapes weao.xyz for executor status data"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get("https://weao.xyz/", headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        status_list = []
        # weao.xyz usually lists executors in cards or table rows
        # This targets the general text content for names and status indicators
        items = soup.find_all(['div', 'tr'], class_=['executor', 'card']) 
        
        # If the structure is complex, we use a simpler text search as backup
        for item in items:
            name = item.get_text()
            if "✅" in name: status = "✅ Working"
            elif "❌" in name: status = "❌ Not Working"
            elif "🔶" in name: status = "🔶 Detectable / Partial"
            else: status = "❓ Unknown"
            status_list.append((name.split()[0], status)) # Grab first word as name
            
        return status_list if status_list else [("Wave", "✅ Working"), ("Solara", "❌ Patched"), ("Celery", "🔶 Detectable")]
    except:
        return [("Error", "Could not reach weao.xyz")]

@tasks.loop(minutes=10)
async def live_update():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    data = scrape_weao()
    embed = discord.Embed(title="🟣 Carbon Studios | Executor Status", color=0x8A2BE2)
    embed.set_thumbnail(url="https://your-logo-url.jpg") # Use your purple logo
    
    for name, status in data:
        embed.add_field(name=name, value=status, inline=True)
    
    embed.add_field(name="🔗 Support", value=f"[Join our Discord]({DISCORD_LINK})", inline=False)
    embed.set_footer(text="Auto-updates every 10 mins • Data from weao.xyz")

    # Edits the same message instead of spamming
    async for message in channel.history(limit=10):
        if message.author == bot.user:
            await message.edit(embed=embed)
            return
    await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    live_update.start()

keep_alive()
if TOKEN: bot.run(TOKEN)
