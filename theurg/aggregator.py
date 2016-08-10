import sys
import time
import logging
import sqlite3

from entities import Match, LeagueStats, HEROES
from fetcher import SteamAPI, Dotabuff

_TYPE_MAP = {
    'int': 'INTEGER',
    'bool': 'BOOLEAN',
    'str': 'TEXT'
}

def _collect_schema(table, schema):
    cols = []
    desc = []

    for name, _, conv, attr in schema:
        type = _TYPE_MAP[conv.__name__]
        cols.append(name)
        desc.append('{:21} {} {}'.format(name, type, attr).strip())

    description = table + '(\n'
    description += ',\n'.join('    ' + col for col in desc)
    description += '\n)'

    return description, cols

_MATCH_DESCRIPTION, _MATCH_COLUMNS = _collect_schema('match', Match.schema())

_MATCH_INSERT_STMT = 'INSERT OR IGNORE INTO match({}) VALUES ({})'.format(
    ','.join(_MATCH_COLUMNS), ','.join('?' for _ in _MATCH_COLUMNS))

_LEAGUE_STATS_DESCRIPTION, _LEAGUE_STATS_COLUMNS = _collect_schema('league_stats',
                                                                   LeagueStats.schema())

_LEAGUE_STATS_INSERT_STMT = 'INSERT OR REPLACE INTO league_stats({}) VALUES ({})'.format(
    ','.join(_LEAGUE_STATS_COLUMNS), ','.join('?' for _ in _LEAGUE_STATS_COLUMNS))

logger = logging.getLogger(__name__)

