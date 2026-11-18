"""ESPN Fantasy Football league client."""

from espn_api.football import League

from core.config import ESPN_S2, LEAGUE_ID, SWID, YEAR


def create_league() -> League:
    return League(
        league_id=LEAGUE_ID,
        year=YEAR,
        espn_s2=ESPN_S2,
        swid=SWID,
    )
