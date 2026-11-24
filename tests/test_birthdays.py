import datetime
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("ESPN_S2", "test-session")
os.environ.setdefault("SWID", "test-swid")

import discord

import cogs.family as family_module
from cogs.family import FamilyCog, _birthday_occurrence
from services.birthdays import BirthdayEntry, parse_birthday_entries


class BirthdayParserTests(unittest.TestCase):
    def test_parses_month_day_and_ignores_years_and_invalid_lines(self):
        messages = [
            SimpleNamespace(
                content=(
                    "<@123> - 04/23\n"
                    "Bob Smith - 2-29-1988\n"
                    "Invalid - 02/30/1990\n"
                    "ISO date - 1990-03-04\n"
                    "No date"
                ),
                mentions=[SimpleNamespace(id=123, display_name="Alice")],
            )
        ]

        entries = parse_birthday_entries(messages)

        self.assertEqual(
            [(entry.month, entry.day, entry.name) for entry in entries],
            [(4, 23, "Alice"), (2, 29, "Bob Smith")],
        )


class BirthdayDateTests(unittest.TestCase):
    def test_february_29_occurrence_and_observed_day(self):
        leap_birthday = BirthdayEntry(2, 29, "Leap Birthday", user_id=123)

        self.assertEqual(
            _birthday_occurrence(leap_birthday, 2025),
            datetime.date(2025, 2, 28),
        )
        self.assertEqual(
            _birthday_occurrence(leap_birthday, 2028),
            datetime.date(2028, 2, 29),
        )
        self.assertTrue(
            FamilyCog._matches_birthday_date(
                leap_birthday,
                datetime.date(2025, 2, 28),
            )
        )
        self.assertFalse(
            FamilyCog._matches_birthday_date(
                leap_birthday,
                datetime.date(2028, 2, 28),
            )
        )


class FakeMessage:
    def __init__(self, message_id, content, author_id=99, mentions=()):
        self.id = message_id
        self.content = content
        self.author = SimpleNamespace(id=author_id)
        self.mentions = list(mentions)
        self.deleted = False

    async def delete(self):
        self.deleted = True

    async def edit(self, content):
        self.content = content


class FakeChannel:
    def __init__(self, channel_id, messages=()):
        self.id = channel_id
        self.messages = list(messages)
        self.sent = []
        self.members = {}
        self.guild = SimpleNamespace(get_member=self.members.get)
        self.history_limit = None

    async def history(self, limit=None):
        self.history_limit = limit
        for message in list(self.messages):
            yield message

    async def send(self, content, **kwargs):
        self.sent.append((content, kwargs))
        message = FakeMessage(100 + len(self.sent), content)
        self.messages.append(message)
        return message


class FakeBot:
    def __init__(self, channels):
        self.channels = channels
        self.user = SimpleNamespace(id=99)

    def get_channel(self, channel_id):
        return self.channels.get(channel_id)

    async def fetch_channel(self, channel_id):
        return self.channels[channel_id]

    def get_user(self, user_id):
        return SimpleNamespace(
            name=f"User{user_id}",
            display_name=f"User{user_id}",
        )


class FakeContext:
    def __init__(self, user_id=42, name="Alice"):
        self.author = SimpleNamespace(
            id=user_id,
            name=name,
            display_name=name,
        )
        self.messages = []

    async def send(self, content, **kwargs):
        self.messages.append((content, kwargs))


class FrozenDateTime(datetime.datetime):
    current = (2025, 2, 28, 8, 30)

    @classmethod
    def now(cls, tz=None):
        return cls(*cls.current, tzinfo=tz)


