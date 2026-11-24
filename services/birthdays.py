"""Parsing helpers for birthday entries kept in Discord."""

import datetime
import re
from dataclasses import dataclass
from typing import Optional


_DATE_PATTERN = re.compile(
    r"(?<!\d-)(?<!\d)(\d{1,2})[/-](\d{1,2})"
    r"(?:[/-]\d{2,4})?(?![\d/.-])"
)
_YEAR_PATTERN = re.compile(r"\b(?:18|19|20)\d{2}\b")
_USER_MENTION_PATTERN = re.compile(r"<@!?(\d+)>")


@dataclass(frozen=True)
class BirthdayEntry:
    month: int
    day: int
    name: str
    user_id: Optional[int] = None
    source_line: str = ""


def parse_birthday_entries(messages):
    """Extract valid month/day birthdays and names from message lines."""
    entries = []

    for message in messages:
        content = getattr(message, "content", "")
        mentioned_users = {
            getattr(user, "id", None): user
            for user in getattr(message, "mentions", ())
        }

        for line in content.splitlines():
            date_matches = list(_DATE_PATTERN.finditer(line))
            if not date_matches:
                continue

            mention = _USER_MENTION_PATTERN.search(line)
            if mention:
                user_id = int(mention.group(1))
                user = mentioned_users.get(user_id)
                name = (
                    getattr(user, "display_name", None)
                    or getattr(user, "name", None)
                    or mention.group(0)
                )
            else:
                user_id = None
                name = _DATE_PATTERN.sub(" ", line)
                name = _YEAR_PATTERN.sub(" ", name)
                name = re.sub(r"[\s\-–—,:;|]+", " ", name).strip()

            if not name:
                continue

            for date_match in date_matches:
                month, day = map(int, date_match.groups())
                try:
                    datetime.date(2000, month, day)
                except ValueError:
                    continue

                entries.append(
                    BirthdayEntry(
                        month=month,
                        day=day,
                        name=name,
                        user_id=user_id,
                        source_line=line,
                    )
                )

    return entries
