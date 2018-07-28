import sys
import os
import os.path
import shutil
import argparse
import json
import internetarchive as ia
from random import choice
from urllib.parse import unquote
from ytsearch.iametadata import *
from ytsearch.youtube_search import YouTubeSearchManager
from ytsearch.video_ranking import videos_cull_by_duration
from ytsearch.youtube_download import download_audio_file_ytdl
from ytsearch.exceptions import *
from archiving.youtube_archiving import archiver_submit
from metadata_update import update_metadata
import audiofp.fingerprint as fp
from audiofp.chromaprint.chromaprint import FingerprintException
import redis
import rq



import youtube.match as ytmatch



logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def merge_results(main, sub, urn):
    for t in sub:
        if t not in main:
            main[t] = {}
        main[t][urn] = sub[t]

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('entries', metavar='ENTRIES', type=str, nargs='+',
                        help='One or more Internet Archive identifiers, or \
                        identifier/filename if --searchbyfilename is specified')
    parser.add_argument('-Y', '--search_youtube', dest='search_youtube',
                        action='store_true', default=False)
    parser.add_argument('-S', '--search_spotify', dest='search_spotify',
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
                        help='Skip tracks that have YouTube identifiers in their metadata')
    parser.add_argument('-q', '--query_format', dest='query_format',
                        metavar='QUERY_FORMAT', default=None)
    parser.add_argument('-d', '--dry_run', dest='dry_run', 
                        action='store_true', default=False,
                        help='Bypass writing metadata to the Archive')
    parser.add_argument('-rq', '--use_redis_queue', dest='use_redis_queue',
                        action='store_true', default=False,
                        help='Upload metadata asynchronously via redis Queue.\
                              Requires a running redis server.')

    args = parser.parse_args()

    config = ia.config.get_config(config_file=args.config_file)

    GOOGLE_API_KEYS = [key.strip() for key in \
                       config.get('ytsearch', {}).get('google_api_keys', '').split(',')]
    YOUTUBE_DL_DIR = config.get('ytsearch', {}).get('youtube_dl_dir', 'tmp/ytdl')
    IA_DL_DIR = config.get('ytsearch', {}).get('ia_dl_dir', 'tmp/iadl')
    MAX_YOUTUBE_RESULTS = int(config.get('ytsearch', {}).get('max_youtube_results', 10))

    yt = YouTubeSearchManager(choice(GOOGLE_API_KEYS),
                              max_results=MAX_YOUTUBE_RESULTS,
                              use_cache=False)

    results = {}

    for entry in args.entries:
        if args.search_by_filename:
            iaid, filename_url = entry.split('/', 1)
            filename = unquote(filename_url)
        else:
            iaid = entry

        try:
            album = IAAlbum(iaid)
        except MetadataException:
            logger.error('{}: Unable to process item metadata'.format(iaid))
            sys.exit(ExitCodes.IAMetadataError.value)
        except MediaTypeException:
            logger.error('{}: Item is not audio'.format(iaid))
            sys.exit(ExitCodes.IAMediatypeError.value)

        YOUTUBE_DL_SUBDIR = '{}/{}'.format(YOUTUBE_DL_DIR, iaid)

        results[iaid] = {}

        # YouTube
        if args.search_youtube:
            youtube_results = {}          
            if args.search_full_album:
                youtube_results = ytmatch.match_album(album, ia_dir=IA_DL_DIR, 
                                                      yt_dir=YOUTUBE_DL_SUBDIR,
                                                      api_key=GOOGLE_API_KEYS)
            if not youtube_results:
                if args.search_by_filename:
                    tracks = [album.track_map[filename]]
                elif args.ignore_matched:
                    tracks = [t for t in album.tracks if not t.get_youtube_match()]
                else:
                    tracks = album.tracks

                youtube_results = ytmatch.match_tracks(tracks, album, ia_dir=IA_DL_DIR,
                                                       yt_dir=YOUTUBE_DL_SUBDIR, 
                                                       api_key=GOOGLE_API_KEYS)
            merge_results(results[iaid], youtube_results, 'youtube')

            # Submit results to the YouTube archiver endpoint
            vids = youtube_results['full_album'] if 'full_album' in youtube_results \
                                                 else list(youtube_results.values())
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
            spotify_results = {}
            if args.search_full_album:
                spotify_results = {}
            if not spotify_results:
                if args.search_by_filename:
                    tracks = [album.track_map[filename]]
                elif args.ignore_matched:
                    pass
                    #TODO: pull spotify matches
                    #tracks = [t for t in album.tracks if not t.get_youtube_match()]
                else:
                    tracks = album.tracks

                spotify_results = {}
                # spotify_results = ytmatch.match_tracks(tracks, album, ia_dir=IA_DL_DIR,
                #                                        yt_dir=YOUTUBE_DL_SUBDIR, 
                #                                        api_key=GOOGLE_API_KEYS)
            merge_results(results[iaid], spotify_results, 'spotify')


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