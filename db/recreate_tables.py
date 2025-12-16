# db/recreate_tables.py
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.config import engine, Base
from db.models import Task  # Import to register the model

async def recreate_tables():
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
        print("Dropped all tables")
        
        # Create all tables with new schema
        await conn.run_sync(Base.metadata.create_all)
        print("Created all tables with new schema")
    
    print("Tables recreated successfully!")

if __name__ == "__main__":
    asyncio.run(recreate_tables())