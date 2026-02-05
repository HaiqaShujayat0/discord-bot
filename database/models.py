



from sqlalchemy import Column, BigInteger, String, Text, DateTime, Boolean, JSON

from sqlalchemy.sql import func


from database.connection import Base

class Message(Base):
    __tablename__ = "messages"
    message_id=Column(BigInteger, primary_key=True)
    channel_id=Column(BigInteger,nullable=False)
    guild_id=Column(BigInteger,nullable=False)
    author_id=Column(BigInteger,nullable=False)
    author_name=Column(String(100),nullable=False)
    content=Column(Text,nullable=True)
    created_at=Column(DateTime(timezone=True),nullable=False)
    edited_at=Column(DateTime(timezone=True),nullable=True)
    deleted_at=Column(DateTime(timezone=True),nullable=True)

    is_pinned=Column(Boolean,default=False)
    has_attachments=Column(Boolean,default=False)
    has_embeds=Column(Boolean,default=False)
    reaction_count=Column(BigInteger,default=0)

    raw_data=Column(JSON,nullable=True)
    def __repr__(self):
        return f"<Message(message_id={self.message_id}) by {self.author_name}>"
   





   
