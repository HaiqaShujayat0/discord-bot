from database.connection import engine, Base

from database.models import Message

def create_tables():
    Base.metadata.create_all(engine)
    print("Tables created successfully")    


def drop_tables():
    Base.metadata.drop_all(engine)
    print("Tables dropped successfully")    


if __name__=="__main__":
    create_tables()