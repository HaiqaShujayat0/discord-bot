import discord
from discord.ext import commands
from discord import app_commands
import sys
from datetime import datetime
import math
import asyncio

sys.path.append('.')
from services.buffer_service import (
    save_message, 
    update_message, 
    delete_message, 
    get_messages,
    update_reactions,
    bulk_delete_messages,
    message_exists
)
from services.reconciliation_service import run_startup_reconciliation
from config import DISCORD_TOKEN


# Bot setup - intents define 
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.reactions = True  # Enable reaction events

# Bot creation
bot = commands.Bot(command_prefix="!", intents=intents)

# Constants
MESSAGES_PER_PAGE = 5


# ============= Date Input Modal =============
class DateInputModal(discord.ui.Modal):
    """Modal for entering date input with better UX"""
    
    def __init__(self, date_type: str, view: 'MessageSearchView'):
        super().__init__(title=f"📅 Set {date_type} Date")
        self.date_type = date_type
        self.search_view = view
        
        # Get current date as default
        today = datetime.now().strftime("%Y-%m-%d")
        
        self.date_input = discord.ui.TextInput(
            label=f"Enter {date_type} Date",
            placeholder="Format: YYYY-MM-DD",
            default=today,
            required=True,
            max_length=10,
            min_length=10
        )
        self.add_item(self.date_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            date_value = datetime.strptime(self.date_input.value, "%Y-%m-%d")
            
            if self.date_type == "From":
                self.search_view.from_date = date_value
            else:
                self.search_view.to_date = date_value
            
            await self.search_view.update_embed(interaction)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ **Invalid date format!**\nPlease use: `YYYY-MM-DD` (e.g., `2026-02-07`)", 
                ephemeral=True
            )


# ============= Results Pagination View =============
class ResultsPaginationView(discord.ui.View):
    """View for paginated search results"""
    
    def __init__(self, messages: list, filters_summary: str, guild: discord.Guild):
        super().__init__(timeout=300)
        self.messages = messages
        self.filters_summary = filters_summary
        self.guild = guild
        self.current_page = 0
        self.total_pages = max(1, math.ceil(len(messages) / MESSAGES_PER_PAGE))
        
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)
    
    def build_results_embed(self) -> discord.Embed:
        """Build the results embed for current page"""
        start_idx = self.current_page * MESSAGES_PER_PAGE
        end_idx = start_idx + MESSAGES_PER_PAGE
        page_messages = self.messages[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"📋 Search Results (Page {self.current_page + 1} of {self.total_pages})",
            description=f"**{len(self.messages)} total messages** • Sorted by newest first\n\n{self.filters_summary}",
            color=discord.Color.green()
        )
        
        for msg in page_messages:
            # Get channel name
            channel = self.guild.get_channel(msg.channel_id)
            channel_name = f"#{channel.name}" if channel else f"#unknown"
            
            # Format timestamps
            created = msg.created_at.strftime("%b %d, %Y at %I:%M %p") if msg.created_at else "Unknown"
            edited_text = ""
            if msg.edited_at:
                edited_text = f" *(edited {msg.edited_at.strftime('%b %d')})*"
            
            # Content preview (100 chars max)
            content = msg.content[:100] + "..." if msg.content and len(msg.content) > 100 else (msg.content or "*[No text content]*")
            
            # Attachments indicator
            attachments_text = ""
            if msg.has_attachments:
                attachments_text = "\n📎 **Attachments:** Yes"
            
            # Reactions summary
            reactions_text = ""
            if msg.reaction_count and msg.reaction_count > 0:
                reactions_text = f"\n😊 **Reactions:** {msg.reaction_count}"
            elif msg.reactions_data:
                try:
                    reactions = msg.reactions_data
                    if reactions:
                        reaction_parts = [f"{r.get('emoji', '?')} x{r.get('count', 0)}" for r in reactions[:3]]
                        reactions_text = f"\n😊 **Reactions:** {', '.join(reaction_parts)}"
                except:
                    pass
            
            # Build field
            field_name = f"{channel_name}  •  👤 {msg.author_name}"
            field_value = (
                f"📅 {created}{edited_text}\n"
                f"```{content}```"
                f"{attachments_text}{reactions_text}"
            )
            
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        embed.set_footer(text=f"Use buttons below to navigate • Page {self.current_page + 1}/{self.total_pages}")
        
        return embed
    
    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary, row=0)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        embed = self.build_results_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages - 1, self.current_page + 1)
        self.update_buttons()
        embed = self.build_results_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="✕ Close", style=discord.ButtonStyle.danger, row=0)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="*Search results closed.*", embed=None, view=None)


