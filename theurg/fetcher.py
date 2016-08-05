import time

import requests

class SteamAPIError(Exception):
    pass

class SteamAPI:
    BASE_URL = 'http://api.steampowered.com/IDOTA2Match_570'

    def __init__(self, api_key, retry_limit=0, retry_delay=1):
        self.api_key = api_key
        self.retry_limit = retry_limit
        self.retry_delay = retry_delay

    def match_details(self, match_id):
        return self.request('GetMatchDetails', {
            'match_id': match_id
        })

    def match_history(self, league_id=None, start_at_match_id=None):
        some_big_number = 10000

        return self.request('GetMatchHistory', {
            'league_id': league_id,
            'start_at_match_id': start_at_match_id,
            'min_players': 10,
            'matches_requested': some_big_number
        })

    def request(self, name, params={}):
        retries = self.retry_limit

        while True:
            try:
                return self._request(name, params)
            except requests.HTTPError as error:
                if error.response.status_code == 503 and retries:
                    retries -= 1
                    time.sleep(self.retry_delay)
                else:
                    raise

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

        if 'status' in result and result['status'] not in [1, 200]:
            if 'statusDetail' in result:
                raise SteamAPIError(result['statusDetail'])
            else:
                raise SteamAPIError('Invalid "status": {}'.format(result['status']))

        return result
