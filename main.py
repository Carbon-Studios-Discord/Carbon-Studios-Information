import discord
from discord.ext import commands, tasks
import cloudscraper
from bs4 import BeautifulSoup
import os
from flask import Flask
from threading import Thread
from datetime import datetime
import asyncio

# --- RENDER PORT FIX ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"

def run():
    # Render requires the bot to listen on a port or it will 'Time Out'
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1446846255572451399 
DISCORD_LINK = "https://discord.gg/carbon-studios-1193808450367537213"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def get_all_executors():
    """Deep scrapes all Mobile, PC, and Mac executors from weao.xyz"""
    try:
        scraper = cloudscraper.create_scraper(browser='chrome')
        response = scraper.get("https://weao.xyz/", timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        all_data = []
        # Target every single row in the status tables
        rows = soup.find_all('tr') 
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                name = cols[0].get_text(strip=True)
                status_raw = cols[1].get_text(strip=True)
                
                # Determine Status Emoji
                if "Working" in status_raw or "✅" in status_raw:
                    status = "✅ Working"
                elif "Patched" in status_raw or "❌" in status_raw:
                    status = "❌ Patched"
                else:
                    status = f"🔄 {status_raw}"

                # EXTRACT DISCORD LINK
                # We look for the <a> tag specifically in this row
                discord_link = "No Link"
                link_tag = row.find('a', href=True)
                if link_tag and "discord" in link_tag['href']:
                    discord_link = f"[Support]({link_tag['href']})"

                all_data.append({"name": name, "status": status, "link": discord_link})
        
        return all_data
    except Exception as e:
        print(f"Scrape Error: {e}")
        return None

@tasks.loop(minutes=10)
async def live_update():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    data = get_all_executors()
    if not data: return

    embed = discord.Embed(title="🟣 Carbon Studios | Live Status Hub", color=0x8A2BE2)
    embed.description = "Real-time executor status & direct support links."
    
    # We loop through EVERY executor found
    for item in data:
        # Format: Name (Status) - Support Link
        embed.add_field(
            name=f"🔹 {item['name']}", 
            value=f"**Status:** {item['status']}\n**Link:** {item['link']}", 
            inline=True
        )

    embed.add_field(name="🔗 Our Server", value=f"[Join Carbon Studios]({DISCORD_LINK})", inline=False)
    embed.set_footer(text=f"Last Updated: {datetime.now().strftime('%H:%M:%S')} UTC")

    # DELETE PREVIOUS BOT MESSAGES (To prevent flooding)
    async for message in channel.history(limit=15):
        if message.author == bot.user:
            await message.delete()

    await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    live_update.start()

keep_alive()
if TOKEN: bot.run(TOKEN)
