import discord
from discord.ext import commands, tasks
import cloudscraper # specialized library to bypass bot protection
from bs4 import BeautifulSoup
import os
from flask import Flask
from threading import Thread
from datetime import datetime
import asyncio

# --- RENDER KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Carbon Studios Status Bot is RUNNING"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1446846255572451399 
DISCORD_LINK = "https://discord.gg/carbon-studios-1193808450367537213"
LOGO_URL = "https://cdn.discordapp.com/icons/1193808450367537213/a_7914e9f733198539655f462555555555.png"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def scrape_executors():
    """Scrapes weao.xyz using CloudScraper to bypass protection"""
    print("--- Starting Scrape ---")
    try:
        scraper = cloudscraper.create_scraper() # Creates a browser-like session
        response = scraper.get("https://weao.xyz/")
        
        if response.status_code != 200:
            print(f"Error: Website returned status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        executor_list = []
        
        # Strategy: Find all common containers (cards, table rows)
        # We look for anything that contains 'status' or known classes
        cards = soup.find_all(['div', 'tr'], class_=['card', 'executor', 'item', 'row'])
        
        # Fallback: If no specific classes found, look for ANY table row
        if not cards:
            cards = soup.find_all('tr')

        print(f"Found {len(cards)} potential items")

        for card in cards:
            text = card.get_text(separator=" ").strip()
            # Skip empty or irrelevant rows
            if len(text) < 5 or "Status" in text[:10]: continue 

            # 1. Get Name (First bold text or first word)
            name_tag = card.find(['h3', 'strong', 'b', 'h4'])
            name = name_tag.get_text(strip=True) if name_tag else text.split()[0]
            
            # 2. Get Status
            if "Working" in text or "✅" in text:
                status = "✅ Working"
            elif "Patched" in text or "❌" in text:
                status = "❌ Patched"
            elif "Detectable" in text or "🔶" in text:
                status = "🔶 Detectable"
            elif "Updating" in text:
                status = "🔄 Updating"
            else:
                # If we can't determine status, skip it (likely not an executor row)
                continue

            # 3. Get Discord Link
            discord_link = "[No Discord Found]"
            all_links = card.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                if "discord.gg" in href or "discord.com" in href:
                    discord_link = f"[Join Server]({href})"
                    break
            
            # Add to list
            executor_list.append({"name": name, "status": status, "link": discord_link})

        print(f"Successfully extracted {len(executor_list)} executors")
        return executor_list

    except Exception as e:
        print(f"CRITICAL SCRAPE ERROR: {e}")
        return None

@tasks.loop(minutes=5)
async def update_status_task():
    print("Running Update Task...")
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Error: Could not find channel. Check CHANNEL_ID.")
        return

    # 1. Get Data
    data = scrape_executors()
    if not data:
        print("No data found. Skipping update.")
        return

    # 2. Build Embed
    embed = discord.Embed(
        title="🟣 Carbon Studios | Live Executor Status",
        description="Real-time status for all executors. Click 'Join Server' for support.",
        color=0x8A2BE2
    )
    embed.set_thumbnail(url=LOGO_URL)

    for ex in data:
        embed.add_field(
            name=f"🔹 {ex['name']}", 
            value=f"**Status:** {ex['status']}\n**Link:** {ex['link']}", 
            inline=True
        )

    embed.add_field(name="🔗 Official Hub", value=f"[Carbon Studios Discord]({DISCORD_LINK})", inline=False)
    embed.set_footer(text=f"Last Updated: {datetime.now().strftime('%H:%M:%S UTC')} • Source: weao.xyz")

    # 3. DELETE OLD MESSAGES & SEND NEW
    # We search the last 10 messages. If the bot sent them, delete them.
    try:
        async for message in channel.history(limit=10):
            if message.author == bot.user:
                await message.delete()
                await asyncio.sleep(1) # Sleep to avoid rate limits
        
        # Send the fresh message
        await channel.send(embed=embed)
        print("Message updated successfully.")
        
    except Exception as e:
        print(f"Message Error: {e}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    update_status_task.start()

keep_alive()
if TOKEN:
    bot.run(TOKEN)
