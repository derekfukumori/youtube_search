import sys
import shutil
import argparse
import json
import internetarchive as ia
from random import choice
from urllib.parse import unquote
from exceptions import *
from archiving.youtube_archiving import archiver_submit
from metadata.metadata_update import update_metadata
from metadata.util import to_list
import redis
import rq
from ia.metadata import *

import youtube.match as ytmatch
from spotify.match import SpotifyMatcher
from spotipy.oauth2 import SpotifyClientCredentials
import musicbrainz.match as mbmatch

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def insert_matches(main, sub, file_source, item_source):
    for t in sub:
        if t not in main:
            main[t] = {}
        if t == 'full_album':
            main[t][item_source] = sub[t]
        else:
            main[t][file_source] = sub[t]

def get_existing_matches(ia_album):
    m = {t.id:{} for t in ia_album.tracks}
    for src in ['spotify:album', 'youtube', 'mb_releasegroup_id']:
        match = ia_album.get_eid(src)
        if match:
            if not 'full_album' in m:
                m['full_album'] = {}
            m['full_album'][src] = match
    for t in ia_album.tracks:
        for src in ['spotify:track', 'youtube', 'mb_recording_id']:
            match = t.get_eid(src)
            if match:
                m[t.id][src] = match
    return m

def merge_dicts(a, b, path=None):
    "Merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass
            else:
                a[key] = to_list(a[key]) + to_list(b[key])
        else:
            a[key] = b[key]
    return a

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('entries', metavar='ENTRIES', type=str, nargs='+',
                        help='One or more Internet Archive identifiers, or \
                        identifier/filename if --searchbyfilename is specified')
    parser.add_argument('-Y', '--search_youtube', dest='search_youtube',
                        action='store_true', default=False)
    parser.add_argument('-S', '--search_spotify', dest='search_spotify',
                        action='store_true', default=False)
    parser.add_argument('-M', '--search_musicbrainz', dest='search_musicbrainz',
                        action='store_true', default=False)
    parser.add_argument('-c', '--config_file', dest='config_file',
                        metavar='CONFIG_FILE', default=None,
                        help='Path to an internetarchive library config file')
    parser.add_argument('-f', '--searchfullalbum', dest='search_full_album',
                        action='store_true', default=False, 
                        help='Match full-album Youtube videos')
    parser.add_argument('-sf', '--searchbyfilename', dest='search_by_filename',
                        action='store_true', default=False, 
                        help='Search using an input CSV of identifier/file URL pairs')
    parser.add_argument('-cac', '--clear_audio_cache', dest='clear_audio_cache',
                        action='store_true', default=False, 
                        help='Remove downloaded audio files after fingerprint comparison')
    parser.add_argument('-i', '--ignore_matched', dest='ignore_matched',
                        action='store_true', default=False,
                        help='Skip matches (track or full-album) that have the \
                        corresponding external identifiers in their metadata')
    parser.add_argument('-aq' '--album_query_format', dest='album_query_format',
                        metavar='ALBUM_QUERY_FORMAT', default='{artist} {title}')
    parser.add_argument('-tq' '--track_query_format', dest='track_query_format',
                        metavar='TRACK_QUERY_FORMAT', default='{artist} {title}')
    parser.add_argument('-d', '--dry_run', dest='dry_run',
                        action='store_true', default=False,
                        help='Bypass writing metadata to the Archive')
    parser.add_argument('-rq', '--use_redis_queue', dest='use_redis_queue',
                        action='store_true', default=False,
                        help='Upload metadata asynchronously via redis Queue.\
                              Requires a running redis server.')
    parser.add_argument('-v', '--verbose', dest='verbose',
                        action='store_true', default=False)

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger('spotify-match').setLevel(logging.DEBUG)

    config = ia.config.get_config(config_file=args.config_file)

    GOOGLE_API_KEYS = [key.strip() for key in \
                       config.get('ytsearch', {}).get('google_api_keys', '').split(',')]
    
    YOUTUBE_DL_DIR = config.get('ytsearch', {}).get('youtube_dl_dir', 'tmp/ytdl')
    IA_DL_DIR = config.get('ytsearch', {}).get('ia_dl_dir', 'tmp/iadl')
    MAX_YOUTUBE_RESULTS = int(config.get('ytsearch', {}).get('max_youtube_results', 10))
    

    results = {}
    existing_matches = {}

    for entry in args.entries:
        if args.search_by_filename:
            iaid, filename_url = entry.split('/', 1)
            filename = unquote(filename_url)
        else:
            iaid = entry

        try:
            ia_album = IAAlbum(iaid)
        except MetadataException:
            logger.error('{}: Unable to process item metadata'.format(iaid))
            sys.exit(ExitCodes.IAMetadataError.value)
        except MediaTypeException:
            logger.error('{}: Item is not audio'.format(iaid))
            sys.exit(ExitCodes.IAMediatypeError.value)
        except DarkedError:
            logger.error('{}: Item is dark'.format(iaid))
            sys.exit(ExitCodes.DarkedError.value)

        YOUTUBE_DL_SUBDIR = '{}/{}'.format(YOUTUBE_DL_DIR, iaid)

        results[iaid] = {t.id:{} for t in ia_album.tracks}

        # Retrieve existing matches for anayltics purposes
        existing_matches[iaid] = get_existing_matches(ia_album)

        # YouTube
        if args.search_youtube:
            youtube_results = {}
            if args.search_full_album:
                if not args.ignore_matched or (args.ignore_matched and not ia_album.get_eid('youtube')):
                    youtube_results = ytmatch.match_album(ia_album, ia_dir=IA_DL_DIR, 
                                                          yt_dir=YOUTUBE_DL_SUBDIR,
                                                          api_key=GOOGLE_API_KEYS,
                                                          query_fmt=args.album_query_format)
            if not youtube_results:
                if args.search_by_filename:
                    ia_tracks = [ia_album.track_map[filename]]
                elif args.ignore_matched:
                    ia_tracks = [t for t in ia_album.tracks if not t.get_eid('youtube')]
                else:
                    ia_tracks = ia_album.tracks

                youtube_results = ytmatch.match_tracks(ia_tracks, ia_album, ia_dir=IA_DL_DIR,
                                                       yt_dir=YOUTUBE_DL_SUBDIR, 
                                                       api_key=GOOGLE_API_KEYS,
                                                       query_fmt=args.track_query_format)
            insert_matches(results[iaid], youtube_results, 'youtube', 'youtube')

            # Submit results to the YouTube archiver endpoint
            vids = youtube_results['full_album'] if 'full_album' in youtube_results \
                                                 else list(youtube_results.values())
            if vids:
                if args.use_redis_queue:
                    try:
                        #TODO: Connection settings in archive config.
                        q = rq.Queue(connection=redis.Redis())
                        q.enqueue(archiver_submit, vids)
                    except redis.exceptions.ConnectionError():
                        archiver_submit(vids)
                else:
                    archiver_submit(vids)

        # Spotify
        if args.search_spotify:
            SPOTIFY_CREDENTIALS = SpotifyClientCredentials(*config.get('ytsearch', {}).get(
                                    'spotify_credentials', ':').split(':'))

            spotify_results = {}
            spm = SpotifyMatcher(SPOTIFY_CREDENTIALS, ia_dir=IA_DL_DIR)
            if args.search_full_album:
                if not args.ignore_matched or (args.ignore_matched and not ia_album.get_eid('spotify:album')):
                    spotify_results = spm.match_album(ia_album, query_fmt=args.album_query_format)
            if not spotify_results:
                if args.search_by_filename:
                    ia_tracks = [ia_album.track_map[filename]]
                elif args.ignore_matched:
                    ia_tracks = [t for t in ia_album.tracks if not t.get_eid('spotify:track')]
                else:
                    ia_tracks = ia_album.tracks
                spotify_results = spm.match_tracks(ia_tracks, ia_album, query_fmt=args.track_query_format)
            insert_matches(results[iaid], spotify_results, 'spotify', 'spotify')

        if args.search_musicbrainz:
            musicbrainz_results = mbmatch.match_album(ia_album)
            insert_matches(results[iaid], musicbrainz_results, 'mb_recording_id', 'mb_releasegroup_id')

        if args.clear_audio_cache:
            shutil.rmtree('{}/{}'.format(IA_DL_DIR.rstrip(), iaid), ignore_errors=True)
            shutil.rmtree(YOUTUBE_DL_SUBDIR, ignore_errors=True)

    if not args.dry_run:
        if args.use_redis_queue:
            try:
                #TODO: Connection settings in archive config.
                q = rq.Queue(connection=redis.Redis())
                q.enqueue(update_metadata, results)
            except redis.exceptions.ConnectionError():
                logger.warning('No valid redis connection; uploading metadata directly.')
                update_metadata(results)
        else:
            update_metadata(results)

    print(json.dumps(results))
    #print(json.dumps(merge_dicts(existing_matches, results)))