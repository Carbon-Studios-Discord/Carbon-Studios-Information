import discord
from discord.ext import commands, tasks
from seleniumbase import Driver
from bs4 import BeautifulSoup
import os
from flask import Flask
from threading import Thread
from datetime import datetime
import traceback
import asyncio

# --- 1. RENDER PORT FIX (Flask) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- 2. CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1446846255572451399 
DISCORD_LINK = "https://discord.gg/carbon-studios-1193808450367537213"

intents = discord.Intents.default()
intents.message_content = True # Needed for channel history management
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 3. THE STEALTH SCRAPER ---
def get_executor_data():
    """Bypasses Cloudflare using UC Mode and a Virtual Display."""
    # uc=True renames 'cdc_' variables; xvfb=True mimics a real monitor on Linux
    driver = Driver(uc=True, xvfb=True) 
    try:
        url = "https://weao.xyz/"
        # Reconnect logic helps bypass the 'Wait 5 seconds' Cloudflare page
        driver.uc_open_with_reconnect(url, 6) 
        driver.sleep(5) 
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        results = []
        rows = soup.find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                name = cols[0].get_text(strip=True)
                if name.lower() in ["executor", "status", "name", ""]: continue
                
                raw_status = cols[1].get_text(strip=True)
                status = "✅ Working" if "Working" in raw_status else "❌ Patched" if "Patched" in raw_status else f"🔄 {raw_status}"
                
                link_tag = row.find('a', href=True)
                link = f"[Join Discord]({link_tag['href']})" if link_tag and "discord" in link_tag['href'] else "No Link"
                results.append({"name": name, "status": status, "link": link})
        
        return results
    except Exception as e:
        print(f"Scraper Error: {e}")
        return None
    finally:
        # Crucial to prevent 'Chrome not found' or 'High RAM' errors
        driver.quit()

# --- 4. DISCORD AUTOMATION ---
@tasks.loop(minutes=10)
async def update_display():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    # Run the heavy scraper in a thread so the bot doesn't freeze
    try:
        data = await bot.loop.run_in_executor(None, get_executor_data)
    except Exception as e:
        print(f"Task Execution Error: {e}")
        return

    embed = discord.Embed(
        title="🟣 Carbon Studios | Executor Status",
        description="Real-time status updates from weao.xyz",
        color=0x8A2BE2 if data else 0xFF0000
    )

    if data:
        # Embeds have a 25-field limit
        for item in data[:24]:
            embed.add_field(
                name=f"🔹 {item['name']}",
                value=f"**Status:** {item['status']}\n{item['link']}",
                inline=True
            )
    else:
        embed.add_field(name="⚠️ Connection Error", value="Cloudflare blocked the request. Retrying...", inline=False)

    embed.set_footer(text=f"Last Sync: {datetime.now().strftime('%H:%M')} UTC")

    # Clean up old messages and send new one
    try:
        async for message in channel.history(limit=5):
            if message.author == bot.user:
                await message.delete()
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Discord Sync Error: {e}")

@update_display.error
async def update_display_error(error):
    print(f"CRITICAL LOOP ERROR: {error}")
    traceback.print_exc()

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    if not update_display.is_running():
        update_display.start()

# --- 5. START ---
if __name__ == "__main__":
    keep_alive()
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("BOT_TOKEN is missing from Environment Variables!")
