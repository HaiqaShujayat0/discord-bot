

import os
from dotenv import load_dotenv

# .env file load karo
load_dotenv()

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Discord Bot Token  
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file!")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN not found in .env file!")

# Test print (baad mein remove karenge)
print("✅ Config loaded successfully!")
print(f"Database URL starts with: {DATABASE_URL[:20]}...")