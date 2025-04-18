
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import datetime
from datetime import UTC
import logging
import a2s
import aiohttp

# Set up logging
logging.basicConfig(level=logging.INFO)

# Configuration
CONFIG = {
    'BOT_TOKEN': 'YOUR_BOT_TOKEN_HERE',  # Discord bot token (get from Discord Developer Portal)
    'SERVER_IP': 'YOUR_SERVER_IP',       # Game server IP (e.g., '148.113.199.214')
    'SERVER_PORT': 27015,                # Game server port (e.g., 27015)
    'SERVER_CHANNEL_ID': 0,              # Discord channel ID for status updates (e.g., 1252566121073344564)
    'STEAM_URL': 'steam://connect/YOUR_SERVER_IP:YOUR_SERVER_PORT',  # Steam connect URL
    'HIDE_PLAYER_NAMES': False,          # True: show "Player 1", False: show real names
    'FALLBACK_API_URL': None             # Optional: URL for fallback API (e.g., 'http://localhost:3000/server')
}

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Button view for server status
class ServerButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Join Server", style=discord.ButtonStyle.primary)
    async def join_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(f"Join the server: `{CONFIG['STEAM_URL']}`", ephemeral=True)

# Function to create the server status embed
def create_server_embed(server_data, status='Online'):
    embed = discord.Embed(
        title=server_data.get('name', 'Conan Exiles Server'),
        description=f"Join the server: `{CONFIG['STEAM_URL']}`",
        color=discord.Color.blue() if status == 'Online' else discord.Color.red(),
        timestamp=datetime.datetime.now(UTC)
    )
    embed.add_field(name='Status', value=status, inline=False)
    embed.add_field(name='Map', value=server_data.get('map', 'Unknown'), inline=True)
    embed.add_field(name='Players', value=f"{server_data.get('players', 0)}/{server_data.get('max_players', 0)}", inline=True)
    player_list = server_data.get('player_list', [])
    if CONFIG['HIDE_PLAYER_NAMES'] != "off" and player_list:
        now = int(time.time())
        if CONFIG['HIDE_PLAYER_NAMES']:
            # Use fake names like "Player 1", "Player 2", etc.
            players_text = '\n'.join([f"Player {i+1} (Time: <t:{now - p['duration'] * 60}:R>)" for i, p in enumerate(player_list)])
        else:
            # Use actual names or "Unknown"
            players_text = '\n'.join([f"{p['name']} (Time: <t:{now - p['duration'] * 60}:R>)" for p in player_list])
        embed.add_field(name='Players Online', value=players_text, inline=False)
    elif CONFIG['HIDE_PLAYER_NAMES'] != "off":
        embed.add_field(name='Players Online', value=f"{server_data.get('players', 0)} players (names unavailable)", inline=False)
    return embed

# Function to query the server
async def query_server():
    try:
        # Try A2S query
        server_address = (CONFIG['SERVER_IP'], CONFIG['SERVER_PORT'])
        server_info = await a2s.ainfo(server_address)
        players = await a2s.aplayers(server_address)
        logging.info("A2S query successful")
        return {
            'name': server_info.server_name or 'Conan Exiles Server',
            'map': server_info.map_name or 'Unknown',
            'players': server_info.player_count,
            'max_players': server_info.max_players,
            'player_list': [{'name': p.name or 'Unknown', 'duration': int(p.duration // 60)} for p in players]
        }
    except Exception as e:
        logging.error(f'A2S error: {e}')
        # Fallback to optional API if configured
        if CONFIG['FALLBACK_API_URL']:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(CONFIG['FALLBACK_API_URL']) as response:
                        js_data = await response.json()
                if js_data.get('status') == 'success':
                    logging.info("Fallback API query successful")
                    return js_data['data']
                else:
                    logging.error("Fallback API query failed")
                    raise Exception('Fallback API failed')
            except Exception as js_e:
                logging.error(f'Fallback API error: {js_e}')
        return None

# Task to update server status embed
@tasks.loop(minutes=5)  # Every 5 minutes
async def update_server_status():
    global SERVER_MESSAGE_ID
    try:
        channel = bot.get_channel(CONFIG['SERVER_CHANNEL_ID'])
        if not channel:
            logging.error(f"Server channel with ID {CONFIG['SERVER_CHANNEL_ID']} not found.")
            return

        server_data = await query_server()
        if server_data:
            embed = create_server_embed(server_data, status='Online')
        else:
            embed = create_server_embed(
                {'name': 'Conan Exiles Server', 'map': 'Unknown', 'players': 0, 'max_players': 0, 'player_list': []},
                status='Offline'
            )

        view = ServerButtonView()  # Add button view

        if SERVER_MESSAGE_ID:
            try:
                message = await channel.fetch_message(SERVER_MESSAGE_ID)
                await message.edit(embed=embed, view=view)
                logging.info("Updated server status embed.")
            except discord.errors.NotFound:
                logging.warning("Server status message not found, sending new one.")
                message = await channel.send(embed=embed, view=view)
                global SERVER_MESSAGE_ID
                SERVER_MESSAGE_ID = message.id
                logging.info(f"Sent new server status message with ID {SERVER_MESSAGE_ID}.")
        else:
            message = await channel.send(embed=embed, view=view)
            global SERVER_MESSAGE_ID
            SERVER_MESSAGE_ID = message.id
            logging.info(f"Sent initial server status message with ID {SERVER_MESSAGE_ID}.")

    except Exception as e:
        logging.error(f"Error in update_server_status: {e}")

@bot.event
async def on_ready():
    logging.info(f'Bot is ready as {bot.user}')
    
    # Start server status task
    if not update_server_status.is_running():
        logging.info("Starting server status update task...")
        update_server_status.start()

# Run the bot
if not CONFIG['BOT_TOKEN'] or CONFIG['BOT_TOKEN'] == 'YOUR_BOT_TOKEN_HERE':
    logging.error("BOT_TOKEN is not set. Please update CONFIG['BOT_TOKEN'] in the script.")
else:
    bot.run(CONFIG['BOT_TOKEN'])
