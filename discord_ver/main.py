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
            command_prefix='?',
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

        # Sync Commands
        guild = discord.Object(id=int(os.getenv("OSBC")))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

bot = SurvyApp()

# Menu Utama
@bot.tree.command(
    name="menu",
    description="Showing all about Survy's command"
)
async def main_menu(interaction: discord.Interaction):
    if interaction.channel.id not in CHANNEL_ID:
        await interaction.response.send_message(
            "❌ Command only works in certain channel!",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="SERVICES",
        description="📚 Here are some features that might help you\n with your Whiteout Survival needs\n please have a look 🥰",
        color=discord.Color.blue()
    )
    embed.set_author(name="Survy MENU", icon_url="https://i.imgur.com/XKb9U3D.jpeg")
    embed.add_field(
        name="🎁 Gift Code Redeem",
        value="`/redeem` to show more redeem options",
        inline=False
    )
    
    await interaction.response.send_message(
        embed=embed,
        ephemeral=False
    )

@bot.tree.command(
    name="redeem",
    description="Showing redeem options"
)
async def redeem_menu(interaction: discord.Interaction):
    if interaction.channel.id not in CHANNEL_ID:
        await interaction.response.send_message(
            "❌ Command only works in certain channel!",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="OPTIONS",
        description="Choose redeem method that you need ⬇️",
        color=discord.Color.gold()
    )
    embed.set_author(name="Survy REDEEM", icon_url="https://i.imgur.com/XKb9U3D.jpeg")
    # Personal Redeem
    embed.add_field(
        name="👤 Personal Redeem",
        value="`/predeem <player_id> <code>`\n"
              "Example: `/1redeem 12345 ABCDEF`",
        inline=False
    )
    # Group Redeem
    embed.add_field(
        name="👥 Group Redeem (Coming Soon)",
        value="`/gredeem <id1,id2,...> <code>`\n"
              "Coming Soon",
        inline=False
    )
    
    embed.set_footer(text="This bot currently still in developing phase")
    
    await interaction.response.send_message(
        embed=embed,
        ephemeral=False
    )

@bot.event
async def on_ready():
    print(f'{bot.user.name} is ready to serve!')

if __name__ == '__main__':
    bot.run(dc_token)