import sys, os
import sqlite3
import pandas as pd
sys.path.append(os.path.join(os.path.dirname(__file__), '../theurg'))

import config
from entities import Match, HEROES

def load_matches():
    conn = sqlite3.connect(config.get_path('aggregation', 'db-path'))
    conn.row_factory = sqlite3.Row
    matches = [Match.from_row(row) for row in conn.execute('SELECT * FROM match')]
    conn.close()
    return matches

def load_matches_df():
    connection = sqlite3.connect(config.get_path('aggregation', 'db-path'))
    query = connection.execute('SELECT * FROM match')
    columns = [column[0] for column in query.description]
    matches = pd.DataFrame.from_records(data=query.fetchall(), columns=columns)
    connection.close()

    return matches

HERO_ID_MAP = {id: idx for idx, id in enumerate(HEROES)}
HERO_COUNT = len(HEROES)
