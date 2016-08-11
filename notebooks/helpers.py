import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../theurg'))

import sqlite3

import config
from entities import Match, HEROES

def load_matches():
    conn = sqlite3.connect(config.get_path('aggregation', 'db-path'))
    conn.row_factory = sqlite3.Row
    matches = [Match.from_row(row) for row in conn.execute('SELECT * FROM match')]
    conn.close()
    return matches

HERO_ID_MAP = {id: idx for idx, id in enumerate(HEROES)}
HERO_COUNT = len(HEROES)
