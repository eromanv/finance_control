import os

# Bot configuration
BOT_TOKEN = os.getenv(
    "BOT_TOKEN", "your_bot_token_here"
)  # Set your bot token in environment variable

# Database configuration
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "finance_db")
DB_USER = os.getenv("DB_USER", "finance_user")
DB_PASS = os.getenv("DB_PASS", "finance_pass")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
