import os
import discord
from discord.ext import commands, tasks
from espn_api.football import League
import datetime
import asyncio
from zoneinfo import ZoneInfo

# ==============================================================================
# 1. INITIALIZE ESPN LEAGUE CONNECTION
# ==============================================================================
NEW_YORK_TZ = ZoneInfo("America/New_York")
LEAGUE_ID = 1031098906
YEAR = 2026          
ESPN_S2 = os.environ["ESPN_S2"]
SWID = os.environ["SWID"]

league = League(league_id=LEAGUE_ID, year=YEAR, espn_s2=ESPN_S2, swid=SWID)

# ==============================================================================
# 2. CONFIGURE DISCORD BOT CLIENT
# ==============================================================================
intents = discord.Intents.default()
intents.message_content = True
allowed_mentions = discord.AllowedMentions(users=True, roles=True, everyone=True)

bot = commands.Bot(command_prefix='!', intents=intents, allowed_mentions=allowed_mentions)
bot.remove_command('help') # Removes default help so our clean custom menu works

# ==============================================================================
# 3. STANDARD LEAGUE COMMANDS (!standings, !matchups, !waivers, !help)
# ==============================================================================
@bot.command(name='standings')
async def get_standings(ctx):
    """Fetches the current league standings."""
    try:
        standings = league.standings()
        
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


@bot.command(name='matchups')
async def get_matchups(ctx):
    """Fetches matchups and live scores for the current week."""
    try:
        current_week = league.current_week
        
        try:
            matchups = league.box_scores(current_week)
        except Exception:
            matchups = league.scoreboard(current_week)
            
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


@bot.command(name='waivers')
async def get_waivers(ctx):
    """Lists top available free agents in the league."""
    try:
        await ctx.send("🔍 Scanning the waiver wire for top available talent...")
        free_agents = league.free_agents(size=10)
        
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


@bot.command(name='help')
async def custom_help(ctx):
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
    
    response += "📅 *Note: Automated league recaps post every Tuesday at 8:00 AM through the Week 14 Championship!*"
    
    await ctx.send(response)

# ==============================================================================
# 4. SEASONAL AWARDS HELPER & COMMAND (!seasonawards)

