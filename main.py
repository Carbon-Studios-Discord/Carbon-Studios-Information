import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import os
from flask import Flask
from threading import Thread
from datetime import datetime

# --- RENDER KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Carbon Studios Status Bot: ACTIVE"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1446846255572451399 
DISCORD_LINK = "https://discord.gg/carbon-studios-1193808450367537213"
LOGO_URL = "https://cdn.discordapp.com/icons/1193808450367537213/a_7914e9f733198539655f462555555555.png"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def scrape_full_data():
    """Scrapes every executor, their status, and their Discord invite from weao.xyz"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get("https://weao.xyz/", headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        executor_data = []
        
        # weao.xyz typically uses 'card' or 'row' structures for each executor
        # We find all containers that hold executor information
        containers = soup.find_all(['div', 'tr'], class_=['card', 'executor', 'item']) 
        
        for item in containers:
            text_content = item.get_text(separator=" ").strip()
            if not text_content: continue
            
            # Extract Name (usually the first strong or header tag)
            name_tag = item.find(['h3', 'h4', 'strong', 'b'])
            name = name_tag.get_text(strip=True) if name_tag else text_content.split()[0]
            
            # Determine Status Emoji
            if "Working" in text_content or "✅" in text_content:
                status = "✅ Working"
            elif "Patched" in text_content or "❌" in text_content:
                status = "❌ Patched"
            elif "Detectable" in text_content or "🔶" in text_content:
                status = "🔶 Detectable"
            else:
                status = "❓ Unknown"
            
            # Extract Discord Link for this specific executor
            discord_url = "No Link"
            links = item.find_all('a', href=True)
            for link in links:
                href = link['href']
                if "discord.gg" in href or "discord.com/invite" in href:
                    discord_url = f"[Join]({href})"
                    break
            
            executor_data.append({"name": name, "status": status, "link": discord_url})
            
        return executor_data
    except Exception as e:
        print(f"Scrape Error: {e}")
        return None

@tasks.loop(minutes=10)
async def update_status_board():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    data = scrape_full_data()
    if not data: return

    embed = discord.Embed(
        title="🟣 Carbon Studios | All Executor Statuses",
        description="Live data including official Discord invites for each executor.",
        color=0x8A2BE2
    )
    embed.set_thumbnail(url=LOGO_URL)

    for exec in data:
        # Format: Name - Status - [Join Link]
        embed.add_field(
            name=f"🔹 {exec['name']}", 
            value=f"{exec['status']}\n{exec['link']}", 
            inline=True
        )
    
    embed.add_field(name="🔗 Main Hub", value=f"[Carbon Studios Discord]({DISCORD_LINK})", inline=False)
    
    current_time = datetime.now().strftime("%I:%M %p")
    embed.set_footer(text=f"Sync Time: {current_time} • Source: weao.xyz")

    # Message Editing Logic (prevents spam)
    async for message in channel.history(limit=5):
        if message.author == bot.user:
            await message.edit(embed=embed)
            return
    await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    update_status_board.start()

keep_alive()
if TOKEN: bot.run(TOKEN)
