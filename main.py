import discord
from discord.ext import commands, tasks
import cloudscraper
from bs4 import BeautifulSoup
import os
from flask import Flask
from threading import Thread
from datetime import datetime
import asyncio

# --- RENDER KEEP-ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Carbon Studios Bot is ALIVE"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1446846255572451399 
DISCORD_LINK = "https://discord.gg/carbon-studios-1193808450367537213"
LOGO_URL = "https://cdn.discordapp.com/icons/1193808450367537213/a_7914e9f733198539655f462555555555.png"

intents = discord.Intents.default()
intents.message_content = True # CRITICAL: Ensure this is enabled in Dev Portal
bot = commands.Bot(command_prefix="!", intents=intents)

def scrape_executors():
    """Scrapes weao.xyz with a fallback if blocked"""
    print("--- Attempting Scrape ---")
    try:
        # CloudScraper mimics a real Chrome browser to bypass Cloudflare
        scraper = cloudscraper.create_scraper(browser='chrome')
        response = scraper.get("https://weao.xyz/")
        
        if response.status_code != 200:
            print(f"Scrape Failed: Status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        executor_list = []
        
        # Look for table rows or cards
        rows = soup.find_all(['tr', 'div'], class_=['card', 'executor', 'item', 'row'])
        if not rows: rows = soup.find_all('tr') # Fallback to any table row

        for row in rows:
            text = row.get_text(separator=" ").strip()
            if len(text) < 3 or "Status" in text[:10]: continue # Skip headers

            # 1. Name
            name_tag = row.find(['h3', 'strong', 'b', 'h4'])
            name = name_tag.get_text(strip=True) if name_tag else text.split()[0]
            
            # 2. Status
            if any(x in text for x in ["Working", "✅"]): status = "✅ Working"
            elif any(x in text for x in ["Patched", "❌"]): status = "❌ Patched"
            elif any(x in text for x in ["Detectable", "🔶"]): status = "🔶 Detectable"
            elif "Updating" in text: status = "🔄 Updating"
            else: continue # Skip if no clear status found

            # 3. Link
            link = "[No Discord]"
            for a in row.find_all('a', href=True):
                if "discord" in a['href']:
                    link = f"[Join Server]({a['href']})"
                    break
            
            executor_list.append({"name": name, "status": status, "link": link})
        
        return executor_list
    except Exception as e:
        print(f"Scrape Error: {e}")
        return None

@tasks.loop(minutes=5)
async def update_status_task():
    print("Running Update Loop...")
    channel = bot.get_channel(CHANNEL_ID)
    
    if not channel:
        print(f"Error: Cannot find channel {CHANNEL_ID}")
        return

    # 1. GET DATA (With Fallback)
    data = scrape_executors()
    
    # If scrape fails, use this fallback list so the bot DOES NOT STAY SILENT
    if not data:
        print("Scrape failed, using Fallback Data.")
        data = [
            {"name": "⚠️ Connection Error", "status": "Could not reach weao.xyz", "link": "[Check Site](https://weao.xyz)"},
            {"name": "Wave", "status": "❓ Unknown", "link": "[Join Discord](https://discord.gg/getwave)"},
            {"name": "Solara", "status": "❓ Unknown", "link": "[Join Discord](https://discord.gg/solara)"}
        ]

    # 2. BUILD EMBED
    embed = discord.Embed(
        title="🟣 Carbon Studios | Executor Status",
        description="Real-time status from weao.xyz",
        color=0x8A2BE2
    )
    embed.set_thumbnail(url=LOGO_URL)

    for ex in data:
        embed.add_field(
            name=f"🔹 {ex['name']}",
            value=f"{ex['status']}\n{ex['link']}",
            inline=True
        )
    
    embed.add_field(name="🔗 Main Hub", value=f"[Carbon Studios Discord]({DISCORD_LINK})", inline=False)
    embed.set_footer(text=f"Last Sync: {datetime.now().strftime('%H:%M UTC')} • Updates every 5m")

    # 3. PURGE & SEND
    try:
        # Delete last 5 messages from ANYONE to keep it clean (requires Manage Messages perm)
        # Or just delete bot's own messages
        async for message in channel.history(limit=10):
            if message.author == bot.user:
                await message.delete()
                await asyncio.sleep(0.5) # Prevent rate limiting
        
        await channel.send(embed=embed)
        print("Embed Sent Successfully.")
    except Exception as e:
        print(f"Sending Error: {e}")
        # If delete fails (no perms), just send it anyway
        await channel.send(embed=embed)

@bot.command()
async def test(ctx):
    """Run this command to force the bot to post immediately"""
    await ctx.send("Force updating status...")
    await update_status_task()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # Run immediately on startup
    if not update_status_task.is_running():
        update_status_task.start()

keep_alive()
if TOKEN: bot.run(TOKEN)
