import discord
from discord.ext import commands, tasks
from seleniumbase import Driver
from bs4 import BeautifulSoup
import os
from flask import Flask
from threading import Thread
from datetime import datetime

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
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 3. YOUR SCRAPER LOGIC ---
def get_executor_data():
    """Uses SeleniumBase UC Mode to bypass Cloudflare."""
    # uc=True is for 'Undetected', xvfb=True is for Linux servers like Render
    driver = Driver(uc=True, xvfb=True) 
    try:
        url = "https://weao.xyz/"
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
        driver.quit()

# --- 4. DISCORD AUTOMATION ---
@tasks.loop(minutes=10)
async def update_display():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel: return

    data = get_executor_data()

    embed = discord.Embed(
        title="🟣 Carbon Studios | Executor Status",
        description="Real-time status updates from weao.xyz",
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
        embed.add_field(name="⚠️ Connection Error", value="Cloudflare blocked the request. Retrying in 10m...", inline=False)

    embed.add_field(name="🔗 Our Server", value=f"[Join Carbon Studios]({DISCORD_LINK})", inline=False)
    embed.set_footer(text=f"Last Sync: {datetime.now().strftime('%H:%M')} UTC")

    # Delete old bot messages to keep it clean
    async for message in channel.history(limit=5):
        if message.author == bot.user:
            await message.delete()
    
    await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    if not update_display.is_running():
        update_display.start()

# --- 5. START EVERYTHING ---
if __name__ == "__main__":
    keep_alive()
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("ERROR: BOT_TOKEN environment variable not found!")
