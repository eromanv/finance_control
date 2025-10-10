import asyncio

from bot import main
from config import DATABASE_URL

if __name__ == "__main__":
    print(DATABASE_URL)
    asyncio.run(main())
