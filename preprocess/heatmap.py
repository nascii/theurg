import numpy as np
import sys
sys.path.append('..')

def get_joint_wins(matches):
    game_stats = get_joint_game_stats(matches)
    joint_wins = np.zeros((113, 113))
    
    for i, heroe_pairs in enumerate(joint_wins):
        for j, value in enumerate(heroe_pairs):
            pair = game_stats[i+1][j+1]
            if pair["games"] == 0:
                joint_wins[i][j] = 0
            else:
                joint_wins[i][j] = pair["wins"] / pair["games"]
    
    return joint_wins

def get_joint_looses(matches):
    game_stats = get_joint_game_stats(matches)
    joint_looses = np.zeros((113, 113))
    
    for i, heroe_pairs in enumerate(joint_looses):
        for j, value in enumerate(heroe_pairs):
            pair = game_stats[i+1][j+1]
            if pair["games"] == 0:
                joint_looses[i][j] = 0
            else:
                joint_looses[i][j] = pair["looses"] / pair["games"]
    
    return joint_looses

# Returns a 2D matrix of game stats: amount of games, wins and looses for each pair of heroes 
def get_joint_game_stats(matches):
    hero_ids = list(range(1, 114))
    game_stats = {id: { _id: { "games": 0, "wins": 0, "looses": 0 } for _id in hero_ids } for id in hero_ids}
    radiant_heroes_columns = ['player_{}_hero_id'.format(n) for n in range(0, 5)]
    dire_heroes_columns = ['player_{}_hero_id'.format(n) for n in range(5, 10)]

    for i, match in matches.iterrows():
        radiant_heroes = set([match[c] for c in radiant_heroes_columns])
        dire_heroes = set([match[c] for c in dire_heroes_columns])
        
        for heroe_1_id in radiant_heroes:
            for heroe_2_id in radiant_heroes: # - set([heroe_1_id]):
                game_stats[heroe_1_id][heroe_2_id]["games"] += 1

                if (match['radiant_win'] == 1):
                    game_stats[heroe_1_id][heroe_2_id]["wins"] += 1
                else:
                    game_stats[heroe_1_id][heroe_2_id]["looses"] += 1
                    
        for heroe_1_id in dire_heroes:
            for heroe_2_id in dire_heroes: # - set([heroe_1_id]):
                game_stats[heroe_1_id][heroe_2_id]["games"] += 1

                if (match['radiant_win'] == 0):
                    game_stats[heroe_1_id][heroe_2_id]["wins"] += 1
                else:
                    game_stats[heroe_1_id][heroe_2_id]["looses"] += 1

    return game_stats
    