# T2D Discord Bot — Product & Feature Blueprint

This is a living project brief for understanding the bot and shaping future
work. The current-state section describes implemented behavior; future ideas
are exploratory, not commitments or a delivery schedule.

## Product summary

The bot currently supports an ESPN fantasy football league and a family
Discord server. It provides league information, scheduled recaps, and opt-in
birthday reminders. Future work should address a real recurring need without
making the bot harder to operate or maintain.

## Current implementation

### Runtime and configuration

- Python application built with `discord.py`; `bot.py` starts the client.
- The client uses the `!` command prefix and loads the `fantasy`, `family`, and
  `general` cogs.
- Shared settings live in `core/config.py`. The bot requests Discord's
  `message_content` and `members` intents; the corresponding privileged intents
  must also be enabled in the Discord Developer Portal.
- Discord and ESPN credentials are read from `DISCORD_TOKEN`, `ESPN_S2`, and
  `SWID` environment variables. Never put credential values in this document
  or commit them to GitHub.
- Birthday entries are stored in the configured Discord `#birthdays` channel;
  there is no separate birthday database.

### Family and general commands

- `!help` lists `!bday setme <MM/DD>`, `!bday removeme`, and `!bday list`, and
  points league members to `!fantasyhelp`.
- `!bday setme <MM/DD>` opts a member in or updates their entry.
- `!bday removeme` removes a member's entry; `!bday list` shows upcoming
  birthdays; `!bday test` previews real matches and a sample dry run.
- Entries retain a month and day, not a birth year. User mentions are used for
  member entries; plain-text names are also supported.
- Birthday reminders run at 8:30 AM America/New_York. The bot posts a
  celebration on the birthday and a 14-day heads-up. February 29 birthdays
  are observed on February 28 in non-leap years.
- Birthday messages resolve server members to `display_name` from the guild
  cache or by fetching the member. Day-of celebrations include a randomly
  selected, hot-linked Tenor GIF from the `BIRTHDAY_GIFS` list in
  `cogs/family.py`. If the guild member cannot be resolved, the name falls
  back to a cached user display name or stored name.
- `!bday test` shows matching real entries (or a no-match note) and separately
  sends a `[SAMPLE DRY RUN]` celebration and 14-day heads-up with a GIF.

### ESPN Fantasy Football commands

- `!fantasyhelp` (alias `!espnhelp`) lists the fantasy commands.
- `!standings` shows current league standings.
- `!matchups` shows the current week's matchups and scores.
- `!waivers` lists up to ten available free agents.
- `!seasonawards [week]` calculates seasonal awards through a completed week,
  up to Week 14.
- Automated recaps are scheduled for Tuesday at 8:00 AM America/New_York,
  mention the configured recap role, and stop after the Week 14 championship.
- `!testrecap [week]` previews a recap. Admin-only `!forcerecap` posts a recap
  to the configured channel.
- ESPN configuration currently sets league year 2026. Recap-week calculation
  is anchored to September 15, 2026, and the awards output labels the season
  as 2026. Future seasons will need this year-specific logic reviewed and
  updated.

### Project structure

- `cogs/` contains Discord commands and scheduled tasks.
- `services/` contains ESPN integration, birthday parsing, and reusable
  fantasy calculations.
- `core/` contains bot setup and shared configuration.
- `tests/` contains unit tests for birthday behavior and help output.

## Operating notes to confirm

These are project/deployment assumptions, not facts enforced by the code. Check
them before planning work that depends on them.

- Earlier project notes describe deployment on Oracle Cloud Ubuntu as a
  `t2dbot` systemd service. Confirm the host and deployment process are still
  current before changing or documenting release steps.
- Earlier server notes mention family members across generations, a wishlist
  thread, and static reminder channels. The bot currently manages birthdays
  and fantasy features; it does not manage wishlists.
- Discord channel and role IDs are configured in code. Keep them out of
  feature-specific logic where shared configuration already exists.

## Design principles

- Solve a specific recurring need; prefer a Discord-native feature when it
  meets the need with less custom state or maintenance.
- Keep routine member commands easy to discover. Keep administrative actions
  limited to appropriate permissions.
- Minimize personal data and retention. For birthdays, month and day are
  sufficient; do not add birth years without a clear, agreed need.
- Be deliberate with user, role, and everyone mentions. Avoid unintended
  pings, especially in scheduled messages.
- Make failures understandable and consider how an admin can recover.
- Minimize external services, dependencies, and privileged permissions.

## Ideas to explore

These are prompts for discussion, not a roadmap:

- **Holiday reminders:** What should be the trusted date source, and who can
  add or change dates?
- **Wishlist helper:** Would a thread template or setup command help while
  keeping wishlist contents in Discord?
- **Family events and RSVPs:** Are Discord scheduled events sufficient, or is
  a lightweight bot workflow actually needed?
- **Fantasy league decisions:** Would polls help, or are Discord's built-in
  polls enough?
- **Trivia and games:** What optional, family-friendly activity would people
  actually use?
- **Announcements:** Is there a recurring announcement task that needs
  assistance, and what permissions would it require?

## How to shape the next feature

Before implementation or deeper theory-crafting, establish:

1. The current manual process or problem, and who experiences it.
2. The smallest useful outcome and how members will discover it.
3. Who may use, configure, and administer it.
4. The source of truth, data collected, and retention needs.
5. Whether Discord already provides the necessary feature.
6. Required external services, privileged intents, permissions, and hosting
   changes.
7. Failure behavior, recovery steps, and focused tests.
8. Whether the idea is ready to implement, needs more discussion, or should be
   parked.

## Feature proposal template

### Feature idea

- **Problem / current process:**
- **Who benefits:**
- **Smallest useful behavior:**
- **Who can use or manage it:**
- **Source of truth and data retention:**
- **Could Discord handle it natively?**
- **External services, intents, or permissions:**
- **Failure and recovery plan:**
- **Test and validation plan:**
- **Open questions:**
- **Status:** Idea / Exploring / Selected / Implemented / Parked / Dropped
