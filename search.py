import argparse
import sys
import glob
import os
import os.path
import shutil
import internetarchive as ia
from urllib.parse import unquote
from ytsearch.iametadata import IAItem
from ytsearch.youtube_search import YouTubeSearchManager
from ytsearch.acoustid_search import YouTubeAcoustidManager
from ytsearch.video_ranking import rank_videos
from ytsearch.video_ranking import videos_cull_by_duration
from ytsearch.youtube_download import download_audio_file_ytdl
import audiofp.fingerprint as fp

def ia_download_file(item, filename, dst_dir='.'):
    path = '{}/{}/{}'.format(dst_dir.rstrip('/'),
                             item.item.identifier,
                             filename)
    if not os.path.isfile(path):
        errors = item.item.download(silent=True, files=[filename], destdir=dst_dir)
        if errors:
            print("Error: failed to download file", filename, file=sys.stderr)
            return None
    return path

def search_by_track(yt, track):
    query = '{} {}'.format(track.artist, track.title)
    results = yt.search(query, track.length)
    results = videos_cull_by_duration(results, track.length, duration_range=10)
    # results = videos_cull_by_keyword(results, track.title)
    return results

def search_by_item(yt, item):
    results = {}
    for name in item.tracks:
        results[name] = search_by_track(yt, item.tracks[name])
    return results

def search_by_album(yt, item):
    query = '{} {}'.format(item.artist, item.album)
    results = yt.search(query, item.length)
    results = videos_cull_by_duration(results, item.length, duration_range=120)
    # results = videos_cull_by_keyword(results, [item.album])
    return results

def fingerprint_ia_audio(item, track, length=120, remove_file=False):
    dl_path = ia_download_file(item, track.get_dl_filename(), dst_dir=IA_DL_DIR)
    #TODO: Handle download failure
    fingerprint = fp.generate_fingerprint(dl_path, length=length)
    if remove_file:
        os.remove(dl_path)
    return fingerprint

def fingerprint_yt_audio(video, length=120, remove_file=False):
    dl_path = download_audio_file_ytdl(video['id'], YOUTUBE_DL_DIR)
    #TODO: Handle download failure
    # fingerprint = fp.generate_fingerprint(dl_path, length=video['duration']+1)
    fingerprint = fp.generate_fingerprint(dl_path, length=length)
    if remove_file:
        os.remove(dl_path)
    return fingerprint

def match_full_album(yt, item, clear_cache=False):
    results = {}
    ordered_tracks = sorted(list(item.tracks.values()), key=lambda t: t.ordinal)
    yt_results = search_by_album(yt, item)
    for v in yt_results:
        matches = {}

        #TODO: Handle failure
        reference_fp = fingerprint_yt_audio(v, length=v['duration']+1, 
                                            remove_file=clear_cache)

        for track in ordered_tracks:
            #TODO: Handle failure
            query_fp = fingerprint_ia_audio(item, track, remove_file=clear_cache)
            if not query_fp:
                matches[track.name] = None
            match = fp.match_fingerprints(reference_fp, query_fp, match_threshold=0.2)
            matches[track.name] = match if match else None
        # If at least half of the item's tracks produce a match, consider this a
        # potential match.
        if sum(bool(match) for match in matches.values())/len(item.tracks) >= 0.5:
            f = [t.ordinal for t in ordered_tracks]
            time_offsets = {}
            first_match = matches[ordered_tracks[0].name]
            time_offsets[ordered_tracks[0].name] = first_match.offset if first_match else 0
            ordered = True
            # Iterate through all tracks in album order and ensure that their
            # respective time offsets are strictly increasing. If not, consider
            # this video an invalid match.
            for i in range(1,len(ordered_tracks)):
                match = matches[ordered_tracks[i].name]
                prev_offset = time_offsets[ordered_tracks[i-1].name]
                curr_offset = match.offset if match else prev_offset + ordered_tracks[i-1].length
                if curr_offset < prev_offset:
                    ordered = False
                    break
                time_offsets[ordered_tracks[i].name] = curr_offset

            if not ordered:
                continue

            results['full_album'] = v['id']
            for track in ordered_tracks:
                results[track.name] = '{0}&t={1}'.format(v['id'], 
                                       max(0, int(time_offsets[track.name])))

            break

    return results

def match_tracks(yt, item, tracks, clear_cache=False):
    results = {}
    #TODO: Operate directly on tracks rather than filenames
    for filename in tracks:
        results[filename] = ''
        yt_results = search_by_track(yt, item.tracks[filename])
        if not yt_results:
            continue
        #TODO: Handle failure
        reference_fp = fingerprint_ia_audio(item, item.tracks[filename], remove_file=clear_cache)
        for v in yt_results:
            #TODO: Handle failure
            query_fp = fingerprint_yt_audio(v, remove_file=clear_cache)
            if fp.match_fingerprints(reference_fp, query_fp):
                results[filename] = v['id']
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

    #TODO: Cycle API keys
    yt = YouTubeSearchManager(GOOGLE_API_KEYS[0],
                              max_results=MAX_YOUTUBE_RESULTS,
                              use_cache=False)

    results = {}

    for entry in args.entries:
        if args.search_by_filename:
            iaid, filename_url = entry.split('/', 1)
        else:
            iaid = entry

        item = IAItem(iaid)

        if not item.metadata() or 'error' in item.metadata():
            print("Error: Could not retrieve metadata for item "  + iaid,
                  file=sys.stderr)
            # TODO: Error codes?
            sys.exit(1)

        results[iaid] = {}

        ordered_tracks = sorted(list(item.tracks.values()), key=lambda t: t.ordinal)

        if args.search_full_album:
            results[iaid] = match_full_album(yt, item, clear_cache=args.clear_audio_cache)

        if not results[iaid]:
            #TODO: Operate directly on tracks rather than filenames
            tracks = [unquote(filename_url)] if args.search_by_filename else item.tracks.keys()
            results[iaid] = match_tracks(yt, item, tracks, args.clear_audio_cache)
            
        if args.clear_audio_cache:
            shutil.rmtree('tmp/iaaudio/' + iaid, ignore_errors=True)
    print(results)