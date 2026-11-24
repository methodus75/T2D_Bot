"""Family utilities, including opt-in birthday reminders."""

import calendar
import datetime
import random
import re

import discord
from discord.ext import commands, tasks

from core.config import (
    BIRTHDAY_LIST_CHANNEL_ID,
    GENERAL_CHANNEL_ID,
    NEW_YORK_TZ,
)
from services.birthdays import BirthdayEntry, parse_birthday_entries


_DATE_INPUT_PATTERN = re.compile(r"^(\d{1,2})[/-](\d{1,2})$")

# Add more direct .gif URLs here to expand the birthday rotation.
BIRTHDAY_GIFS = [
    "https://media1.tenor.com/m/zID0voNWZeMAAAAC/the-office-its-your-birthday-period-happy-birthday.gif",
    "https://media.tenor.com/oh2jVo_lP48AAAAM/steve-carrell-happy-birthday.gif",
    "https://media.tenor.com/G3H0TWklcv0AAAAM/parks-and-rec-nick-offerman.gif",
    "https://media.tenor.com/TREaEuasPx4AAAAM/happy-birthday-spongebob.gif",
    "https://media.tenor.com/0SOQhf25VLsAAAAM/spongebob-squarepants-nickelodeon.gif",
    "https://media.tenor.com/X185VU8GGAUAAAAM/everybody-dance-now-speaker.gif",
    "https://media.tenor.com/4U0EMvNU1iQAAAAM/cat-cool.gif",
    "https://media.tenor.com/dvWMEVj2W60AAAAM/happy-birthday-goats.gif",
    "https://media.tenor.com/OV_-iVw0048AAAAM/yay-birthday.gif",
    "https://media.tenor.com/34rn7EldmxIAAAAM/ron-swanson.gif",
]


def _parse_birthday_date(value):
    match = _DATE_INPUT_PATTERN.fullmatch(value.strip())
    if not match:
        return None

    month, day = map(int, match.groups())
    try:
        datetime.date(2000, month, day)
    except ValueError:
        return None

    return month, day


def _birthday_occurrence(entry: BirthdayEntry, year: int) -> datetime.date:
    day = entry.day
    if entry.month == 2 and day == 29 and not calendar.isleap(year):
        day = 28
    return datetime.date(year, entry.month, day)


class FamilyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_reminder_date = None

    def cog_unload(self):
        self.birthday_reminder.cancel()

    async def _get_channel(self, channel_id):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            channel = await self.bot.fetch_channel(channel_id)
        return channel

    async def _read_birthday_entries(self):
        channel = await self._get_channel(BIRTHDAY_LIST_CHANNEL_ID)
        messages = [
            message async for message in channel.history(limit=None)
        ]
        return channel, messages, parse_birthday_entries(messages)

    async def _entry_name(self, entry, guild=None):
        if entry.user_id is None:
            return entry.name

        member = guild.get_member(entry.user_id) if guild else None
        if member is None and guild is not None:
            try:
                member = await guild.fetch_member(entry.user_id)
            except (discord.NotFound, discord.HTTPException):
                member = None
        if member is not None:
            return member.display_name
        user = self.bot.get_user(entry.user_id)
        if user is not None:
            display_name = getattr(user, "display_name", None) or user.name
            if display_name:
                return display_name
        if entry.name and not entry.name.startswith("<@"):
            return entry.name
        return f"Member {entry.user_id}"

    @staticmethod
    def _matches_birthday_date(entry, target_date):
        if (entry.month, entry.day) == (target_date.month, target_date.day):
            return True
        return (
            entry.month == 2
            and entry.day == 29
            and target_date.month == 2
            and target_date.day == 28
            and not calendar.isleap(target_date.year)
        )

    async def _remove_user_entries(self, channel, messages, user_id, user_names):
        removed = 0
        bot_user_id = getattr(self.bot.user, "id", None)

        for message in messages:
            entries = [
                entry
                for entry in parse_birthday_entries([message])
                if entry.user_id == user_id
                or (
                    entry.user_id is None
                    and entry.name.casefold() in user_names
                )
            ]
            if not entries:
                continue

            removed_lines = {entry.source_line for entry in entries}
            remaining_lines = [
                line
                for line in message.content.splitlines()
                if line not in removed_lines
            ]
            remaining_content = "\n".join(remaining_lines)

            if not remaining_content.strip():
                await message.delete()
            elif getattr(getattr(message, "author", None), "id", None) == bot_user_id:
                await message.edit(content=remaining_content)
            else:
                if getattr(message, "attachments", ()) or getattr(
                    message, "embeds", ()
                ):
                    raise RuntimeError(
                        "Cannot safely replace a birthday message with attachments or embeds."
                    )
                await channel.send(
                    remaining_content,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                await message.delete()
            removed += 1

        return removed

    @tasks.loop(seconds=60)
    async def birthday_reminder(self):
        now = datetime.datetime.now(NEW_YORK_TZ)
        if (
            now.hour != 8
            or now.minute != 30
            or self._last_reminder_date == now.date()
        ):
            return

        try:
            birthday_channel, _, entries = await self._read_birthday_entries()
            two_week_date = now.date() + datetime.timedelta(days=14)
            todays_birthdays = [
                entry
                for entry in entries
                if self._matches_birthday_date(entry, now.date())
            ]
            upcoming_birthdays = [
                entry
                for entry in entries
                if self._matches_birthday_date(entry, two_week_date)
            ]

            if todays_birthdays or upcoming_birthdays:
                general_channel = await self._get_channel(GENERAL_CHANNEL_ID)
                for entry in todays_birthdays:
                    name = await self._entry_name(entry, birthday_channel.guild)
                    gif_url = random.choice(BIRTHDAY_GIFS)
                    await general_channel.send(
                        f"🎂 Happy Birthday to **{name}**! "
                        f"Wishing you a fantastic day! 🎉\n{gif_url}",
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                for entry in upcoming_birthdays:
                    name = await self._entry_name(entry, birthday_channel.guild)
                    await general_channel.send(
                        f"📅 Heads up! **{name}**'s birthday is coming up in "
                        f"2 weeks ({entry.month:02d}/{entry.day:02d})!",
                        allowed_mentions=discord.AllowedMentions.none(),
                    )

            self._last_reminder_date = now.date()
        except Exception as e:
            print(f"Error executing birthday reminder: {e}")

    @commands.group(name="bday", invoke_without_command=True)
    async def birthday(self, ctx):
        """Shows birthday reminder commands."""
        await ctx.send(
            "Use `!bday setme <MM/DD>`, `!bday removeme`, "
            "`!bday list`, or `!bday test`."
        )

    @birthday.command(name="setme")
    async def set_birthday(self, ctx, date_text: str):
        """Opt in by adding or updating your birthday."""
        parsed_date = _parse_birthday_date(date_text)
        if parsed_date is None:
            await ctx.send("Enter a valid birthday as MM/DD, for example `04/23`.")
            return

        month, day = parsed_date
        user_names = {
            name.strip().casefold()
            for name in (
                getattr(ctx.author, "display_name", ""),
                getattr(ctx.author, "name", ""),
            )
            if name
        }
        try:
            channel, messages, _ = await self._read_birthday_entries()
            await channel.send(
                f"<@{ctx.author.id}> - {month:02d}/{day:02d}",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            try:
                await self._remove_user_entries(
                    channel,
                    messages,
                    ctx.author.id,
                    user_names,
                )
            except Exception as e:
                await ctx.send(
                    "Your birthday was saved, but an older entry could not be "
                    "removed. Please ask an admin to check the birthday channel "
                    "and the bot's message permissions."
                )
                print(f"Error replacing birthday entry: {e}")
                return

            await ctx.send(
                f"Your birthday is saved as **{month:02d}/{day:02d}**."
            )
        except Exception as e:
            await ctx.send("Failed to save your birthday. Check bot logs.")
            print(f"Error saving birthday: {e}")

    @birthday.command(name="removeme")
    async def remove_birthday(self, ctx):
        """Remove your birthday entry."""
        try:
            channel, messages, _ = await self._read_birthday_entries()
            user_names = {
                name.strip().casefold()
                for name in (
                    getattr(ctx.author, "display_name", ""),
                    getattr(ctx.author, "name", ""),
                )
                if name
            }
            removed = await self._remove_user_entries(
                channel,
                messages,
                ctx.author.id,
                user_names,
            )
            if removed:
                await ctx.send("Your birthday entry has been removed.")
            else:
                await ctx.send("No birthday entry was found for you.")
        except Exception as e:
            await ctx.send("Failed to remove your birthday. Check bot logs.")
            print(f"Error removing birthday: {e}")

    @birthday.command(name="list")
    async def list_birthdays(self, ctx):
        """List birthdays in order of their next occurrence."""
        try:
            birthday_channel, _, entries = await self._read_birthday_entries()
            today = datetime.datetime.now(NEW_YORK_TZ).date()
            upcoming = []
            for entry in entries:
                occurrence = _birthday_occurrence(entry, today.year)
                if occurrence < today:
                    occurrence = _birthday_occurrence(entry, today.year + 1)
                upcoming.append((occurrence, entry))
            upcoming.sort(key=lambda item: item[0])

            if not upcoming:
                await ctx.send("No birthdays are listed yet.")
                return

            guild = getattr(ctx, "guild", None) or birthday_channel.guild
            lines = []
            for _, entry in upcoming:
                name = await self._entry_name(entry, guild)
                lines.append(
                    f"• **{name}** — {entry.month:02d}/{entry.day:02d}"
                )
            await ctx.send(
                "🎂 **Upcoming birthdays**\n" + "\n".join(lines),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as e:
            await ctx.send("Failed to read the birthday list. Check bot logs.")
            print(f"Error listing birthdays: {e}")

    @birthday.command(name="test")
    async def test_birthdays(self, ctx):
        """Preview today's birthday reminder in the current channel."""
        try:
            birthday_channel, _, entries = await self._read_birthday_entries()
            now = datetime.datetime.now(NEW_YORK_TZ)
            two_week_date = now.date() + datetime.timedelta(days=14)
            todays_birthdays = [
                entry
                for entry in entries
                if self._matches_birthday_date(entry, now.date())
            ]
            upcoming_birthdays = [
                entry
                for entry in entries
                if self._matches_birthday_date(entry, two_week_date)
            ]
            if not todays_birthdays and not upcoming_birthdays:
                await ctx.send(
                    f"No birthdays found for {now:%B %d} or in 14 days; "
                    "no reminder would be posted.",
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            else:
                guild = getattr(ctx, "guild", None) or birthday_channel.guild
                messages = []
                for entry in todays_birthdays:
                    name = await self._entry_name(entry, guild)
                    messages.append(
                        f"🎂 Happy Birthday to **{name}**! "
                        f"Wishing you a fantastic day! 🎉\n"
                        f"{random.choice(BIRTHDAY_GIFS)}"
                    )
                for entry in upcoming_birthdays:
                    name = await self._entry_name(entry, guild)
                    messages.append(
                        f"📅 Heads up! **{name}**'s birthday is coming up in "
                        f"2 weeks ({entry.month:02d}/{entry.day:02d})!"
                    )
                await ctx.send(
                    "Birthday reminder preview:\n" + "\n".join(messages),
                    allowed_mentions=discord.AllowedMentions.none(),
                )

            sample_gif = random.choice(BIRTHDAY_GIFS)
            sample_preview = (
                "[SAMPLE DRY RUN]\n"
                "🎂 Happy Birthday to **Alex**! "
                f"Wishing you a fantastic day! 🎉\n{sample_gif}\n"
                f"📅 Heads up! **Alex**'s birthday is coming up in 2 weeks "
                f"({two_week_date:%m/%d})!"
            )
            await ctx.send(
                sample_preview,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except Exception as e:
            await ctx.send("Failed to preview birthdays. Check bot logs.")
            print(f"Error testing birthdays: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.birthday_reminder.is_running():
            self.birthday_reminder.start()


async def setup(bot):
    await bot.add_cog(FamilyCog(bot))