# ============= Message Search View =============
class MessageSearchView(discord.ui.View):
    """Interactive view for message search with filters"""
    
    def __init__(self, guild: discord.Guild, user: discord.User):
        super().__init__(timeout=300)
        self.guild = guild
        self.requesting_user = user
        
        # Filter state
        self.selected_channels = []
        self.selected_members = []
        self.from_date = None
        self.to_date = None
        self.reaction_filter = "any"
    
    def build_embed(self) -> discord.Embed:
        """Build the filter status embed with better visual hierarchy"""
        embed = discord.Embed(
            title="🔍 Message Search",
            description="*Select filters below, then click* **Submit**\n\u200B",
            color=discord.Color.blurple()
        )
        
        # ═══════════════════════════════════════════════════════
        # FILTERS SECTION - Using inline fields for horizontal layout
        # ═══════════════════════════════════════════════════════
        
        # Channel(s)
        if self.selected_channels:
            channels_text = "\n".join([f"• `#{c.name}`" for c in self.selected_channels])
        else:
            channels_text = "• `All channels`"
        
        # Member(s)
        if self.selected_members:
            members_text = "\n".join([f"• `{m.display_name}`" for m in self.selected_members])
        else:
            members_text = "• `All members`"
        
        # Reaction(s)
        reaction_display = {
            "any": "• 🔘 Any",
            "has_reactions": "• ✅ Has reactions",
            "no_reactions": "• ❌ No reactions"
        }
        reaction_text = reaction_display.get(self.reaction_filter, "• 🔘 Any")
        
        # Add filter fields in a row (inline=True for horizontal layout)
        embed.add_field(
            name="📁 CHANNELS",
            value=f"{channels_text}\n\u200B",
            inline=True
        )
        embed.add_field(
            name="👥 MEMBERS", 
            value=f"{members_text}\n\u200B",
            inline=True
        )
        embed.add_field(
            name="😊 REACTIONS",
            value=f"{reaction_text}\n\u200B",
            inline=True
        )
        
        # Date Range section (full width)
        from_text = f"`{self.from_date.strftime('%b %d, %Y')}`" if self.from_date else "`Not set`"
        to_text = f"`{self.to_date.strftime('%b %d, %Y')}`" if self.to_date else "`Not set`"
        
        embed.add_field(
            name="📅 DATE RANGE",
            value=f"**From:** {from_text}  ➜  **To:** {to_text}",
            inline=False
        )
        
        # Footer with requester
        embed.set_footer(
            text=f"Requested by: {self.requesting_user.display_name}",
            icon_url=self.requesting_user.display_avatar.url if self.requesting_user.display_avatar else None
        )
        
        return embed
    
    def build_filters_summary(self) -> str:
        """Build a compact summary of active filters for results view"""
        parts = []
        
        if self.selected_channels:
            channels = ", ".join([f"#{c.name}" for c in self.selected_channels])
            parts.append(f"📁 **Channels:** {channels}")
        
        if self.selected_members:
            members = ", ".join([m.display_name for m in self.selected_members])
            parts.append(f"👥 **Members:** {members}")
        
        if self.from_date or self.to_date:
            from_str = self.from_date.strftime('%b %d, %Y') if self.from_date else "Any"
            to_str = self.to_date.strftime('%b %d, %Y') if self.to_date else "Any"
            parts.append(f"📅 **Date Range:** {from_str} → {to_str}")
        
        if self.reaction_filter != "any":
            reaction_text = "Has reactions" if self.reaction_filter == "has_reactions" else "No reactions"
            parts.append(f"😊 **Reactions:** {reaction_text}")
        
        return "\n".join(parts) if parts else "*No filters applied*"
    
    async def update_embed(self, interaction: discord.Interaction):
        """Update the embed with current filter state"""
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    # ===== Channel Select =====
    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        placeholder="📁 Select Channel(s)",
        min_values=0,
        max_values=5,
        channel_types=[discord.ChannelType.text],
        row=0
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.selected_channels = select.values
        await self.update_embed(interaction)
    
    # ===== Member Select =====
    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="👥 Select Member(s)",
        min_values=0,
        max_values=5,
        row=1
    )
    async def member_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        self.selected_members = select.values
        await self.update_embed(interaction)
    
    # ===== From Date Button =====
    @discord.ui.button(label="📅 From Date", style=discord.ButtonStyle.primary, row=2)
    async def from_date_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DateInputModal("From", self)
        await interaction.response.send_modal(modal)
    
    # ===== To Date Button =====
    @discord.ui.button(label="📅 To Date", style=discord.ButtonStyle.primary, row=2)
    async def to_date_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DateInputModal("To", self)
        await interaction.response.send_modal(modal)
    
    # ===== Reaction Filter Button =====
    @discord.ui.button(label="😊 Set Reaction", style=discord.ButtonStyle.primary, row=2)
    async def reaction_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        options = ["any", "has_reactions", "no_reactions"]
        current_index = options.index(self.reaction_filter)
        self.reaction_filter = options[(current_index + 1) % len(options)]
        await self.update_embed(interaction)
    
    # ===== Submit Button =====
    @discord.ui.button(label="✅ Submit", style=discord.ButtonStyle.success, row=3)
    async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Build filter parameters
        guild_id = self.guild.id
        channel_ids = [c.id for c in self.selected_channels] if self.selected_channels else None
        author_ids = [m.id for m in self.selected_members] if self.selected_members else None
        
        # Query database - get more messages for proper pagination
        messages = get_messages(
            guild_id=guild_id,
            channel_id=channel_ids[0] if channel_ids and len(channel_ids) == 1 else None,
            author_id=author_ids[0] if author_ids and len(author_ids) == 1 else None,
            from_date=self.from_date,
            to_date=self.to_date,
            limit=50  # Get more for pagination
        )
        
        # Filter by multiple channels/members if needed
        if channel_ids and len(channel_ids) > 1:
            messages = [m for m in messages if m.channel_id in channel_ids]
        if author_ids and len(author_ids) > 1:
            messages = [m for m in messages if m.author_id in author_ids]
        
        # Filter by reactions
        if self.reaction_filter == "has_reactions":
            messages = [m for m in messages if (m.reaction_count or 0) > 0]
        elif self.reaction_filter == "no_reactions":
            messages = [m for m in messages if (m.reaction_count or 0) == 0]
        
        # Build results
        if not messages:
            result_embed = discord.Embed(
                title="🔍 Search Results",
                description="**No messages found** matching your filters!\n\nTry adjusting your search criteria.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=result_embed, ephemeral=True)
        else:
            # Create pagination view
            filters_summary = self.build_filters_summary()
            pagination_view = ResultsPaginationView(messages, filters_summary, self.guild)
            result_embed = pagination_view.build_results_embed()
            await interaction.followup.send(embed=result_embed, view=pagination_view, ephemeral=True)




@bot.event
async def on_ready():
    print(f" Bot is online!")
    print(f" Logged in as: {bot.user.name}")
    print(f" Bot ID: {bot.user.id}")
    print(f" Connected to {len(bot.guilds)} server(s)")
    print("-" * 50)

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Sync Failed: {e}")
    
    print("-" * 50)
    
    # Start reconciliation as a background task (non-blocking)
    bot.loop.create_task(run_startup_reconciliation(bot))


@bot.event
async def on_message(message):
    # Ignore if bot itself
    if message.author == bot.user:
        return

    if not message.guild:
        return 
    
    print(f" Message from {message.author}: {message.content[:50]}...")
    save_message(message)
    
    await bot.process_commands(message)


@bot.event
async def on_message_edit(before, after):
    if after.author.bot:
        return

    if not after.guild:
        return

    print(f" Edit : '{before.content[:30]}...''{after.content[:30]}...'")
    update_message(after)


@bot.tree.command(name="list", description="Search buffered messages with filters")
async def list_messages(interaction: discord.Interaction):
    """
    /list - Interactive message search with filters
    """
    # Create the search view
    view = MessageSearchView(interaction.guild, interaction.user)
    embed = view.build_embed()
    
    # Send the interactive filter UI
    await interaction.response.send_message(embed=embed, view=view)


@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    if not message.guild:
        return 
    print(f" deleted : '{message.content[:30]}...' by {message.author}")
    
    delete_message(message.id)


@bot.event
async def on_bulk_message_delete(messages):
    """
    Handle bulk message deletion (e.g., when moderator purges messages).
    Hard deletes all messages from the database.
    """
    if not messages:
        return
    
    # Filter to only guild messages
    guild_messages = [m for m in messages if m.guild]
    if not guild_messages:
        return
    
    message_ids = [m.id for m in guild_messages]
    print(f"🗑️ Bulk delete: {len(message_ids)} messages")
    
    bulk_delete_messages(message_ids)


@bot.event
async def on_reaction_add(reaction, user):
    """
    Handle reaction being added to a message.
    Updates reactions_data and reaction_count in DB.
    """
    # Ignore bot reactions
    if user.bot:
        return
    
    message = reaction.message
    
    # Only handle guild messages
    if not message.guild:
        return
    
    # Check if message exists in our database
    if not message_exists(message.id):
        return
    
    # Build reactions data from current message state
    reactions_data = []
    total_count = 0
    
    for r in message.reactions:
        emoji_str = str(r.emoji)
        reactions_data.append({
            "emoji": emoji_str,
            "count": r.count,
            "is_custom": r.is_custom_emoji()
        })
        total_count += r.count
    
    # Update database
    update_reactions(message.id, reactions_data, total_count)
    print(f"➕ Reaction added: {reaction.emoji} on message {message.id}")


@bot.event
async def on_reaction_remove(reaction, user):
    """
    Handle reaction being removed from a message.
    Updates reactions_data and reaction_count in DB.
    """
    # Ignore bot reactions
    if user.bot:
        return
    
    message = reaction.message
    
    # Only handle guild messages
    if not message.guild:
        return
    
    # Check if message exists in our database
    if not message_exists(message.id):
        return
    
    # Build reactions data from current message state
    reactions_data = []
    total_count = 0
    
    for r in message.reactions:
        emoji_str = str(r.emoji)
        reactions_data.append({
            "emoji": emoji_str,
            "count": r.count,
            "is_custom": r.is_custom_emoji()
        })
        total_count += r.count
    
    # Update database
    update_reactions(message.id, reactions_data, total_count)
    print(f"➖ Reaction removed: {reaction.emoji} on message {message.id}")



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


@bot.command(name="stats")
async def stats(ctx):
    
    from services.buffer_service import get_messages
    
    # Get message count from database (limit high to get count)
    messages = get_messages(guild_id=ctx.guild.id, limit=1000)
    count = len(messages)
    
    await ctx.send(
        f"📊 **Buffer Statistics**\n"
        f"Server: {ctx.guild.name}\n"
        f"Buffered Messages: {count}\n"
        f"Channels: {len(ctx.guild.text_channels)}"
    )


@bot.command(name="roll")
async def roll(ctx, sides: int = 6):
   
    import random
    result = random.randint(1, sides)
    await ctx.send(f" You rolled a **{result}** (d{sides})")


# Bot start 
if __name__ == "__main__":
    print("🔄 Starting Discord Bot...")
    bot.run(DISCORD_TOKEN)


