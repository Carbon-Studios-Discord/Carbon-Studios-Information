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
from pyvirtualdisplay import Display  # This is the secret weapon

# --- 1. RENDER SERVER CONFIG ---
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

# --- 2. BOT CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1446846255572451399 
DISCORD_LINK = "https://discord.gg/carbon-studios-1193808450367537213"

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 3. THE "NUCLEAR" SCRAPER ---
def get_executor_data():
    display = None
    driver = None
    try:
        # A. MANUALLY START A FAKE MONITOR
        # This tricks the browser into thinking it has a screen (1920x1080)
        display = Display(visible=0, size=(1920, 1080))
        display.start()
        
        # B. START BROWSER IN "HEADED" MODE (NOT HEADLESS)
        # We say headless=False because we have the fake monitor above.
        # This is 100% undetectable by Cloudflare because it IS a real browser.
        driver = Driver(uc=True, headless=False)
        
        url = "https://weao.xyz/"
        # Connect and wait for the Cloudflare "checking your browser" screen to pass
        driver.uc_open_with_reconnect(url, 10) 
        driver.sleep(8) # Generous wait time for the page to load
        
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
        print(f"Scraper Crashed: {e}")
        traceback.print_exc()
        return None
        
    finally:
        # C. CLEANUP IS MANDATORY
        # We must close the driver AND the fake screen or the server memory fills up
        if driver:
            try: driver.quit()
            except: pass
        if display:
            try: display.stop()
            except: pass

# --- 4. DISCORD LOOP ---
@tasks.loop(minutes=10)
async def update_display():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    # Run scraper in a separate thread to prevent bot lag
    data = await bot.loop.run_in_executor(None, get_executor_data)

    embed = discord.Embed(
        title="🟣 Carbon Studios | Executor Status",
        description="Real-time status updates via Virtual Display",
        color=0x8A2BE2 if data else 0xFF0000
    )

    if data:
        for item in data[:24]:
            embed.add_field(
                name=f"🔹 {item['name']}",
                value=f"**Status:** {item['status']}\n{item['link']}",
                inline=True
            )
    else:
        embed.add_field(name="⚠️ Connection Error", value="Could not bypass Cloudflare. Retrying...", inline=False)

    embed.set_footer(text=f"Last Sync: {datetime.now().strftime('%H:%M')} UTC")

    try:
        async for message in channel.history(limit=5):
            if message.author == bot.user:
                await message.delete()
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Discord Error: {e}")

@bot.event
async def on_ready():
    print(f"Bot Active: {bot.user}")
    if not update_display.is_running():
        update_display.start()

if __name__ == "__main__":
    keep_alive()
    if TOKEN:
        bot.run(TOKEN)
