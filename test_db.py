from sqlalchemy import create_engine
from app.database import Base, DATABASE_URL

engine = create_engine(DATABASE_URL)

try:
    print("Connecting to the database...")
    with engine.connect() as connection:
        print("Connection successful!")
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
except Exception as e:
    print(f"Error: {e}")
