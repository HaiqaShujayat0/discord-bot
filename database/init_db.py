import asyncio
from database.connection import engine, Base
from database.models import Message

async def create_tables():
    """Create all tables asynchronously"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created successfully")    

async def drop_tables():
    """Drop all tables asynchronously"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("✅ Tables dropped successfully")    

if __name__ == "__main__":
    asyncio.run(create_tables())