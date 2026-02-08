
from database.models import Message
from database.connection import SessionLocal
from datetime import datetime



def save_message(discord_message):
    
    db = SessionLocal()
    
    try:
        # Check if message already exists in database
        existing = db.query(Message).filter(
            Message.message_id == discord_message.id
        ).first()
        
        if existing:
            print(f" Message {discord_message.id} already exists, skipping")
            return existing
        
        # Create new message object
        db_message = Message(
            message_id=discord_message.id,
            channel_id=discord_message.channel.id,
            guild_id=discord_message.guild.id,
            author_id=discord_message.author.id,
            author_name=str(discord_message.author),
            content=discord_message.content,
            created_at=discord_message.created_at,
            is_pinned=discord_message.pinned,
            has_attachments=len(discord_message.attachments) > 0,
            has_embeds=len(discord_message.embeds) > 0,
            reaction_count=0,
            raw_data={
                "jump_url": discord_message.jump_url,
                "attachments": [
                    {"id": a.id, "filename": a.filename, "url": a.url}
                    for a in discord_message.attachments
                ],
                "embeds": [e.to_dict() for e in discord_message.embeds]
            }
        )
        
        # Add to session and save to database
        db.add(db_message)
        db.commit()
        print(f" Saved message {discord_message.id}")
        return db_message
        
    except Exception as e:
        print(f" Error  occured while saving: {e}")
        db.rollback()
        return None
    finally:
        db.close()           




def update_message(discord_message):

    db=SessionLocal()

    try:

        existing=db.query(Message).filter(Message.message_id==discord_message.id).first()

        if not existing:
            return save_message(discord_message)

        #update if old
        existing.content=discord_message.content
        existing.edited_at=discord_message.edited_at
        existing.is_pinned=discord_message.pinned
        existing.has_attachments=len(discord_message.attachments)>0
        existing.has_embeds=len(discord_message.embeds)>0

        db.commit()
        print(f" Updated message {discord_message.id}")
        return existing
        

    except Exception as e :
        print(f"error while updating the message")
        db.rollback()
        return None

    finally:
        db.close()
        
def delete_message(message_id):
    db=SessionLocal()

    try:
        existing=db.query(Message).filter(Message.message_id==message_id).first()
        if not existing:
            print(f" message {message_id}not found in database")
            return False

        db.delete(existing)
        db.commit()
        print(f"permanently deleted message {message_id}")
        return True

    except Exception as e:
        print(f"error deleting: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def get_messages(guild_id=None, channel_id=None, author_id=None, from_date=None, to_date=None, has_attachments=None, limit=20):
    """Get messages with optional filters"""
    db = SessionLocal()

    try:
        query = db.query(Message).filter(
            Message.guild_id == guild_id
        )
    
        if channel_id:
            query = query.filter(Message.channel_id == channel_id)

        if author_id:
            query = query.filter(Message.author_id == author_id)

        if from_date:
            query = query.filter(Message.created_at >= from_date)

        if to_date: 
            query = query.filter(Message.created_at <= to_date)

        if has_attachments:
            query = query.filter(Message.has_attachments == True)

        messages = query.order_by(Message.created_at.desc()).limit(limit).all()
        return messages

    except Exception as e:
        print(f"error getting messages: {e}")
        return []

    finally:
        db.close()


def get_message_by_id(message_id):
    """Get a single message by ID"""
    db = SessionLocal()
    
    try:
        message = db.query(Message).filter(Message.message_id == message_id).first()
        return message
    except Exception as e:
        print(f"Error getting message {message_id}: {e}")
        return None
    finally:
        db.close()


def update_reactions(message_id, reactions_data, reaction_count):
    """Update reactions for a message"""
    db = SessionLocal()
    
    try:
        message = db.query(Message).filter(Message.message_id == message_id).first()
        
        if not message:
            print(f"Message {message_id} not found for reaction update")
            return False
        
        message.reactions_data = reactions_data
        message.reaction_count = reaction_count
        
        db.commit()
        print(f"Updated reactions for message {message_id}: {reaction_count} total")
        return True
        
    except Exception as e:
        print(f"Error updating reactions: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def bulk_delete_messages(message_ids):
    """Delete multiple messages efficiently (hard delete)"""
    if not message_ids:
        return 0
    
    db = SessionLocal()
    
    try:
        deleted_count = db.query(Message).filter(
            Message.message_id.in_(message_ids)
        ).delete(synchronize_session=False)
        
        db.commit()
        print(f"Bulk deleted {deleted_count} messages")
        return deleted_count
        
    except Exception as e:
        print(f"Error in bulk delete: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


def get_channel_message_ids(channel_id, limit=100):
    """Get message IDs for a channel (used for reconciliation)"""
    db = SessionLocal()
    
    try:
        messages = db.query(Message.message_id).filter(
            Message.channel_id == channel_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        
        return {m.message_id for m in messages}
        
    except Exception as e:
        print(f"Error getting channel message IDs: {e}")
        return set()
    finally:
        db.close()


def message_exists(message_id):
    """Check if a message exists in the database"""
    db = SessionLocal()
    
    try:
        exists = db.query(Message).filter(Message.message_id == message_id).first() is not None
        return exists
    except Exception as e:
        print(f"Error checking message existence: {e}")
        return False
    finally:
        db.close()