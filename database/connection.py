from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import sys
sys.path.append('..')  
from src.config import DATABASE_URL

# Create synchronous engine
engine = create_engine(DATABASE_URL, echo=False)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()
