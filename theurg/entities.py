from collections import namedtuple

def _match_schema():
    yield _column('match_id', attr='PRIMARY KEY')
    yield _column('match_seq_num')
    yield _column('league_id')
    yield _column('series_id', not_null=False)
    yield _column('series_type', not_null=False)
    yield _column('start_time')
    yield _column('cluster')
    yield _column('lobby_type')
    yield _column('game_mode')

    yield _column('radiant_team_id', not_null=False)
    yield _column('radiant_team_complete', not_null=False, conv=bool)
    yield _column('radiant_captain', not_null=False)
    yield _column('radiant_score')

    yield _column('dire_team_id', not_null=False)
    yield _column('dire_team_complete', not_null=False, conv=bool)
    yield _column('dire_captain', not_null=False)
    yield _column('dire_score')

    for n in range(10):
        _pl_column = lambda name, not_null=True: _column('player_{}_{}'.format(n, name),
                                                         ('players', n, name),
                                                         not_null=not_null)
        yield _pl_column('account_id')
        yield _pl_column('hero_id')
        yield _pl_column('level')
        yield _pl_column('gold', not_null=False)

        yield _pl_column('kills')
        yield _pl_column('deaths')
        yield _pl_column('assists')

        yield _pl_column('gold_spent', not_null=False)
        yield _pl_column('last_hits')
        yield _pl_column('denies')
        yield _pl_column('xp_per_min')
        yield _pl_column('gold_per_min')
        yield _pl_column('hero_damage', not_null=False)
        yield _pl_column('hero_healing', not_null=False)
        yield _pl_column('tower_damage', not_null=False)

    for n in range(20):
        yield _column('pick_ban_{}_hero_id'.format(n), ('picks_bans', n), not_null=False)

    yield _column('duration')
    yield _column('first_blood_time')
    yield _column('negative_votes')
    yield _column('positive_votes')

    yield _column('radiant_win', conv=bool)

def _league_stats_schema():
    yield _column('league_id', attr='PRIMARY KEY')
    yield _column('min_match_id')
    yield _column('max_match_id')
    yield _column('complete', conv=bool)

def _column(name, path=None, conv=int, attr='', not_null=True):
    if not_null:
        attr = 'NOT NULL ' + attr

    # TODO(loyd): add `not_null` checking.
    wconv = lambda x: conv(x) if x is not None else None
    wconv.__name__ = conv.__name__

    return name, path or (name,), wconv, attr

_PLAYER_CONVS = [(path[2], conv) for _, path, conv, _ in _match_schema()
                                    if path[:2] == ('players', 0)]
_PLAYER_PROPS = [name for name, _ in _PLAYER_CONVS]

class Player(namedtuple('Player', _PLAYER_PROPS)):
    @staticmethod
    def from_json(json):
        return Player(**{prop: conv(json.get(prop)) for prop, conv in _PLAYER_CONVS})

_MATCH_CONVS = [(path[0], conv) for _, path, conv, _ in _match_schema() if len(path) == 1]
_MATCH_PROPS = [name for name, _ in _MATCH_CONVS]
_MATCH_PROPS.extend(['players', 'picks_bans'])

class Match(namedtuple('Match', _MATCH_PROPS)):
    @staticmethod
    def schema():
        return _match_schema()

    @staticmethod
    def from_json(json):
        dict = {}

        for prop, conv in _MATCH_CONVS:
            dict[prop] = conv(json.get(prop if prop != 'league_id' else 'leagueid')) # Bullshit!

        dict['picks_bans'] = [int(pb['hero_id']) for pb in json.get('picks_bans', [])]
        dict['players'] = [Player.from_json(pl) for pl in json['players']]

        return Match(**dict)

    @staticmethod
    def from_row(row):
        dict = {}
        players = []
        picks_bans = []

        for name, path, conv, _ in _match_schema():
            value = conv(row[name])

            if path[0] == 'players':
                if len(players) == path[1]:
                    players.append({})

                players[path[1]][path[2]] = value
            elif path[0] == 'picks_bans':
                picks_bans.append(value)
            else:
                dict[path[0]] = value

        dict['picks_bans'] = picks_bans
        dict['players'] = [Player.from_json(pl) for pl in players]

        return Match(**dict)

    def to_row(self):
        return [_get(self, path) for _, path, _, _ in _match_schema()]

_LEAGUE_STATS_PROPS = [path[0] for _, path, _, _ in _league_stats_schema()]

class LeagueStats(namedtuple('LeagueStats', _LEAGUE_STATS_PROPS)):
    @staticmethod
    def schema():
        return _league_stats_schema()

    @staticmethod
    def from_row(row):
        return LeagueStats(
            **{path[0]: conv(row[name]) for name, path, conv, _ in _league_stats_schema()})

    def to_row(self):
        return [_get(self, path) for _, path, _, _ in _league_stats_schema()]

def _get(obj, path):
    try:
        value = obj

        for part in path:
            is_idx = isinstance(part, int)
            value = value[part] if is_idx else getattr(value, part)

        return value
    except:
        return None

HEROES = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,25,26,27,28,29,30,31,32,33,34,
          35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,
          65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,
          95,96,97,98,99,100,101,102,103,104,105,106,107,109,110,111,112,113]
