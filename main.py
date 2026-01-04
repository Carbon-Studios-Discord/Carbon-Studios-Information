import discord
from discord.ext import commands, tasks
import cloudscraper
from bs4 import BeautifulSoup
import os
from flask import Flask
from threading import Thread
from datetime import datetime

# --- FLASK SERVER (For Render) ---
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

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1446846255572451399 
DISCORD_LINK = "https://discord.gg/carbon-studios-1193808450367537213"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Global variable to store the message ID so we can edit it
status_msg_id = None

def get_executor_data():
    """Bypasses protection and scrapes executor data."""
    try:
        # Using a more aggressive browser imitation
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
        # Adding a real User-Agent header is often the missing piece
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
        response = scraper.get("https://weao.xyz/", headers=headers, timeout=20)
        
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Finding all table rows
        rows = soup.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                name = cols[0].get_text(strip=True)
                # Skip header rows
                if name.lower() in ["executor", "status", "name", ""] or len(name) > 30:
                    continue

                raw_status = cols[1].get_text(strip=True)
                status = "✅ Working" if "Working" in raw_status else "❌ Patched" if "Patched" in raw_status else f"🔄 {raw_status}"

                link_tag = row.find('a', href=True)
                link = f"[Join Discord]({link_tag['href']})" if link_tag and "discord" in link_tag['href'] else "No Link"

                results.append({"name": name, "status": status, "link": link})
        
        return results
    except Exception as e:
        print(f"Scraper Error: {e}")
        return None

@tasks.loop(minutes=5)
async def update_display():
    global status_msg_id
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
        # Displaying all found executors
        for item in data[:24]:
            embed.add_field(
                name=f"🔹 {item['name']}",
                value=f"**Status:** {item['status']}\n{item['link']}",
                inline=True
            )
    else:
        embed.add_field(name="⚠️ Connection Error", value="Could not reach weao.xyz. Retrying...", inline=False)

    embed.add_field(name="🔗 Main Hub", value=f"[Join Carbon Studios]({DISCORD_LINK})", inline=False)
    embed.set_footer(text=f"Last Sync: {datetime.now().strftime('%H:%M')} UTC • Updates every 5m")

    # Clean up and Send/Edit logic
    try:
        # Step 1: Find any existing message by the bot in the channel and delete it
        # This prevents flooding if the bot restarts
        async for message in channel.history(limit=5):
            if message.author == bot.user:
                await message.delete()
        
        # Step 2: Send a fresh message
        await channel.send(embed=embed)
        
    except Exception as e:
        print(f"Display Error: {e}")

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    if not update_display.is_running():
        update_display.start()

if __name__ == "__main__":
    keep_alive()
    if TOKEN:
        bot.run(TOKEN)
