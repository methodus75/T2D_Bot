"""Discord client setup."""

import discord
from discord.ext import commands
from espn_api.football import League


class T2DBot(commands.Bot):
    def __init__(self, league: League):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        allowed_mentions = discord.AllowedMentions(
            users=True,
            roles=True,
            everyone=True,
        )
        super().__init__(
            command_prefix="!",
            intents=intents,
            allowed_mentions=allowed_mentions,
        )
        self.league = league
        self.remove_command("help")

    async def setup_hook(self):
        await self.load_extension("cogs.fantasy")
        await self.load_extension("cogs.family")
        await self.load_extension("cogs.general")
