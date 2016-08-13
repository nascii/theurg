import pandas as pd
import numpy as np
from collections import Counter

HERO_COLUMNS = ['player_{}_hero_id'.format(n) for n in range(0, 10)]

def get_heroes_dummies(df):
    radiant_heroes_1 = pd.get_dummies(df['player_0_hero_id'], prefix='radiant_has_heroe_id_', prefix_sep='')
    radiant_heroes_2 = pd.get_dummies(df['player_1_hero_id'], prefix='radiant_has_heroe_id_', prefix_sep='')
    radiant_heroes_3 = pd.get_dummies(df['player_2_hero_id'], prefix='radiant_has_heroe_id_', prefix_sep='')
    radiant_heroes_4 = pd.get_dummies(df['player_3_hero_id'], prefix='radiant_has_heroe_id_', prefix_sep='')
    radiant_heroes_5 = pd.get_dummies(df['player_4_hero_id'], prefix='radiant_has_heroe_id_', prefix_sep='')

    dire_heroes_1 = pd.get_dummies(df['player_5_hero_id'], prefix='dire_has_heroe_id_', prefix_sep='')
    dire_heroes_2 = pd.get_dummies(df['player_6_hero_id'], prefix='dire_has_heroe_id_', prefix_sep='')
    dire_heroes_3 = pd.get_dummies(df['player_7_hero_id'], prefix='dire_has_heroe_id_', prefix_sep='')
    dire_heroes_4 = pd.get_dummies(df['player_8_hero_id'], prefix='dire_has_heroe_id_', prefix_sep='')
    dire_heroes_5 = pd.get_dummies(df['player_9_hero_id'], prefix='dire_has_heroe_id_', prefix_sep='')

    ### SHIT STARTS ###
    # If we will not do this shit, we will have NaNs for not intersecting columns when adding dfs
    heroes_names = list(set(get_all_heroes(df)))
    
    if np.nan in heroes_names:
        heroes_names.pop(heroes_names.index(np.nan))

    for name in heroes_names:
        radiant_c = 'radiant_has_heroe_id_' + str(name)
        dire_c = 'dire_has_heroe_id_' + str(name)
        
        if radiant_c not in radiant_heroes_1.columns: radiant_heroes_1[radiant_c] = 0
        if radiant_c not in radiant_heroes_2.columns: radiant_heroes_2[radiant_c] = 0
        if radiant_c not in radiant_heroes_3.columns: radiant_heroes_3[radiant_c] = 0
        if radiant_c not in radiant_heroes_4.columns: radiant_heroes_4[radiant_c] = 0
        if radiant_c not in radiant_heroes_5.columns: radiant_heroes_5[radiant_c] = 0
        
        if dire_c not in dire_heroes_1.columns: dire_heroes_1[dire_c] = 0
        if dire_c not in dire_heroes_2.columns: dire_heroes_2[dire_c] = 0
        if dire_c not in dire_heroes_3.columns: dire_heroes_3[dire_c] = 0
        if dire_c not in dire_heroes_4.columns: dire_heroes_4[dire_c] = 0
        if dire_c not in dire_heroes_5.columns: dire_heroes_5[dire_c] = 0
    ### SHIT ENDS ###

    radiant_heroes = radiant_heroes_1 + radiant_heroes_2 + radiant_heroes_3 + radiant_heroes_4 + radiant_heroes_5
    dire_heroes = dire_heroes_1 + dire_heroes_2 + dire_heroes_3 + dire_heroes_4 + dire_heroes_5

    return (radiant_heroes, dire_heroes)

# Returns 1D array of all heroes, played in all our matches with repeats (to count them)
def get_all_heroes(matches):
    heroes = []

    for c in HERO_COLUMNS:
        heroes = heroes + matches[c].values.tolist()

    return heroes

def get_heroe_counts(df):
    heroes = get_all_heroes(df)
    # Counting our heroes
    counts = Counter(heroes)
    counts = [(k, counts[k]) for k in counts.keys()]
    counts.sort(key=lambda x: x[1], reverse=True)

    return counts
