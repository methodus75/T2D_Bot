"""Discord commands and scheduled recap for the fantasy league."""

import asyncio
import datetime

from discord.ext import commands, tasks

from core.bot import T2DBot
from core.config import NEW_YORK_TZ, RECAP_CHANNEL_ID, RECAP_ROLE_ID
from services.fantasy import generate_recap_text, generate_season_awards


def _completed_week(now: datetime.datetime) -> int:
    season_anchor = datetime.date(2026, 9, 15)
    return ((now.date() - season_anchor).days // 7) + 1


class FantasyCog(commands.Cog):
    def __init__(self, bot: T2DBot):
        self.bot = bot
        self.league = bot.league

    def cog_unload(self):
        self.tuesday_recap.cancel()

    @commands.command(name="standings")
    async def get_standings(self, ctx):
        """Fetches the current league standings."""
        try:
            self.league.refresh()
            standings = self.league.standings()
            
            response = "**🏆 Current League Standings 🏆**\n"
            rank = 1
            for team in standings:
                if team is None:
                    continue
                    
                team_name = getattr(team, 'team_name', f"Team {team.team_id}")
                wins = getattr(team, 'wins', 0)
                losses = getattr(team, 'losses', 0)
                
                response += f"{rank}. **{team_name}** ({wins}-{losses})\n"
                rank += 1
                
            await ctx.send(response)
        except Exception as e:
            await ctx.send("Failed to retrieve standings. Check bot logs.")
            print(f"Error in standings: {e}")

    @commands.command(name="matchups")
    async def get_matchups(self, ctx):
        """Fetches matchups and live scores for the current week."""
        try:
            self.league.refresh()
            current_week = self.league.current_week
            
            try:
                matchups = self.league.box_scores(current_week)
            except Exception:
                matchups = self.league.scoreboard(current_week)
                
            response = f"🏈 **Week {current_week} Matchups & Scores** 🏈\n"
            
            for match in matchups:
                if match is None:
                    continue
                    
                home_team = getattr(match, 'home_team', None)
                if home_team is not None:
                    home_name = getattr(home_team, 'team_name', "Unknown Team")
                    home_score = getattr(match, 'home_score', 0)
                else:
                    home_name = "BYE"
                    home_score = 0
                    
                away_team = getattr(match, 'away_team', None)
                if away_team is not None:
                    away_name = getattr(away_team, 'team_name', "Unknown Team")
                    away_score = getattr(match, 'away_score', 0)
                else:
                    away_name = "BYE"
                    away_score = 0
                
                response += f"⚡ **{home_name}** ({home_score}) vs. **{away_name}** ({away_score})\n"
                    
            await ctx.send(response)
        except Exception as e:
            await ctx.send("Failed to retrieve matchups. Check bot logs.")
            print(f"Error in matchups: {e}")

    @commands.command(name="waivers")
    async def get_waivers(self, ctx):
        """Lists top available free agents in the league."""
        try:
            await ctx.send("🔍 Scanning the waiver wire for top available talent...")
            free_agents = self.league.free_agents(size=10)
            
            if not free_agents:
                await ctx.send("No free agents found or data is currently restricted.")
                return

            response = "🔥 **Top Available Waiver Wire Targets** 🔥\n"
            response += "*Based on total points scored this season*\n\n"
            
            for player in free_agents:
                name = getattr(player, 'name', 'Unknown Player')
                position = getattr(player, 'position', 'N/A')
                pro_team = getattr(player, 'pro_team', 'FA')
                total_points = getattr(player, 'total_points', 0)
                
                response += f"🏃‍♂️ **{name}** ({position} - {pro_team.upper()}) | Total Pts: **{total_points:.1f}**\n"
                
            await ctx.send(response)
        except Exception as e:
            await ctx.send("Failed to retrieve waiver data.")
            print(f"Error in waivers: {e}")

    @commands.command(name="help")
    async def custom_help(self, ctx):
        """Lists available fantasy football commands for league members."""
        response = "🏈 **ESPN Fantasy Football Bot Commands** 🏈\n"
        response += "Use the following commands to check league details:\n\n"
        
        response += "🏆 **`!standings`**\n"
        response += "↳ *Displays the current live ranks, wins, and losses for all teams.*\n\n"
        
        response += "⚡ **`!matchups`**\n"
        response += "↳ *Shows the active matchups and live real-time scores for the current week.*\n\n"
        
        response += "🔍 **`!waivers`**\n"
        response += "↳ *Scans the waiver wire and highlights top available free agents.*\n\n"

        response += "🏅 **`!seasonawards [week]`**\n"
        response += "↳ *Calculates season superlatives through the latest completed week, or a selected completed week.*\n\n"

        response += "🎂 **`!bday setme <MM/DD>`**\n"
        response += "↳ *Opt in to a birthday reminder or update your date.*\n\n"

        response += "🎂 **`!bday removeme`**, **`!bday list`**, **`!bday test`**\n"
        response += "↳ *Remove your entry, view upcoming birthdays, or preview today's reminder.*\n\n"
        
        response += "📅 *Note: Automated league recaps post every Tuesday at 8:00 AM through the Week 14 Championship!*"
        
        await ctx.send(response)

    @commands.command(name="seasonawards")
    async def season_awards_cmd(self, ctx, through_week: int = None):
        """Displays seasonal superlatives through the latest or a selected week."""
        try:
            last_completed_week = min(self.league.current_week - 1, 14)
            if through_week is not None:
                if not 1 <= through_week <= 14:
                    await ctx.send("Choose a week between 1 and 14.")
                    return
                if through_week > last_completed_week:
                    if last_completed_week < 1:
                        await ctx.send("There are no completed weeks to calculate yet.")
                    else:
                        await ctx.send(
                            f"Week {through_week} is not completed yet. "
                            f"ESPN data is available through Week {last_completed_week}."
                        )
                    return

            await ctx.send(
                "⏳ Crunching the seasonal awards across completed weeks. "
                "Give me a few seconds!"
            )
            awards_output = generate_season_awards(
                self.league,
                max_week=through_week if through_week is not None else 14
            )
            await ctx.send(awards_output)
        except Exception as e:
            await ctx.send("Failed to calculate seasonal awards. Check bot logs.")
            print(f"Error in seasonawards: {e}")

    @tasks.loop(seconds=60)
    async def tuesday_recap(self):
        now = datetime.datetime.now(NEW_YORK_TZ)

        # Triggers every Tuesday at 8:00 AM America/New_York, including DST changes.
        if now.weekday() == 1 and now.hour == 8 and now.minute == 0:
            try:
                self.league.refresh()
                recap_week = _completed_week(now)

                # Stop automated recaps once the Week 14 Championship is finished.
                if recap_week > 14:
                    return

                channel_id = RECAP_CHANNEL_ID
                channel = self.bot.get_channel(channel_id)
                if channel:
                    prefix = f"🏈 📢 Attention <@&{RECAP_ROLE_ID}>!\n"
                    response = generate_recap_text(
                        self.league,
                        prefix,
                        target_week=recap_week,
                    )
                    await channel.send(response)
                    await asyncio.sleep(60)
            except Exception as e:
                print(f"Error executing Tuesday Recap task: {e}")

    @commands.command(name="testrecap")
    async def test_recap(self, ctx, week: int = None):
        """Admin test command to preview a week's recap."""
        try:
            self.league.refresh()
            await ctx.send("⚙️ Generating a live preview of the weekly recap...")
            response = generate_recap_text(
                self.league,
                "📊 [TEST PREVIEW]\n",
                target_week=(
                    week
                    if week is not None
                    else _completed_week(datetime.datetime.now(NEW_YORK_TZ))
                ),
            )
            await ctx.send(response)
        except Exception as e:
            await ctx.send("Failed to run test recap. Check bot logs.")
            print(f"Error in testrecap: {e}")

    @commands.command(name="forcerecap")
    @commands.has_permissions(administrator=True)
    async def force_recap(self, ctx):
        """Admin command to post the weekly recap."""
        try:
            self.league.refresh()
        except Exception as e:
            await ctx.send("Failed to refresh league data. Check bot logs.")
            print(f"Error refreshing league for forcerecap: {e}")
            return

        channel_id = RECAP_CHANNEL_ID
        channel = self.bot.get_channel(channel_id)

        if not channel:
            await ctx.send("❌ Error: Could not find the designated league channel.")
            return

        await ctx.send(
            f"⚙️ Forcing weekly recap... It will post to <#{channel_id}> shortly."
        )

        try:
            prefix = f"🏈 📢 [LATE ENTRY] Attention <@&{RECAP_ROLE_ID}>!\n"
            response = generate_recap_text(
                self.league,
                prefix,
                target_week=_completed_week(datetime.datetime.now(NEW_YORK_TZ)),
            )
            await channel.send(response)
        except Exception as e:
            await ctx.send("Failed to execute force recap. Check bot logs.")
            print(f"Error in forcerecap: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Logged in as {self.bot.user.name} (ID: {self.bot.user.id})")
        print("------")

        if not self.tuesday_recap.is_running():
            self.tuesday_recap.start()


async def setup(bot: T2DBot) -> None:
    await bot.add_cog(FantasyCog(bot))
