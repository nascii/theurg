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

    def match_history(self, league_id=None, hero_id=None, start_at_match_id=None):
        some_big_number = 10000

        return self.request('GetMatchHistory', {
            'league_id': league_id,
            'hero_id': hero_id,
            'start_at_match_id': start_at_match_id,
            'min_players': 10,
            'matches_requested': some_big_number
        })

    def league_listing(self):
        return self.request('GetLeagueListing')['leagues']

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

class DotabuffError(Exception):
    pass

class Dotabuff:
    BASE_URL = 'http://www.dotabuff.com/esports'

    _NAMES = ['Amateur League', 'Professional League', 'Premium League']
    _MARKS = ['<small>{}</small>'.format(name) for name in _NAMES]

    def league_tier(self, league_id):
        txt = self._request('{}/{}/{}'.format(self.BASE_URL, 'leagues', league_id))

        for idx, mark in enumerate(self._MARKS):
            if mark in txt:
                return idx + 1

        raise DotabuffError('Not found league tier')

    def _request(self, url):
        r = requests.get(url, headers={
            # This prevents getting 429. xD
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:48.0) Gecko/20100101 Firefox/48.0'
        })
        r.raise_for_status()

        return r.text
