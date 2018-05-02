import argparse
import sys
import glob
import os.path
import shutil
from urllib.parse import unquote
from ytsearch.iametadata import IAItem
from ytsearch.youtube_search import YouTubeSearchManager
from ytsearch.acoustid_search import YouTubeAcoustidManager
from ytsearch.video_ranking import rank_videos
from ytsearch.video_ranking import videos_cull_by_duration
from ytsearch.youtube_download import download_audio_file_ytdl
import audiofp.fingerprint as fp
from defaults import *

def ia_download_file(item, filename, dst_dir='tmp/iaaudio'):
    path = dst_dir.rstrip('/') + '/' + item.item.identifier + '/' + filename
    cached_files = glob.glob(path)
    if not cached_files:
        errors = item.item.download(silent=True, files=[filename], destdir=dst_dir)
        if errors:
            print("Error: failed to download file", filename, file=sys.stderr)
            return ''
    return path

def search_by_track(yt, track):
    if not track.acoustid:
        return ''
    # TODO: Refine queries.
    query = track.artist + " " + track.title
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
    query = item.artist + " " + item.album
    results = yt.search(query, item.length)
    results = videos_cull_by_duration(results, item.length, duration_range=120)
    # results = videos_cull_by_keyword(results, [item.album])
    return results

def match_full_album(yt, item, clear_cache=False):
    results = {}
    ordered_tracks = sorted(list(item.tracks.values()), key=lambda t: t.track_ordering)
    yt_results = search_by_album(yt, item)
    for v in yt_results:
        matches = {}
        yt_dl_path = download_audio_file_ytdl(v['id'], AUDIO_CACHE_DIR, VIDEO_CACHE_DIR)
        reference_fp = fp.generate_fingerprint(yt_dl_path, length=v['duration']+1) 
        if clear_cache:
            os.remove(yt_dl_path)

        for track in ordered_tracks:
            dl_path = ia_download_file(item, track.name)
            if not dl_path:
                matches[track.name] = None
                continue
            query_fp = fp.generate_fingerprint(dl_path)
            match = fp.match_fingerprints(reference_fp, query_fp, match_threshold=0.2)
            matches[track.name] = match if match else None
        # If at least half of the item's tracks produce a match, consider this a
        # successful full-album match.
        if sum(bool(match) for match in matches.values())/len(item.tracks) >= 0.5:
            time_offsets = {}
            first_match = matches[ordered_tracks[0].name]
            time_offsets[ordered_tracks[0].name] = first_match.offset if first_match else 0
            ordered = True
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
                results[track.name] = '{0}&t={1}'.format(v['id'], max(0, int(time_offsets[track.name])))

            break
    # finally:
        #os.remove(yt_dl_path)

    return results



if __name__=='__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('entries', metavar='ENTRIES', type=str, nargs='+',
        help='Something')
    parser.add_argument('-f', '--searchfullalbum', dest='search_full_album',
            action='store_true', default=False, help='Match full-album Youtube videos')
    parser.add_argument('-sf', '--searchbyfilename', dest='search_by_filename',
            action='store_true', default=False, help='Search using an input \
            CSV of identifier/file URL pairs')
    parser.add_argument('-gk', '--google_api_key', dest='google_api_key',
            metavar='GOOGLE_API_KEY', default=GOOGLE_API_KEY, help='Google API key')
    parser.add_argument('-ak', '--acoustid_api_key', dest='acoustid_api_key',
            metavar='ACOUSTID_API_KEY', default=ACOUSTID_API_KEY, help='Acoustid API key')
    # parser.add_argument('-yc', '--use_youtube_cache', dest='use_youtube_cache',
    #         action='store_true', default=False, help='Use YouTube search cache')
    # parser.add_argument('-ycp', '--youtube_cache_path', dest='youtube_cache_path',
    #         metavar = 'YOUTUBE_CACHE_PATH', default=YOUTUBE_CACHE_PATH,
    #         help='Path to YouTube search cache file')
    parser.add_argument('-ymax', '--max_youtube_results', dest='max_youtube_results',
            metavar='MAX_YOUTUBE_RESULTS', type=int, default=MAX_YOUTUBE_RESULTS,
            help='Maximum number of video results returned for a YouTube query')
    parser.add_argument('-cac', '--clear_audio_cache', dest='clear_audio_cache',
            action='store_true', default=False, help='Remove downloaded audio \
            files after fingerprint comparison')

    args = parser.parse_args()

    yt = YouTubeSearchManager(args.google_api_key,
                              max_results=args.max_youtube_results,
                              use_cache=False)
                              #use_cache=args.use_youtube_cache,
                              #cache_path=args.youtube_cache_path)

    ac = YouTubeAcoustidManager(args.acoustid_api_key,
                                AUDIO_CACHE_DIR,
                                VIDEO_CACHE_DIR,
                                clear_cache=args.clear_audio_cache)

    results = {}

    for entry in args.entries:
        if args.search_by_filename:
            iaid, filename_url = entry.split('/', 1)
        else:
            iaid = entry

        item = IAItem(iaid)

        if not item.metadata() or 'error' in item.metadata():
            print("Error: Could not retrieve metadata for item "  + iaid,
                  file = sys.stderr)
            # TODO: Error codes?
            sys.exit(1)

        results[iaid] = {}


        

        if args.search_full_album:
            results[iaid] = match_full_album(yt, item, clear_cache=args.clear_audio_cache)

        #TODO: separate functions
        if not results[iaid]:
            tracks = [unquote(filename_url)] if args.search_by_filename else item.tracks.keys()
            for filename in tracks:
                results[iaid][filename] = ''
                yt_results = search_by_track(yt, item.tracks[filename])
                if yt_results:
                    dl_path = ia_download_file(item, filename)
                    if not dl_path:
                        continue
                    reference_fp = fp.generate_fingerprint(dl_path)
                for v in yt_results:
                    yt_dl_path = download_audio_file_ytdl(v['id'], AUDIO_CACHE_DIR, VIDEO_CACHE_DIR)
                    query_fp = fp.generate_fingerprint(yt_dl_path)
                    if args.clear_audio_cache:
                        os.remove(yt_dl_path)
                    if fp.match_fingerprints(reference_fp, query_fp):
                        results[iaid][filename] = v['id']
                        break
        if args.clear_audio_cache:
            shutil.rmtree('tmp/iaaudio/' + iaid, ignore_errors=True)
    print(results)