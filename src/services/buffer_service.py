
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

