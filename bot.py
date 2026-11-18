"""Application entry point for the T2D fantasy football bot."""

import asyncio

from core.bot import T2DBot
from core.config import DISCORD_TOKEN
from services.espn import create_league


async def main() -> None:
    bot = T2DBot(create_league())
    async with bot:
        await bot.load_extension("cogs.fantasy")
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
