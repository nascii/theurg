import requests

class SteamAPIError(Exception):
    pass

class SteamAPI:
    BASE_URL = 'http://api.steampowered.com/IDOTA2Match_570'

    def __init__(self, api_key):
        self.api_key = api_key

    def match_details(self, match_id):
        return self._request('GetMatchDetails', {
            'match_id': match_id
        })

    def match_history(self, league_id=None, start_at_match_id=None):
        some_big_number = 10000

        return self._request('GetMatchHistory', {
            'league_id': league_id,
            'start_at_match_id': start_at_match_id,
            'min_players': 10,
            'matches_requested': some_big_number
        })

    def _request(self, name, params={}):
        url = '{}/{}/v1'.format(self.BASE_URL, name)

        params['key'] = self.api_key

        r = requests.get(url, params=params)
        r.raise_for_status()

        data = r.json()

        if 'result' not in data:
            raise SteamAPIError('Missing "result"')

        result = data['result']

        if 'error' in result:
            raise SteamAPIError(result['error'])

        if 'status' in result and result['status'] != 1:
            if 'statusDetail' in result:
                raise SteamAPIError(result['statusDetail'])
            else:
                raise SteamAPIError('Invalid "status": {}'.format(result['status']))

        return result
