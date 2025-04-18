# ConanServerStatus

"""
Conan Exiles Server Status Bot
This Discord bot queries a game server (using A2S protocol) and displays its status in an embed,
updated every 5 minutes. It includes a "Join Server" button linking to the server via Steam.
The bot can optionally use a fallback API for server data if configured.

Dependencies:
- discord.py (`pip install discord.py`)
- a2s (`pip install python-a2s`)
- aiohttp (`pip install aiohttp`)

Setup:
1. Install dependencies listed above.
2. Update the CONFIG dictionary below with your Discord bot token, server details, and channel ID.
3. Run the script: `python server_status_bot.py`

Note: Ensure the Discord bot has permissions to read/send messages and manage embeds in the target channel.
"""
