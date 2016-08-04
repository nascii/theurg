import sys
import time
import logging
import sqlite3

import config
from entities import Match, LeagueStats
from fetcher import SteamAPI

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
    DB_PATH = config.get_path('aggregation', 'db-path')
    API_KEY_PATH = config.get_path('aggregation', 'api-key-path')
    RETRY_LIMIT = config.get('aggregation', 'retry-limit')
    RETRY_DELAY = config.get('aggregation', 'retry-delay')
    LEAGUES = config.get('aggregation', 'leagues')

    with open(API_KEY_PATH) as apikey:
        API_KEY = apikey.read().strip()

    def __init__(self):
        self.api = SteamAPI(self.API_KEY, self.RETRY_LIMIT, self.RETRY_DELAY)
        self.db = sqlite3.connect(self.DB_PATH)

        self._prepare_db()

    def complement(self):
        for league_id in self.LEAGUES:
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
        self.db.row_factory = sqlite3.Row

        with self.db:
            self.db.execute('CREATE TABLE IF NOT EXISTS ' + _MATCH_DESCRIPTION)
            self.db.execute('CREATE TABLE IF NOT EXISTS ' + _LEAGUE_STATS_DESCRIPTION)

    def _bootstrap(self, league_id):
        logger.info('Bootstrapping league #%d...', league_id)

        matches, complete = self._download_by_history(league_id)

        if not matches:
            logger.info('There are no available matches for league #%d', league_id)
            return None

        league_stats = LeagueStats(league_id=league_id,
                                   min_match_id=matches[0].match_id,
                                   max_match_id=matches[-1].match_id,
                                   complete=complete)

        self._save_matches_and_league_stats(matches, league_stats)

        return league_stats

    def _download_recent(self, league_stats):
        league_id = league_stats.league_id
        max_saved_match_id = league_stats.max_match_id

        logger.info('Downloading recent matches for league #%d...', league_id)

        matches, complete = self._download_by_history(league_id, max_saved_match_id)

        if not matches:
            logger.info('There are no new non-indexed matches for league #%d', league_id)
            return league_stats

        max_match_id = matches[-1].match_id
        mid_match_id = matches[0].match_id

        while not complete:
            logger.info(
                'Last saved match for league #%d is not reached. Downloading next chunk...',
                league_id)
            chunk, complete = self._download_by_history(league_id, max_saved_match_id, mid_match_id)

            if chunk:
                matches.extend(chunk)
                mid_match_id = chunk[0].match_id

        league_stats = league_stats._replace(max_match_id = max_match_id)
        self._save_matches_and_league_stats(matches, league_stats)

        return league_stats

    def _download_ancient(self, league_stats):
        league_id = league_stats.league_id
        logger.info('Downloading ancient matches for league #%d...', league_id)

        complete = False

        while not complete:
            matches, complete = self._download_by_history(league_id,
                                                          max_match_id=league_stats.min_match_id)

            min_match_id = matches[0].match_id if matches else league_stats.min_match_id
            league_stats = league_stats._replace(min_match_id = min_match_id, complete = complete)

            self._save_matches_and_league_stats(matches, league_stats)

        return league_stats

    def _download_by_history(self, league_id, min_match_id=None, max_match_id=None):
        suffix = ''
        if min_match_id:
            suffix += ' (>#{})'.format(min_match_id)
        if max_match_id:
            suffix += ' (<#{})'.format(max_match_id)

        logger.debug('Looking for matches for league #%d%s...', league_id, suffix)

        history = self.api.match_history(league_id, max_match_id - 1 if max_match_id else None)

        complete = history['results_remaining'] == 0
        if not complete and min_match_id:
            complete = min_match_id in (m['match_id'] for m in history['matches'])

        low, high = min_match_id or 0, max_match_id or sys.maxsize
        filtered = (m for m in history['matches'] if low < m['match_id'] < high)
        relevant = sorted(filtered, key=lambda m: m['match_id'])

        matches = []

        for meta in relevant:
            match_id = meta['match_id']
            logger.debug('Downloading match #%d...', match_id)

            json = self.api.match_details(match_id)
            json['series_id'] = meta.get('series_id')

            match = Match.from_json(json)
            matches.append(match)

        return matches, complete

    def _load_league_stats(self, league_id):
        cursor = self.db.execute('SELECT * FROM league_stats WHERE league_id = ?', (league_id,))
        row = cursor.fetchone()

        return LeagueStats.from_row(row) if row else None

    def _save_matches_and_league_stats(self, matches, league_stats):
        rows = (match.to_row() for match in matches)

        with self.db:
            self.db.execute(_LEAGUE_STATS_INSERT_STMT, league_stats.to_row())
            self.db.executemany(_MATCH_INSERT_STMT, rows)

        logger.info('%d matches for league #%d have been added to the database',
                    len(matches), league_stats.league_id)

if __name__ == '__main__':
    Aggregator().complement()
