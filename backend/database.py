from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

client = None
db = None

async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

async def close_mongo_connection():
    global client
    if client:
        client.close()

async def get_database():
    global db
    if db is None:
        await connect_to_mongo()
    return db

# Create indexes for better performance
async def create_indexes():
    db = await get_database()
    
    # User indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    
    # Problem indexes
    await db.problems.create_index("number", unique=True)
    await db.problems.create_index("difficulty")
    await db.problems.create_index("tags")
    
    # Submission indexes
    await db.submissions.create_index([("user_id", 1), ("problem_id", 1)])
    await db.submissions.create_index("submitted_at")
    
    # Contest indexes
    await db.contests.create_index("start_time")
    await db.contests.create_index("status")
    
    # Discussion indexes
    await db.discussions.create_index("created_at")
    await db.discussions.create_index("author_id")