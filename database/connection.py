

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


import sys
sys.path.append('..')  
from src.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
   
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def test_connection():
    
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False