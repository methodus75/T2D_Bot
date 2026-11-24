"""General-purpose commands for the family Discord server."""

from discord.ext import commands


class GeneralCog(commands.Cog):
    @commands.command(name="help")
    async def custom_help(self, ctx):
        """Lists general and family commands."""
        response = "👋 **Bot Commands** 👋\n"
        response += "Family commands:\n\n"
        response += "🎂 **`!bday setme <MM/DD>`**\n"
        response += "↳ *Opt in to a birthday reminder or update your date.*\n\n"
        response += "🎂 **`!bday removeme`**\n"
        response += "↳ *Remove your birthday entry.*\n\n"
        response += "🎂 **`!bday list`**\n"
        response += "↳ *View upcoming birthdays.*\n\n"
        response += "League members: use `!fantasyhelp` for ESPN Fantasy Football commands."
        await ctx.send(response)


async def setup(bot):
    await bot.add_cog(GeneralCog())
