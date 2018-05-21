import argparse
import sys
import glob
import os
import os.path
import shutil
import internetarchive as ia
from random import choice
from urllib.parse import unquote
from ytsearch.iametadata import *
from ytsearch.youtube_search import YouTubeSearchManager
from ytsearch.acoustid_search import YouTubeAcoustidManager
from ytsearch.video_ranking import rank_videos
from ytsearch.video_ranking import videos_cull_by_duration
from ytsearch.youtube_download import download_audio_file_ytdl
import audiofp.fingerprint as fp
from audiofp.chromaprint.chromaprint import FingerprintException

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def search_by_track(yt, track):
    """ Query YouTube for an individual track
    """
    query = '{} {}'.format(track.artist, track.title)
    results = yt.search(query, track.duration)
    results = videos_cull_by_duration(results, track.duration, duration_range=10)
    # results = videos_cull_by_keyword(results, track.title)
    return results

def search_by_album(yt, album):
    """ Query YouTube for full-album videos
    """
    query = '{} {}'.format(album.artist, album.title)
    results = yt.search(query, album.duration)
    results = videos_cull_by_duration(results, album.duration, duration_range=120)
    # results = videos_cull_by_keyword(results, [album.title])
    return results

def fingerprint_ia_audio(track, length=120, remove_file=False):
    dl_path = track.download(destdir=IA_DL_DIR)
    #TODO: Handle download failure
    fingerprint = fp.generate_fingerprint(dl_path, length=length)
    if remove_file:
        os.remove(dl_path)
    return fingerprint

def fingerprint_yt_audio(video, length=120, remove_file=False):
    dl_path = download_audio_file_ytdl(video['id'], YOUTUBE_DL_DIR)
    #TODO: Handle download failure
    fingerprint = fp.generate_fingerprint(dl_path, length=length)
    if remove_file:
        os.remove(dl_path)
    return fingerprint

def match_full_album(yt, album, clear_cache=False):
    results = {}
    yt_results = search_by_album(yt, album)
    for v in yt_results:
        matches = {}

        try:
            reference_fp = fingerprint_yt_audio(v, length=v['duration']+1, 
                                                remove_file=clear_cache)
        except FingerprintException:
            logger.warning('{}: Unable to fingerprint YouTube video "{}"'.format(album.identifier, v['id']))
            continue

        for track in album.tracks:
            matches[track.name] = None
            try:
                query_fp = fingerprint_ia_audio(track, remove_file=clear_cache)
            except FingerprintException:
                logger.warning('{}: Unable to fingerprint file "{}"'.format(album.identifier, track.name))
                continue
            
            match = fp.match_fingerprints(reference_fp, query_fp, match_threshold=0.2)
            matches[track.name] = match if match else None
        # If at least half of the album's tracks produce a match, consider this 
        # video a potential match.
        if sum(bool(match) for match in matches.values())/len(album.tracks) >= 0.5:
            f = [t.ordinal for t in album.tracks]
            time_offsets = {}
            first_match = matches[album.tracks[0].name]
            time_offsets[album.tracks[0].name] = first_match.offset if first_match else 0
            ordered = True
            # Iterate through all tracks in album-order and ensure that their
            # respective time offsets are strictly increasing. If not, consider
            # this video an invalid match.
            for i in range(1,len(album.tracks)):
                match = matches[album.tracks[i].name]
                prev_offset = time_offsets[album.tracks[i-1].name]
                curr_offset = match.offset if match else prev_offset + album.tracks[i-1].duration
                if curr_offset < prev_offset:
                    ordered = False
                    break
                time_offsets[album.tracks[i].name] = curr_offset

            if not ordered:
                continue

            results['full_album'] = v['id']
            for track in album.tracks:
                results[track.name] = '{0}&t={1}'.format(v['id'], 
                                       max(0, int(time_offsets[track.name])))

            break

    return results

def match_tracks(yt, album, tracks, clear_cache=False):
    results = {}
    for track in tracks:
        results[track.name] = ''
        yt_results = search_by_track(yt, track)
        if not yt_results:
            continue
        try:
            reference_fp = fingerprint_ia_audio(track, remove_file=clear_cache)
        except FingerprintException:
            logger.warning('{}: Unable to fingerprint file "{}"'.format(album.identifier, track.name))
            continue
        for v in yt_results:
            try:
                query_fp = fingerprint_yt_audio(v, remove_file=clear_cache)
            except FingerprintException:
                logger.warning('{}: Unable to fingerprint YouTube video "{}"'.format(album.identifier, v['id']))
                continue
            if fp.match_fingerprints(reference_fp, query_fp):
                results[track.name] = v['id']
                break
    return results



if __name__=='__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('entries', metavar='ENTRIES', type=str, nargs='+',
                        help='One or more Internet Archive identifiers, or \
                        identifier/filename if --searchbyfilename is specified')
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
            #TODO Logging
            #TODO Retries
            sys.exit(1)
        except MediaTypeException:
            #TODO: Logging
            sys.exit(1)

        results[iaid] = {}

        if args.search_full_album:
            results[iaid] = match_full_album(yt, album, clear_cache=args.clear_audio_cache)

        if not results[iaid]:
            tracks = [album.track_map[filename]] if args.search_by_filename else album.tracks
            results[iaid] = match_tracks(yt, album, tracks, args.clear_audio_cache)
            
        if args.clear_audio_cache:
            shutil.rmtree('{}/{}'.format(IA_DL_DIR.rstrip(), iaid), ignore_errors=True)
    print(results)