class BirthdayCogTests(unittest.IsolatedAsyncioTestCase):
    async def test_setme_replaces_plain_name_without_removing_other_entries(self):
        birthday_channel_id = family_module.BIRTHDAY_LIST_CHANNEL_ID
        general_channel_id = family_module.GENERAL_CHANNEL_ID
        old_message = FakeMessage(
            1,
            "Alice - 03/04\nBob - 04/05",
        )
        birthday_channel = FakeChannel(birthday_channel_id, [old_message])
        bot = FakeBot(
            {
                birthday_channel_id: birthday_channel,
                general_channel_id: FakeChannel(general_channel_id),
            }
        )
        cog = FamilyCog(bot)
        ctx = FakeContext()

        await FamilyCog.set_birthday.callback(cog, ctx, "04/23")

        self.assertIsNone(birthday_channel.history_limit)
        self.assertEqual(
            birthday_channel.sent[0][0],
            "<@42> - 04/23",
        )
        self.assertEqual(old_message.content, "Bob - 04/05")
        self.assertIn("saved as **04/23**", ctx.messages[-1][0])

    async def test_setme_preserves_other_lines_in_a_shared_user_message(self):
        birthday_channel_id = family_module.BIRTHDAY_LIST_CHANNEL_ID
        general_channel_id = family_module.GENERAL_CHANNEL_ID
        old_message = FakeMessage(
            1,
            "Alice - 03/04\nBob - 04/05",
            author_id=77,
        )
        birthday_channel = FakeChannel(birthday_channel_id, [old_message])
        bot = FakeBot(
            {
                birthday_channel_id: birthday_channel,
                general_channel_id: FakeChannel(general_channel_id),
            }
        )
        cog = FamilyCog(bot)
        ctx = FakeContext()

        await FamilyCog.set_birthday.callback(cog, ctx, "04/23")

        self.assertTrue(old_message.deleted)
        self.assertIn(
            "Bob - 04/05",
            [content for content, _ in birthday_channel.sent],
        )
        self.assertIn(
            "<@42> - 04/23",
            [content for content, _ in birthday_channel.sent],
        )

    async def test_list_sorts_by_next_occurrence(self):
        FrozenDateTime.current = (2025, 2, 28, 8, 30)
        birthday_channel_id = family_module.BIRTHDAY_LIST_CHANNEL_ID
        general_channel_id = family_module.GENERAL_CHANNEL_ID
        birthday_channel = FakeChannel(
            birthday_channel_id,
            [
                FakeMessage(1, "Alice - 01/01"),
                FakeMessage(2, "Bob - 12/01"),
                FakeMessage(3, "Carol - 02/29"),
            ],
        )
        cog = FamilyCog(
            FakeBot(
                {
                    birthday_channel_id: birthday_channel,
                    general_channel_id: FakeChannel(general_channel_id),
                }
            )
        )
        ctx = FakeContext()

        with patch.object(family_module.datetime, "datetime", FrozenDateTime):
            await FamilyCog.list_birthdays.callback(cog, ctx)

        output = ctx.messages[-1][0]
        self.assertLess(output.index("Carol"), output.index("Bob"))
        self.assertLess(output.index("Bob"), output.index("Alice"))

    async def test_february_29_reminder_is_non_pinging(self):
        FrozenDateTime.current = (2025, 2, 28, 8, 30)
        birthday_channel_id = family_module.BIRTHDAY_LIST_CHANNEL_ID
        general_channel_id = family_module.GENERAL_CHANNEL_ID
        mentioned_user = SimpleNamespace(id=42, display_name="Birthday Person")
        birthday_channel = FakeChannel(
            birthday_channel_id,
            [
                FakeMessage(
                    1,
                    "<@42> - 02/29",
                    mentions=[mentioned_user],
                ),
                FakeMessage(2, "Alice - 03/14"),
            ],
        )
        birthday_channel.members[42] = SimpleNamespace(
            display_name="Server Nickname",
        )
        general_channel = FakeChannel(general_channel_id)
        cog = FamilyCog(
            FakeBot(
                {
                    birthday_channel_id: birthday_channel,
                    general_channel_id: general_channel,
                }
            )
        )

        with patch.object(family_module.datetime, "datetime", FrozenDateTime):
            await FamilyCog.birthday_reminder.coro(cog)

        self.assertEqual(len(general_channel.sent), 2)
        self.assertIn(
            "**Server Nickname**",
            general_channel.sent[0][0],
        )
        self.assertIn("Alice", general_channel.sent[1][0])
        self.assertIn("03/14", general_channel.sent[1][0])
        self.assertEqual(
            repr(general_channel.sent[0][1]["allowed_mentions"]),
            repr(discord.AllowedMentions.none()),
        )

        ctx = FakeContext()
        with patch.object(family_module.datetime, "datetime", FrozenDateTime):
            await FamilyCog.test_birthdays.callback(cog, ctx)
        self.assertIn("Server Nickname", ctx.messages[-1][0])
        self.assertIn("Heads up", ctx.messages[-1][0])
        self.assertIn("03/14", ctx.messages[-1][0])

    async def test_list_uses_server_nickname_for_mentioned_members(self):
        FrozenDateTime.current = (2025, 2, 28, 8, 30)
        birthday_channel_id = family_module.BIRTHDAY_LIST_CHANNEL_ID
        general_channel_id = family_module.GENERAL_CHANNEL_ID
        birthday_channel = FakeChannel(
            birthday_channel_id,
            [
                FakeMessage(
                    1,
                    "<@42> - 12/01",
                    mentions=[SimpleNamespace(id=42, display_name="Global Name")],
                ),
            ],
        )
        birthday_channel.members[42] = SimpleNamespace(
            display_name="Server Nickname",
        )
        cog = FamilyCog(
            FakeBot(
                {
                    birthday_channel_id: birthday_channel,
                    general_channel_id: FakeChannel(general_channel_id),
                }
            )
        )
        ctx = FakeContext()

        with patch.object(family_module.datetime, "datetime", FrozenDateTime):
            await FamilyCog.list_birthdays.callback(cog, ctx)

        self.assertIn("Server Nickname", ctx.messages[-1][0])
        self.assertNotIn("Global Name", ctx.messages[-1][0])

    async def test_missing_guild_member_falls_back_to_user_display_name(self):
        cog = FamilyCog(FakeBot({}))
        entry = BirthdayEntry(12, 1, "Old Mention Name", user_id=42)

        self.assertEqual(cog._entry_name(entry), "User42")

    async def test_two_week_heads_up_observes_february_29(self):
        FrozenDateTime.current = (2025, 2, 14, 8, 30)
        birthday_channel_id = family_module.BIRTHDAY_LIST_CHANNEL_ID
        general_channel_id = family_module.GENERAL_CHANNEL_ID
        birthday_channel = FakeChannel(
            birthday_channel_id,
            [FakeMessage(1, "Leap Birthday - 02/29")],
        )
        general_channel = FakeChannel(general_channel_id)
        cog = FamilyCog(
            FakeBot(
                {
                    birthday_channel_id: birthday_channel,
                    general_channel_id: general_channel,
                }
            )
        )

        with patch.object(family_module.datetime, "datetime", FrozenDateTime):
            await FamilyCog.birthday_reminder.coro(cog)

        self.assertEqual(len(general_channel.sent), 1)
        self.assertIn("Heads up", general_channel.sent[0][0])
        self.assertIn("02/29", general_channel.sent[0][0])


if __name__ == "__main__":
    unittest.main()
