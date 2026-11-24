# Family Discord Bot — Feature Blueprint

This is a loose planning document, not a schedule or commitment. Ideas can be
added, changed, or dropped as the family server grows.

## Purpose

The bot currently serves the ESPN fantasy football league. Longer term, it may
also help the family Discord with useful, low-maintenance activities and
coordination for parents, grandparents, and teens.

The goal is a friendly family utility bot, not a collection of features for
their own sake.

## What exists today

- Python Discord bot using `discord.py`, connected to an ESPN fantasy football
  league.
- General help (`!help`) lists family commands and points league members to
  `!fantasyhelp` (also available as `!espnhelp`) for
  `!standings`, `!matchups`, `!waivers`, and `!seasonawards [week]`.
- Other commands: `!testrecap` and admin-only `!forcerecap`.
- Automated weekly recap scheduled for Tuesday at 8:00 AM America/New_York.
- Opt-in birthday reminders at 8:30 AM America/New_York, using the static
  `#birthdays` channel as the source of truth; members can use `!bday` commands
  to manage and preview entries. Birthday names use server nicknames when the
  member is available in the server.
- Hosted on an Oracle Cloud Ubuntu server as the `t2dbot` systemd service.
- Credentials are provided through a server-side environment file and should
  never be committed to GitHub.

## Family server context

- The server is for family members across generations, including teens.
- There are static text channels for birthday reminders.
- There is a thread channel for birthday and holiday wishlists.
- Future fantasy leagues may use polls for group decisions.
- Most features should be available to members, with role-based access where it
  makes sense. The server owner should retain full administrative control.

## Design principles

- Prefer Discord's built-in events, polls, threads, and permissions when they
  already meet the need.
- Keep routine member features easy to discover and use.
- Restrict configuration, moderation, and other administrative actions to the
  owner or trusted roles.
- Minimize stored family information. For example, avoid storing birth years
  when a month and day would suffice, and only automate personal reminders
  with the family's agreement.
- Keep wishlist contents in Discord rather than copying them to an external
  service or database unless there is a clear reason.
- Avoid unnecessary external services and dependencies to keep hosting and
  maintenance simple.
- Be deliberate with user, role, and everyone mentions to prevent accidental
  pings.
- Add features when they solve a real recurring need; no deadlines are set.

## Possible future ideas

These are exploratory ideas, not a committed roadmap.

- **Holiday reminders:** Automate reminders based on existing Discord content,
  with a privacy-conscious source of dates.
- **Wishlist helper:** Create a consistently formatted wishlist thread or
  provide a simple template, while leaving the wishlist content in Discord.
- **Fantasy league polls:** Help create or manage polls for future league
  decisions; first consider whether Discord's built-in polls are sufficient.
- **Family events and RSVPs:** Use Discord scheduled events or a lightweight
  RSVP flow for gatherings.
- **Trivia and games:** Offer optional, family-friendly activities.
- **Announcements:** Make it easier for authorized family members to post
  important updates without giving the bot broad permission to ping everyone.
- **Household or family coordination:** Consider only if a specific recurring
  task would benefit from automation.

## How to evaluate an idea

Before implementing a feature, capture:

1. What people do manually today, and what is frustrating about it.
2. Who should be able to use it and who should configure it.
3. What the bot needs to store, for how long, and whether Discord already
   stores the information.
4. Whether a native Discord feature solves the problem with less maintenance.
5. Whether the feature needs an external service, additional permissions, or
   ongoing moderation.
6. How to test it and what to do if it fails.

## Possible organization as the bot grows

`bot.py` is the application entry point. Shared bot setup and configuration
live in `core/`, ESPN integration and reusable fantasy calculations live in
`services/`, and the current fantasy commands and Tuesday recap live in
`cogs/fantasy.py`. Keep future distinct features in separate Discord.py
extensions or cogs (for example, family events, polls, and games) so one
feature stays easy to change without entangling the others.

A separate bot may be preferable if a future feature needs substantially
different permissions, data handling, or reliability requirements.

## Idea notes template

Copy this for a new proposal:

### Feature idea

- **Problem or current manual process:**
- **Who would use it:**
- **Who can manage it:**
- **What the bot would do:**
- **Information stored and retention:**
- **Could Discord handle this natively?**
- **External services or extra permissions:**
- **Maintenance and failure considerations:**
- **Status:** Idea / Exploring / Selected / Built / Dropped
