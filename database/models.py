

from sqlalchemy import Column, BigInteger, String, Text, DateTime, Boolean, JSON, Index
from sqlalchemy.sql import func
from database.connection import Base

class Message(Base):
    __tablename__ = "messages"
    
    message_id = Column(BigInteger, primary_key=True)
    channel_id = Column(BigInteger, nullable=False, index=True)
    guild_id = Column(BigInteger, nullable=False, index=True)
    author_id = Column(BigInteger, nullable=False, index=True)
    author_name = Column(String(100), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    edited_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    is_pinned = Column(Boolean, default=False)
    has_attachments = Column(Boolean, default=False)
    has_embeds = Column(Boolean, default=False)
    reaction_count = Column(BigInteger, default=0)

    # Separate JSON columns for easier querying (clean approach)
    attachments_data = Column(JSON, nullable=True)  # Array of attachment objects
    embeds_data = Column(JSON, nullable=True)  # Array of embed objects
    reactions_data = Column(JSON, nullable=True)  # Array of reaction objects
    raw_data = Column(JSON, nullable=True)  # Full message snapshot for reference
    
    def __repr__(self):
        return f"<Message(message_id={self.message_id}) by {self.author_name}>"

# Add composite indexes for common query patterns
Index('idx_guild_channel_created', Message.guild_id, Message.channel_id, Message.created_at)
Index('idx_guild_author_created', Message.guild_id, Message.author_id, Message.created_at)
   





   