class Aggregator:
    def __init__(self, db_path, api_key, retry_limit=None, retry_delay=None):
        self._steam_api = SteamAPI(api_key, retry_limit, retry_delay)
        self._dotabuff = Dotabuff()
        self._db = sqlite3.connect(db_path)
        self._match_filter = set()

        self._prepare_db()

    def complement(self, leagues):
        for league_id in leagues:
            try:
                self.complement_league(league_id)
            except KeyboardInterrupt:
                raise
            except:
                logger.exception('Exception while complementing league #%d', league_id)

    def complement_league(self, league_id):
        league_stats = self._load_league_stats(league_id)

        if league_stats:
            league_stats = self._download_recent(league_stats)
        else:
            league_stats = self._bootstrap(league_id)

            if not league_stats:
                return

        if not league_stats.complete:
            league_stats = self._download_ancient(league_stats)

    def _prepare_db(self):
        self._db.row_factory = sqlite3.Row

        with self._db:
            self._db.execute('CREATE TABLE IF NOT EXISTS ' + _MATCH_DESCRIPTION)
            self._db.execute('CREATE TABLE IF NOT EXISTS ' + _LEAGUE_STATS_DESCRIPTION)

    def _bootstrap(self, league_id):
        logger.info('Bootstrapping league #%d...', league_id)

        league_tier = self._dotabuff.league_tier(league_id)
        matches, complete, (min_match_id, max_match_id) = self._download_by_history(league_id,
                                                                                    league_tier)
        if not matches:
            logger.info('There are no available matches for league #%d', league_id)

        if not min_match_id:
            return None

        league_stats = LeagueStats(league_id=league_id,
                                   tier=league_tier,
                                   min_match_id=min_match_id,
                                   max_match_id=max_match_id,
                                   complete=complete)

        self._save_matches_and_league_stats(matches, league_stats)

        return league_stats

    def _download_recent(self, league_stats):
        league_id = league_stats.league_id
        league_tier = league_stats.tier
        max_saved_match_id = league_stats.max_match_id

        logger.info('Downloading recent matches for league #%d...', league_id)

        matches, complete, (mid_match_id, max_match_id) = self._download_by_history(
            league_id, league_tier, min_match_id=max_saved_match_id)

        if not matches:
            logger.info('There are no new non-indexed matches for league #%d', league_id)

        if not mid_match_id:
            return league_stats

        while not complete:
            logger.info('Last saved match for league #%d is not reached', league_id)

            chunk, complete, (mid_match_id, _) = self._download_by_history(
                league_id, league_tier, min_match_id=max_saved_match_id, max_match_id=mid_match_id)

            matches.extend(chunk)

        league_stats = league_stats._replace(max_match_id=max_match_id)
        self._save_matches_and_league_stats(matches, league_stats)

        return league_stats

    def _download_ancient(self, league_stats):
        league_id = league_stats.league_id
        logger.info('Downloading ancient matches for league #%d...', league_id)

        max_of_min_id = 0
        min_completed_id = league_stats.min_match_id
        next_heroes = [(hero_id, min_completed_id) for hero_id in HEROES]

        while next_heroes:
            heroes, next_heroes = next_heroes, []
            matches = []

            for hero_id, min_match_id in heroes:
                chunk, complete, (min_match_id, _) = self._download_by_history(
                    league_id, league_stats.tier, hero_id, max_match_id=min_match_id)

                if not complete:
                    next_heroes.append((hero_id, min_match_id))

                    if min_match_id:
                        max_of_min_id = max(min_match_id, max_of_min_id)
                else:
                    if min_match_id:
                        min_completed_id = min(min_match_id, min_completed_id)

                matches.extend(chunk)

            min_match_id = max_of_min_id if next_heroes else min_completed_id
            league_stats = league_stats._replace(min_match_id=min_match_id,
                                                 complete=not next_heroes)
            self._save_matches_and_league_stats(matches, league_stats)

        return league_stats

    def _download_by_history(self, league_id, league_tier, hero_id=None,
                             min_match_id=None, max_match_id=None):
        suffix = ''
        if hero_id:
            suffix += ' and hero #{}'.format(hero_id)
        if min_match_id:
            suffix += ' (>#{})'.format(min_match_id)
        if max_match_id:
            suffix += ' (<#{})'.format(max_match_id)

        logger.debug('Looking for matches for league #%d%s...', league_id, suffix)

        history = self._steam_api.match_history(league_id, hero_id,
                                                max_match_id - 1 if max_match_id else None)

        complete = history['results_remaining'] == 0
        if not complete and min_match_id:
            complete = min_match_id in (m['match_id'] for m in history['matches'])

        if not history['matches']:
            return [], complete, (None, None)

        # Filter the list of matches to download.
        low, high = min_match_id or 0, max_match_id or sys.maxsize
        relevant = [m for m in history['matches'] if low < m['match_id'] < high]

        if not relevant:
            return [], complete, (None, None)

        min_match_id = min(m['match_id'] for m in relevant)
        max_match_id = max(m['match_id'] for m in relevant)

        unknown = (m for m in relevant if m['match_id'] not in self._match_filter)
        ordered = sorted(unknown, key=lambda m: m['match_id'])

        matches = []

        # Download info about the matches.
        for meta in ordered:
            match_id = meta['match_id']
            logger.debug('Downloading match #%d...', match_id)

            json = self._steam_api.match_details(match_id)
            json['series_id'] = meta.get('series_id')
            json['league_tier'] = league_tier

            match = Match.from_json(json)
            matches.append(match)

        # Remember the matches to prevent re-downloading.
        for match in matches:
            self._match_filter.add(match.match_id)

        return matches, complete, (min_match_id, max_match_id)

    def _load_league_stats(self, league_id):
        cursor = self._db.execute('SELECT * FROM league_stats WHERE league_id = ?', (league_id,))
        row = cursor.fetchone()

        return LeagueStats.from_row(row) if row else None

    def _save_matches_and_league_stats(self, matches, league_stats):
        rows = (match.to_row() for match in matches)

        with self._db:
            self._db.execute(_LEAGUE_STATS_INSERT_STMT, league_stats.to_row())
            self._db.executemany(_MATCH_INSERT_STMT, rows)

        logger.info('%d matches for league #%d have been added to the database',
                    len(matches), league_stats.league_id)
