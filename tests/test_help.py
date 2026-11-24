import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("DISCORD_TOKEN", "test-token")
os.environ.setdefault("ESPN_S2", "test-session")
os.environ.setdefault("SWID", "test-swid")

from cogs.fantasy import FantasyCog
from cogs.general import GeneralCog


class FakeContext:
    def __init__(self):
        self.messages = []

    async def send(self, content):
        self.messages.append(content)


class HelpCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_help_lists_family_commands_and_points_to_fantasy_help(self):
        ctx = FakeContext()

        await GeneralCog.custom_help.callback(GeneralCog(), ctx)

        output = ctx.messages[-1]
        self.assertIn("!bday setme <MM/DD>", output)
        self.assertIn("!bday removeme", output)
        self.assertIn("!bday list", output)
        self.assertIn("!fantasyhelp", output)
        self.assertNotIn("!standings", output)

    async def test_fantasyhelp_lists_league_commands_and_recap_schedule(self):
        ctx = FakeContext()
        cog = FantasyCog(SimpleNamespace(league=object()))

        await FantasyCog.fantasy_help.callback(cog, ctx)

        output = ctx.messages[-1]
        for command in (
            "!standings",
            "!matchups",
            "!waivers",
            "!seasonawards [week]",
        ):
            self.assertIn(command, output)
        self.assertIn("Tuesday at 8:00 AM", output)
        self.assertNotIn("!bday", output)
        self.assertEqual(FantasyCog.fantasy_help.aliases, ["espnhelp"])


if __name__ == "__main__":
    unittest.main()
