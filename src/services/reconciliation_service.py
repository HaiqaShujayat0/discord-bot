

import asyncio
import discord
from services.buffer_service import (
    save_message, 
    delete_message, 
    get_channel_message_ids,
    message_exists,
    bulk_delete_messages
)


async def reconcile_channel(channel: discord.TextChannel, chunk_size: int = 100):
   
    try:
        print(f"  📥 Reconciling #{channel.name}...")
        
        # Get message IDs currently in our database for this channel
        db_message_ids = get_channel_message_ids(channel.id, limit=chunk_size)
        
        # Fetch recent messages from Discord API
        discord_messages = []
        discord_message_ids = set()
        
        async for message in channel.history(limit=chunk_size):
            discord_messages.append(message)
            discord_message_ids.add(message.id)
        
        # Find messages to ADD (in Discord but not in DB)
        messages_to_add = [
            msg for msg in discord_messages 
            if msg.id not in db_message_ids
        ]
        
        # Find messages to DELETE (in DB but not in Discord)
        messages_to_delete = db_message_ids - discord_message_ids
        
        # Add missing messages
        added_count = 0
        for msg in messages_to_add:
            if not msg.author.bot:  # Skip bot messages
                save_message(msg)
                added_count += 1
        
        # Delete removed messages (hard delete)
        deleted_count = 0
        if messages_to_delete:
            deleted_count = bulk_delete_messages(list(messages_to_delete))
        
        if added_count > 0 or deleted_count > 0:
            print(f"    ✅ #{channel.name}: +{added_count} added, -{deleted_count} deleted")
        else:
            print(f"    ✅ #{channel.name}: up to date")
            
        # Yield control to event loop (don't block other tasks)
        # await asyncio.sleep(0.1)
        
        return added_count, deleted_count
        
    except discord.Forbidden:
        print(f"    ⚠️ No permission to read #{channel.name}")
        return 0, 0
    except Exception as e:
        print(f"    ❌ Error reconciling #{channel.name}: {e}")
        return 0, 0


async def reconcile_guild(guild: discord.Guild):
    """
    Reconcile all text channels in a guild.
    
    Args:
        guild: The Discord guild (server) to reconcile
    """
    print(f"\n🔄 Reconciling guild: {guild.name}")
    
    total_added = 0
    total_deleted = 0
    channels_processed = 0
    
    # Get all text channels the bot can access
    for channel in guild.text_channels:
        # Check if bot has permission to read message history
        permissions = channel.permissions_for(guild.me)
        
        if permissions.read_message_history and permissions.view_channel:
            added, deleted = await reconcile_channel(channel)
            total_added += added
            total_deleted += deleted
            channels_processed += 1
            
            # Rate limit: wait between channels to avoid API throttling
            await asyncio.sleep(0.5)
    
    print(f"✅ Guild reconciliation complete: {channels_processed} channels, +{total_added} added, -{total_deleted} deleted\n")
    
    return total_added, total_deleted


async def run_startup_reconciliation(bot):
    """
    Run reconciliation for all guilds on bot startup.
    
    This is called from on_ready() as a background task.
    It doesn't block command handling.
    
    Args:
        bot: The Discord bot instance
    """
    print("\n" + "=" * 50)
    print("🔍 STARTING RECONCILIATION")
    print("=" * 50)
    
    total_added = 0
    total_deleted = 0
    
    for guild in bot.guilds:
        try:
            added, deleted = await reconcile_guild(guild)
            total_added += added
            total_deleted += deleted
        except Exception as e:
            print(f"❌ Error reconciling guild {guild.name}: {e}")
    
    print("=" * 50)
    print(f" RECONCILIATION COMPLETE")
    print(f"   Total: +{total_added} messages added, -{total_deleted} messages deleted")
    print("=" * 50 + "\n")
