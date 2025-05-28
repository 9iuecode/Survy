import discord
import sys
import os
from dotenv import load_dotenv
from discord.ext import commands

# Configuration
BASEDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASEDIR))
load_dotenv()
dc_token = os.getenv("token")
CHANNEL_ID = [1364460757084930101]


class SurvyApp(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
        command_prefix = '?',
        intents=intents,
        help_command=None
    )
    
    async def setup_hook(self):
        # Load Cogs
        cogsdir = os.path.join(BASEDIR, 'cogs')
        for filename in os.listdir(cogsdir):
            if filename.endswith('.py') and not filename.startswith('_'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f'{filename} loaded!')

        # Sync a Certain Location
        guild = discord.Object(id=int(os.getenv("OSBC")))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
bot = SurvyApp()

# Discord Commands
@bot.event
async def on_ready():
    print(f'{bot.user.name} is ready to serve!')

if __name__ == '__main__':
    bot.run(dc_token)