def generate_season_awards(max_week=14):
    last_completed_week = min(league.current_week - 1, max_week)
    if last_completed_week < 1:
        return "\nNot enough completed weeks to calculate seasonal awards yet!"

    high_score = -1.0
    high_score_info = "N/A"
    low_score = 9999.0
    low_score_info = "N/A"

    closest_margin = 9999.0
    closest_info = "N/A"
    biggest_margin = -1.0
    blowout_info = "N/A"

    team_scores = {}
    bench_points = {}
    injury_weeks = {}
    lineup_unavailable_weeks = []

    for week in range(1, last_completed_week + 1):
        try:
            box_scores = league.box_scores(week)
        except KeyError as error:
            if error.args != ("rosterForCurrentScoringPeriod",):
                raise
            box_scores = league.scoreboard(week)
            lineup_unavailable_weeks.append(week)

        for match in box_scores:
            if match is None:
                continue

            home_team = getattr(match, "home_team", None)
            away_team = getattr(match, "away_team", None)
            home_score = getattr(match, "home_score", 0.0)
            away_score = getattr(match, "away_score", 0.0)

            if (
                home_team
                and away_team
                and not (home_score == 0 and away_score == 0)
            ):
                home_name = getattr(home_team, "team_name", "Unknown")
                away_name = getattr(away_team, "team_name", "Unknown")
                home_totals = team_scores.setdefault(home_name, [0.0, 0.0])
                away_totals = team_scores.setdefault(away_name, [0.0, 0.0])
                home_totals[0] += home_score
                home_totals[1] += away_score
                away_totals[0] += away_score
                away_totals[1] += home_score

                for name, score in (
                    (home_name, home_score),
                    (away_name, away_score),
                ):
                    if score > high_score:
                        high_score = score
                        high_score_info = (
                            f"**{name}** ({score:.2f} pts in Week {week})"
                        )

                    if score < low_score:
                        low_score = score
                        low_score_info = (
                            f"**{name}** ({score:.2f} pts in Week {week})"
                        )

                margin = abs(home_score - away_score)
                winning_score = max(home_score, away_score)
                losing_score = min(home_score, away_score)

                if home_score == away_score:
                    matchup_text = (
                        f"**{home_name}** tied **{away_name}** "
                        f"({home_score:.2f} - {away_score:.2f}, "
                        f"in Week {week})"
                    )
                else:
                    winner = home_name if home_score > away_score else away_name
                    loser = away_name if home_score > away_score else home_name
                    matchup_text = (
                        f"**{winner}** over **{loser}** "
                        f"({winning_score:.2f} - {losing_score:.2f}, "
                        f"margin: {margin:.2f} in Week {week})"
                    )

                if margin < closest_margin:
                    closest_margin = margin
                    closest_info = matchup_text

                if margin > biggest_margin and margin > 0:
                    biggest_margin = margin
                    blowout_info = matchup_text

            lineups = (
                (home_team, getattr(match, "home_lineup", [])),
                (away_team, getattr(match, "away_lineup", [])),
            )

            for team_obj, lineup in lineups:
                if team_obj is None or not lineup:
                    continue

                team_name = getattr(team_obj, "team_name", "Unknown Team")
                bench_points.setdefault(team_name, 0.0)
                injury_weeks.setdefault(team_name, 0)

                for player in lineup:
                    slot = getattr(player, "slot_position", "")
                    points = getattr(player, "points", 0.0)
                    status = getattr(player, "injuryStatus", "ACTIVE")

                    if slot == "BE":
                        bench_points[team_name] += points

                    if status in ("OUT", "INJURY_RESERVE") or slot == "IR":
                        injury_weeks[team_name] += 1

    scoring_champ = (
        max(team_scores, key=lambda name: team_scores[name][0])
        if team_scores else None
    )
    punching_bag = (
        max(team_scores, key=lambda name: team_scores[name][1])
        if team_scores else None
    )

    unforeseen_team = (
        max(bench_points, key=bench_points.get) if bench_points else "N/A"
    )
    hospital_team = (
        max(injury_weeks, key=injury_weeks.get) if injury_weeks else "N/A"
    )

    awards_text = (
        f"\n🏅 **2026 SEASONAL AWARDS "
        f"(Through Week {last_completed_week})** 🏅\n"
    )
    if lineup_unavailable_weeks:
        unavailable_weeks = ", ".join(
            str(week) for week in lineup_unavailable_weeks
        )
        awards_text += (
            f"⚠️ ESPN did not provide historical lineups for Week(s) "
            f"{unavailable_weeks}; bench and injury totals exclude those weeks.\n"
        )

    awards_text += f"👑 **Highest Single-Week Score:** {high_score_info}\n"
    awards_text += f"💩 **Lowest Single-Week Score:** {low_score_info}\n"
    awards_text += f"🎯 **Closest Matchup:** {closest_info}\n"
    awards_text += f"💥 **Blowout of the Year:** {blowout_info}\n"

    if scoring_champ is not None:
        awards_text += (
            f"🔥 **Scoring Champ (Highest PF):** "
            f"{scoring_champ} ({team_scores[scoring_champ][0]:.2f} pts)\n"
        )
    else:
        awards_text += "🔥 **Scoring Champ (Highest PF):** N/A\n"

    if punching_bag is not None:
        awards_text += (
            f"🛡️ **Punching Bag (Highest PA):** "
            f"{punching_bag} ({team_scores[punching_bag][1]:.2f} pts)\n"
        )
    else:
        awards_text += "🛡️ **Punching Bag (Highest PA):** N/A\n"

    if bench_points:
        awards_text += (
            f"🔮 **Unforeseen (Points Left on Bench):** "
            f"{unforeseen_team} ({bench_points[unforeseen_team]:.2f} pts)\n"
        )
    else:
        awards_text += "🔮 **Unforeseen (Points Left on Bench):** N/A\n"

    if injury_weeks:
        awards_text += (
            f"🏥 **Hospital Ward (Injuries / Out / IR):** "
            f"{hospital_team} "
            f"({injury_weeks[hospital_team]} player-weeks)\n"
        )
    else:
        awards_text += "🏥 **Hospital Ward (Injuries / Out / IR):** N/A\n"

    return awards_text


@bot.command(name="seasonawards")
async def season_awards_cmd(ctx, through_week: int = None):
    """Displays seasonal superlatives through the latest or a selected week."""
    try:
        last_completed_week = min(league.current_week - 1, 14)
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
            max_week=through_week if through_week is not None else 14
        )
        await ctx.send(awards_output)
    except Exception as e:
        await ctx.send("Failed to calculate seasonal awards. Check bot logs.")
        print(f"Error in seasonawards: {e}")


# 5. RECAP HELPER, AUTOMATED TUESDAY LOOP & ADMIN COMMANDS

