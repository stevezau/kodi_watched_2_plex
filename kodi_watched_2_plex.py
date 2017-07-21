#!/usr/bin/env python
# import re
import logging
import argparse
import requests
from plexapi.myplex import MyPlexAccount

logging.basicConfig(format='%(message)s', level=logging.INFO)
logging.getLogger('plexapi').setLevel(logging.CRITICAL)
log = logging.getLogger(__name__)

parser = argparse.ArgumentParser()

parser.add_argument("kodi_api_url", type=str, help="Kodi API URL IE: http://192.168.0.190:8080")
parser.add_argument("plex_username", type=str, help="Plex Account Username")
parser.add_argument("plex_password", type=str, help="Plex Account Password")
parser.add_argument("plex_server_name", type=str, help="Plex Server Name IE: media")


def get_json(rsp):
    rsp.raise_for_status()
    data = rsp.json()
    if 'error' in data:
        raise Exception('Kodi API Error: %s', data['error']['message'])
    return data.get('result', {})


def get_movies(api_url):
    payload = {
        'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovies',
        'filter': {'field': 'playcount', 'operator': 'greaterthan', 'value': '0'},
        'params': {'properties': ['playcount', 'imdbnumber', 'lastplayed']},
        'id': 'libMovies'
    }
    data = get_json(requests.post(api_url, json=payload))
    return dict((m['imdbnumber'], m) for m in data.get('movies', []))


def get_tv(api_url):
    tv_shows = {}
    payload_tv = {
        'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows',
        'params': {'properties': ['uniqueid']},
        'id': 'libTVShows'
    }
    data = get_json(requests.post(api_url, json=payload_tv))
    tv_shows_data = dict((m['tvshowid'], m) for m in data.get('tvshows', []))

    payload_ep = {
        'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes',
        'params': {'properties': ['season', 'episode', 'uniqueid', 'playcount', 'tvshowid']},
        'id': 'libMovies'
    }
    data = get_json(requests.post(api_url, json=payload_ep))
    for ep in data.get('episodes', []):
        tvdb_id = tv_shows_data.get(ep['tvshowid'], {}).get('uniqueid', {}).get('unknown')
        if not tvdb_id:
            continue
        if tvdb_id not in tv_shows:
            tv_shows[tvdb_id] = {}
        tv_show = tv_shows[tvdb_id]

        if ep['season'] not in tv_show:
            tv_show[ep['season']] = {}
        tv_show_season = tv_show[ep['season']]
        tv_show_season[ep['episode']] = ep

    return tv_shows


if __name__ == '__main__':
    args = parser.parse_args()
    kodi_api_url = '%s/jsonrpc' % args.kodi_api_url.rstrip('/')

    try:
        account = MyPlexAccount(args.plex_username, args.plex_password)
        plex = account.resource(args.plex_server_name).connect()
    except Exception as e:
        log.critical('Error connecting to Plex %s' % str(e))
        exit(1)

    # TVShows
    try:
        log.info('Getting Kodi Episodes List')
        kodi_episodes = get_tv(kodi_api_url)

        log.info('Getting Plex TVShows')
        plex_episodes = plex.library.section('TV Shows').search(unwatched=True, libtype='episode')
        log.info('Sorting through Plex Episodes to detect watched from Kodi')

        for epsiode in plex_episodes:
            # Only support TheTVDB parsed shows
            tvdb_match = re.search(r'thetvdb://([0-9]+)/', epsiode.guid)
            if tvdb_match:
                kodi_ep = kodi_episodes.get(tvdb_match.group(1), {}).get(epsiode.seasonNumber, {}).get(epsiode.index)
                if kodi_ep:
                    if kodi_ep.get('playcount') > 0 and not epsiode.isWatched:
                        log.info('Marking epsiode %s S%sE%s as watched' %
                                 (epsiode.grandparentTitle, epsiode.seasonNumber, epsiode.index))
                        epsiode.markWatched()
    except Exception as e:
        log.critical('Error processing TVShows %s' % str(e))
        exit(1)

    # Movies
    try:
        log.info('Getting Kodi Movie List')
        kodi_movies = []
        kodi_movies = get_movies(kodi_api_url)

        log.info('Getting Plex Movies')
        plex_movies = plex.library.section('Movies').search(unwatched=True)
        log.info('Sorting through Plex Movies to detect watched from Kodi')

        for movie in plex_movies:
            # Only support IMDB parsed movies
            imdb_match = re.search(r'((?:nm|tt)[\d]{7})', movie.guid)
            if imdb_match:
                imdb_id = imdb_match.group(1)
                kodi_movie = kodi_movies.get(imdb_id)
                if kodi_movie:
                    if kodi_movie.get('playcount') > 0 and not movie.isWatched:
                        log.info('Marking movie %s as watched' % movie.title)
                        movie.markWatched()
    except Exception as e:
        log.critical('Error processing Movies %s' % str(e))
        exit(1)
