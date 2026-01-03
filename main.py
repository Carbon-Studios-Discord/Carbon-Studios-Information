import discord
from discord.ext import commands, tasks
import cloudscraper
from bs4 import BeautifulSoup
import os
from flask import Flask
from threading import Thread
from datetime import datetime

# --- FLASK SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): 
    return "Bot is Active"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- BOT CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = 1446846255572451399 
DISCORD_LINK = "https://discord.gg/carbon-studios-1193808450367537213"

# Message Content Intent is required to delete history effectively
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix="!", intents=intents)

def get_executor_data():
    """Scrapes executor names, status, and discord links."""
    try:
        # We use a more specific browser fingerprint to bypass Cloudflare
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
        response = scraper.get("https://weao.xyz/", timeout=20)
        
        if response.status_code != 200:
            print(f"Failed to reach site. Status: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        all_executors = []
        
        # weao.xyz uses table rows (tr) for their status lists
        rows = soup.find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            # Ensure it's a valid data row (Name and Status columns)
            if len(cols) >= 2:
                name = cols[0].get_text(strip=True)
                
                # Filter out header rows
                if name.lower() in ["executor", "status", "name"]:
                    continue

                status_text = cols[1].get_text(strip=True)
                
                # Formatting Status with Emojis
                if "Working" in status_text or "✅" in status_text:
                    status = "✅ Working"
                elif "Patched" in status_text or "❌" in status_text:
                    status = "❌ Patched"
                else:
                    status = f"🔄 {status_text}"

                # Find the Discord link within the row
                link_tag = row.find('a', href=True)
                if link_tag and "discord" in link_tag['href']:
                    discord_link = f"[Join]({link_tag['href']})"
                else:
                    discord_link = "N/A"

                all_executors.append({
                    "name": name,
                    "status": status,
                    "link": discord_link
                })
        
        return all_executors
    except Exception as e:
        print(f"Scraper Error: {e}")
        return None

@tasks.loop(minutes=5)
async def update_status():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return

    data = get_executor_data()
    
    # Create the Embed
    embed = discord.Embed(
        title="🟣 Carbon Studios | Executor Status", 
        description="Real-time status updates and support links.",
        color=0x8A2BE2,
        timestamp=datetime.utcnow()
    )

    if data:
        for item in data[:25]: # Embeds have a limit of 25 fields
            embed.add_field(
                name=f"🔹 {item['name']}",
                value=f"**Status:** {item['status']}\n**Discord:** {item['link']}",
                inline=True
            )
    else:
        embed.description = "⚠️ **Connection Error**: Could not reach weao.xyz. Retrying in 5m..."
        embed.color = discord.Color.red()

    embed.add_field(name="🔗 Main Hub", value=f"[Join Carbon Studios]({DISCORD_LINK})", inline=False)
    embed.set_footer(text="Last Updated")

    # --- DELETE OLD MESSAGES TO PREVENT FLOODING ---
    try:
        # Search last 10 messages for the bot's previous post
        async for message in channel.history(limit=10):
            if message.author == bot.user:
                await message.delete()
    except Exception as e:
        print(f"Cleanup Error: {e}")

    # Send the fresh update
    await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    if not update_status.is_running():
        update_status.start()

if __name__ == "__main__":
    keep_alive()
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Error: No BOT_TOKEN found!")
