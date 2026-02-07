

import discord
from discord.ext import commands
import sys

sys.path.append('.')
from services.buffer_service import save_message, update_message, delete_message, get_messages

from discord import app_commands

from config import DISCORD_TOKEN


# Bot setup - intents define 
# Intents what the bot can access 
intents = discord.Intents.default()
intents.message_content = True  # Messages padhne ki permission
intents.guilds = True           # Server info access
intents.members = True          # Member info access

# Bot creation
bot = commands.Bot( command_prefix="!",intents=intents)


@bot.event
async def on_ready():
    
    print(f" Bot is online!")
    print(f" Logged in as: {bot.user.name}")
    print(f" Bot ID: {bot.user.id}")
    print(f" Connected to {len(bot.guilds)} server(s)")
    print("-" * 50)

    #slash commands here syncing comamnds available when bot connects
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Sync Failed: {e}")
    
    print("-" * 50)
            
        

@bot.event  #on message event
async def on_message(message):
   
    # ignore if bot itself
    if message.author == bot.user:
        return

    if not message.guild:
        return 
    
    # print msg info 
    print(f" Message from {message.author}: {message.content[:50]}...")
    
    save_message(message)

    
    # Commands process 
    await bot.process_commands(message)

 # update message event
@bot.event
async def on_message_edit(before,after):
    if after.author.bot:
        return

    if not after.guild:
        return

    print(f" Edit : '{before.content[:30]}...''{after.content[:30]}...'")

    update_message(after)


@bot.tree.command(name="list", description="Show all buffered messages")
async def list_messages(interaction: discord.Interaction):
    """
    /list - Database se saari messages dikhao
    """
    # Get guild ID
    guild_id = interaction.guild.id
    
    # Get messages from database
    messages = get_messages(guild_id=guild_id, limit=20)
    
    # If no messages found
    if not messages:
        await interaction.response.send_message(
            "❌ No messages found in database!",
            ephemeral=True
        )
        return
    
    # Create embed
    embed = discord.Embed(
        title="📋 Buffered Messages",
        description=f"Found {len(messages)} message(s)",
        color=discord.Color.blue()
    )
    
    # Add each message to embed
    for msg in messages[:10]:
        if msg.content:
            content = msg.content[:100]
        else:
            content = "[No content]"
        
        embed.add_field(
            name=f"👤 {msg.author_name}",
            value=f"```{content}```",
            inline=False
        )
    
    # Send ephemeral response
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    if not message.guild:
        return 
    print(f" deleted : '{message.content[:30]}...' by {message.author}")
    
    delete_message(message.id)





@bot.command(name="ping")
async def ping(ctx):
   
    await ctx.send("🏓 Pong!")


@bot.command(name="hello")
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.name}!")


@bot.command(name="info")
async def info(ctx):
    server=ctx.guild
    await ctx.send(
        f" Server info \n"
        f"Name: {server.name}\n"
        f"Members:{server.member_count}\n"
        f"Created:{server.created_at.strftime('%Y-%m-%d')}"

    )


# Bot start 
if __name__ == "__main__":
    print("🔄 Starting Discord Bot...")
    bot.run(DISCORD_TOKEN)


