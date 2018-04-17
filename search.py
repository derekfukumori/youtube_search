import argparse
import sys
import os.path
from urllib.parse import unquote
from ytsearch.iametadata import IAItem
from ytsearch.youtube_search import YouTubeSearchManager
from ytsearch.acoustid_search import YouTubeAcoustidManager
from ytsearch.video_ranking import rank_videos
from ytsearch.youtube_download import download_audio_file_ytdl
import audiofp.fingerprint as fp
from defaults import *

def search_by_track(yt, track):
    if not track.acoustid:
        return ''
    # TODO: Refine queries.
    query = track.artist + " " + track.title
    return yt.search(query, track.length)
    return []

def search_by_item(yt, item):
    results = {}
    for name in item.tracks:
        results[name] = search_by_track(yt, item.tracks[name])
    return results

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('entries', metavar='ENTRIES', type=str, nargs='+',
        help='Something')
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

        if args.search_by_filename:
            filename = unquote(filename_url)
            yt_results = {filename: search_by_track(yt, item.tracks[filename])}
        else:
            yt_results = search_by_item(yt, item)

        for name in yt_results:
            results[iaid][name] = ''

            #print('Matching ' + iaid + '/' + name, file=sys.stderr)

            videos = rank_videos(yt_results[name], item.tracks[name])

            if videos:
                errors = item.item.download(silent=True, files=[name], destdir='tmp/iaaudio')
                if errors:
                    #TODO: Error message, exit code
                    exit(1)
                dst_path = 'tmp/iaaudio/' + iaid + '/' + name
                src_fp = fp.generate_fingerprint(dst_path)


            for v in videos:

                #print('  '+v['id'], file=sys.stderr)


                dl_path = download_audio_file_ytdl(v['id'], AUDIO_CACHE_DIR, VIDEO_CACHE_DIR)
                vid_fp = fp.generate_fingerprint(dl_path)

                if fp.match_fingerprints(src_fp, vid_fp):
                    results[iaid][name] = v['id']
                    break
                # if ac.match(v['id'], item.tracks[name].acoustid):
                #     results[iaid][name] = v['id']
                #     break

    print(results)
    #print("", file=sys.stderr)