def generate_recap_text(prefix_message="", target_week=None):
    if target_week is None:
        target_week = league.current_week - 1 if league.current_week > 1 else 1

    # Use scoreboard() for future weeks so ESPN doesn't fall back to the current week.
    if target_week > league.current_week:
        matchups = league.scoreboard(target_week)
    else:
        try:
            matchups = league.box_scores(target_week)
        except Exception:
            matchups = league.scoreboard(target_week)

    response = prefix_message

    if target_week == 14:
        response += (
            "🏆🎉 CHAMPIONSHIP FINALE & END OF SEASON RECAP 🎉🏆\n"
            "The 2026 Fantasy Football season has officially concluded! "
            "Here are the final championship results:\n\n"
        )
    elif target_week == 13:
        response += (
            "🔥🏈 PLAYOFF ROUND 1 & CONSOLATION RECAP: WEEK 13 🏈🔥\n"
            "Win or go home! Here is how the opening playoff round "
            "and consolation ladder shook out:\n\n"
        )
    else:
        response += (
            f"📊 🏆 THE TUESDAY RECAP: WEEK {target_week} FINAL SCORES "
            "🏆 📊\n"
            "The matchups are finalized! Here is how the league shook out:\n\n"
        )

    for match in matchups:
        if match is None:
            continue

        home_team = getattr(match, "home_team", None)
        away_team = getattr(match, "away_team", None)

        home_name = (
            getattr(home_team, "team_name", "Unknown Team")
            if home_team
            else "BYE"
        )
        home_score = getattr(match, "home_score", 0)
        away_name = (
            getattr(away_team, "team_name", "Unknown Team")
            if away_team
            else "BYE"
        )
        away_score = getattr(match, "away_score", 0)

        if home_score == 0 and away_score == 0:
            response += (
                f"🗓️ {home_name} vs. {away_name} "
                "(Upcoming / Unplayed)\n"
            )
        elif home_score > away_score:
            response += (
                f"✅ {home_name} ({home_score}) def. "
                f"{away_name} ({away_score})\n"
            )
        elif away_score > home_score:
            response += (
                f"✅ {away_name} ({away_score}) def. "
                f"{home_name} ({home_score})\n"
            )
        else:
            response += (
                f"🤝 {home_name} ({home_score}) TIED "
                f"{away_name} ({away_score})\n"
            )

    if target_week == 14:
        response += generate_season_awards(max_week=14)

        try:
            final_standings = [
                team for team in league.standings() if team is not None
            ]
            if final_standings:
                champion = getattr(
                    final_standings[0],
                    "team_name",
                    "Our League Winner",
                )
                response += (
                    f"\n👑 ALL HAIL YOUR 2026 LEAGUE CHAMPION: "
                    f"{champion.upper()}! 👑\n"
                )
        except Exception as e:
            print(f"Could not fetch final champion: {e}")

        response += (
            "\nThank you everyone for a great season! Automated weekly "
            "recaps are now paused until next year. Use !standings anytime "
            "to view the final leaderboard."
        )
    elif target_week == 12:
        response += (
            "\n🚨 That wraps up the Regular Season! Playoff brackets and "
            "consolation ladders lock in for Week 13! Use !standings to "
            "see who made the cut."
        )
    elif target_week == 13:
        response += (
            "\n🏆 Next stop: THE CHAMPIONSHIP FINALE in Week 14! "
            "Use !matchups to see the title game!"
        )
    else:
        response += "\nUse !standings to see the updated league ranks!"

    return response


@tasks.loop(seconds=60)
async def tuesday_recap():
    now = datetime.datetime.now(NEW_YORK_TZ)

    # Triggers every Tuesday at 8:00 AM America/New_York, including DST changes.
    if now.weekday() == 1 and now.hour == 8 and now.minute == 0:
        recap_week = league.current_week

        # Stop automated recaps once the Week 14 Championship is finished.
        if recap_week > 14:
            return

        channel_id = 1552492353682415707
        channel = bot.get_channel(channel_id)

        if channel:
            try:
                prefix = "🏈 📢 Attention <@&1552492639796858942>!\n"
                response = generate_recap_text(
                    prefix,
                    target_week=recap_week,
                )
                await channel.send(response)
                await asyncio.sleep(60)
            except Exception as e:
                print(f"Error executing Tuesday Recap task: {e}")


@bot.command(name="testrecap")
async def test_recap(ctx, week: int = None):
    """Admin test command to preview a week's recap."""
    try:
        await ctx.send("⚙️ Generating a live preview of the weekly recap...")
        response = generate_recap_text(
            "📊 [TEST PREVIEW]\n",
            target_week=week,
        )
        await ctx.send(response)
    except Exception as e:
        await ctx.send("Failed to run test recap. Check bot logs.")
        print(f"Error in testrecap: {e}")


@bot.command(name="forcerecap")
@commands.has_permissions(administrator=True)
async def force_recap(ctx):
    """Admin command to post the weekly recap."""
    channel_id = 1552492353682415707
    channel = bot.get_channel(channel_id)

    if not channel:
        await ctx.send("❌ Error: Could not find the designated league channel.")
        return

    await ctx.send(
        f"⚙️ Forcing weekly recap... It will post to <#{channel_id}> shortly."
    )

    try:
        prefix = "🏈 📢 [LATE ENTRY] Attention <@&1552492639796858942>!\n"
        response = generate_recap_text(prefix)
        await channel.send(response)
    except Exception as e:
        await ctx.send("Failed to execute force recap. Check bot logs.")
        print(f"Error in forcerecap: {e}")


# 6. BOT STARTUP EVENT & EXECUTION

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("------")

    if not tuesday_recap.is_running():
        tuesday_recap.start()


bot.run(os.environ["DISCORD_TOKEN"])