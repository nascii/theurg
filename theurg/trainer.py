import sqlite3
import itertools as it

import numpy as np
import sklearn as sk
import sklearn.linear_model

from entities import Match

# TODO(loyd): move somewhere.
HEROS = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,25,26,27,28,29,30,31,32,33,34,
         35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,
         65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,
         95,96,97,98,99,100,101,102,103,104,105,106,107,109,110,111,112,113]

HERO_ID_MAP = {id: idx for idx, id in enumerate(HEROS)}

class Trainer:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row

        self.samples = None
        self.results = None

    def train(self):
        self.samples, self.results = self._extract_samples()

        logistic = sk.linear_model.LogisticRegressionCV()
        logistic.fit(self.samples, self.results)

        scores = logistic.scores_[True].mean(0)
        C_idx = scores.argmax()

        print(logistic.Cs_[C_idx], scores[C_idx])

    def _extract_samples(self):
        matches = [Match.from_row(row) for row in self.db.execute('SELECT * FROM match')]

        hero_count = len(HEROS)
        synergy_tbl = np.zeros((hero_count, hero_count), np.int32)
        counter_tbl = np.zeros((hero_count, hero_count), np.int32)
        results = np.empty(len(matches), np.bool)

        for idx, match in enumerate(matches):
            heros = [HERO_ID_MAP[pl.hero_id] for pl in match.players]

            if match.radiant_win:
                for i, j in it.combinations(range(0, 5), 2):
                    synergy_tbl[heros[i], heros[j]] += 1

                for i, j in it.combinations_with_replacement(range(0, 5), 2):
                    counter_tbl[heros[i], heros[j+5]] += 1
            else:
                for i, j in it.combinations(range(0, 5), 2):
                    synergy_tbl[heros[i+5], heros[j+5]] += 1

            results[idx] = match.radiant_win

        samples = np.zeros((len(matches), hero_count * 2 + 2), np.int32)

        for match, sample in zip(matches, samples):
            heros = [HERO_ID_MAP[pl.hero_id] for pl in match.players]

            for hero in heros[:5]:
                sample[hero] = 1

            for hero in heros[5:]:
                sample[hero_count + hero] = 1

            for i, j in it.combinations(range(0, 5), 2):
                radiant_synergy = synergy_tbl[heros[i], heros[j]]
                dire_synergy = synergy_tbl[heros[i+5], heros[j+5]]
                sample[hero_count * 2] += radiant_synergy - dire_synergy

            for i, j in it.combinations_with_replacement(range(0, 5), 2):
                radiant_counter = counter_tbl[heros[i], heros[j+5]]
                sample[hero_count * 2 + 1] += radiant_counter

        return samples, results
