import sqlite3
import itertools as it

import numpy as np
from sklearn import preprocessing
from sklearn.linear_model import LogisticRegression

from entities import Match

# TODO(loyd): move somewhere.
HEROS = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,25,26,27,28,29,30,31,32,33,34,
         35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,
         65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,
         95,96,97,98,99,100,101,102,103,104,105,106,107,109,110,111,112,113]

HERO_ID_MAP = {id: idx for idx, id in enumerate(HEROS)}
HERO_COUNT = len(HEROS)

class Predictor:
    def __init__(self, db_path):
        self.db_path = db_path

    def train(self):
        self._load_matches()
        self._calc_synergy_countering()
        self._extract_samples()
        self._fit_model()

    def predict(self, matches):
        samples = self._transform_matches(matches, True)

        for match, sample in zip(matches, samples):
            self._match_to_sample(match, sample)

        return self.logistic.predict(samples)

    def _load_matches(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        self.matches = [Match.from_row(row) for row in conn.execute('SELECT * FROM match')]
        conn.close()

    def _calc_synergy_countering(self):
        synergy_all_tbl = np.zeros((HERO_COUNT, HERO_COUNT), np.int32)
        synergy_win_tbl = np.zeros((HERO_COUNT, HERO_COUNT), np.int32)
        counter_all_tbl = np.zeros((HERO_COUNT, HERO_COUNT), np.int32)
        counter_win_tbl = np.zeros((HERO_COUNT, HERO_COUNT), np.int32)

        for idx, match in enumerate(self.matches):
            heros = [HERO_ID_MAP[pl.hero_id] for pl in match.players]

            for i, j in it.combinations(range(0, 5), 2):
                synergy_all_tbl[heros[i], heros[j]] += 1
                if match.radiant_win:
                    synergy_win_tbl[heros[i], heros[j]] += 1

            for i, j in it.combinations(range(5, 10), 2):
                synergy_all_tbl[heros[i], heros[j]] += 1
                if not match.radiant_win:
                    synergy_win_tbl[heros[i], heros[j]] += 1

            for i, j in it.combinations_with_replacement(range(0, 5), 2):
                counter_all_tbl[heros[i], heros[j+5]] += 1
                if match.radiant_win:
                    counter_win_tbl[heros[i], heros[j+5]] += 1

        with np.errstate(divide='ignore', invalid='ignore'):
            synergy_tbl = synergy_win_tbl / synergy_all_tbl
            synergy_tbl[~np.isfinite(synergy_tbl)] = .5
            counter_tbl = counter_win_tbl / counter_all_tbl
            counter_tbl[~np.isfinite(counter_tbl)] = .5

        self.synergy_tbl = synergy_tbl
        self.counter_tbl = counter_tbl

    def _extract_samples(self):
        self.X, self.y = self._transform_matches(self.matches)

    def _match_to_sample(self, match, sample):
        heros = [HERO_ID_MAP[pl.hero_id] for pl in match.players]

        for hero in heros[:5]:
            sample[hero] = 1

        for hero in heros[5:]:
            sample[HERO_COUNT + hero] = 1

        radiant_synergy = 0
        for i, j in it.combinations(range(0, 5), 2):
            radiant_synergy += self.synergy_tbl[heros[i], heros[j]]

        dire_synergy = 0
        for i, j in it.combinations(range(5, 10), 2):
            dire_synergy += self.synergy_tbl[heros[i], heros[j]]

        sample[HERO_COUNT * 2] = radiant_synergy - dire_synergy

        radiant_counter = 0
        for i, j in it.combinations_with_replacement(range(0, 5), 2):
            radiant_counter += self.counter_tbl[heros[i], heros[j+5]]

        sample[HERO_COUNT * 2 + 1] = radiant_counter

    def _transform_matches(self, matches, live=False):
        X = np.zeros((len(matches), HERO_COUNT * 2 + 2))
        if not live:
            y = np.empty(len(matches), np.bool)

        for idx, match, sample in zip(it.count(), matches, X):
            self._match_to_sample(match, sample)
            if not live:
                y[idx] = match.radiant_win

        X = preprocessing.scale(X)
        return X if live else X, y

    def _fit_model(self):
        logistic = LogisticRegression()
        logistic.fit(self.X, self.y)

        self.logistic = logistic
