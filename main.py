import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import os
from flask import Flask
from threading import Thread
from datetime import datetime
import asyncio

# --- RENDER WEB SERVER (Keep-Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Carbon Studios Live Board: ACTIVE"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1446846255572451399 
DISCORD_LINK = "https://discord.gg/carbon-studios-1193808450367537213"
LOGO_URL = "https://cdn.discordapp.com/icons/1193808450367537213/a_7914e9f733198539655f462555555555.png"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def scrape_weao_data():
    """Scrapes ALL executors, statuses, and links from weao.xyz"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get("https://weao.xyz/", headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        executor_list = []
        # Target table rows on weao.xyz
        rows = soup.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                # Get Name and Status text
                name = cells[0].get_text(strip=True)
                status_text = cells[1].get_text(strip=True)
                
                # Assign Emojis
                if "Working" in status_text or "✅" in status_text:
                    status = "✅ Working"
                elif "Patched" in status_text or "❌" in status_text:
                    status = "❌ Patched"
                elif "Detectable" in status_text or "🔶" in status_text:
                    status = "🔶 Detectable"
                else:
                    status = f"❓ {status_text}"
                
                # Find the specific Discord link for this row
                link_tag = row.find('a', href=True)
                d_link = f"[Join Discord]({link_tag['href']})" if link_tag and "discord" in link_tag['href'] else "No Link"
                
                executor_list.append({"name": name, "status": status, "link": d_link})
        
        return executor_list
    except Exception as e:
        print(f"Scrape Error: {e}")
        return None

@tasks.loop(minutes=10)
async def refresh_status_board():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    # 1. Scrape the new data
    data = scrape_weao_data()
    if not data: return

    # 2. Build the Embed
    embed = discord.Embed(
        title="🟣 Carbon Studios | All Executor Statuses",
        description="Live data pulled from weao.xyz. Join the executor servers for specific support.",
        color=0x8A2BE2
    )
    embed.set_thumbnail(url=LOGO_URL)

    for ex in data:
        embed.add_field(
            name=f"🔹 {ex['name']}",
            value=f"**Status:** {ex['status']}\n**Link:** {ex['link']}",
            inline=True
        )
    
    embed.add_field(name="🔗 Main Hub", value=f"[Carbon Studios Discord]({DISCORD_LINK})", inline=False)
    
    current_time = datetime.now().strftime("%I:%M %p")
    embed.set_footer(text=f"Last Live Sync: {current_time} • Updates every 10m")

    # 3. DELETE OLD MESSAGES (To prevent flooding)
    # This removes all previous bot messages in the channel before sending the fresh one
    async for message in channel.history(limit=20):
        if message.author == bot.user:
            try:
                await message.delete()
            except:
                pass

    # 4. Send the updated board
    await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Status Bot logged in as {bot.user}")
    refresh_status_board.start()

keep_alive()
if TOKEN:
    bot.run(TOKEN)
