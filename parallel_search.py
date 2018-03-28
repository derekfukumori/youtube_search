import argparse
import defaults
from ytsearch.iametadata import IAItem
from ytsearch.youtube_search import YouTubeSearchManager
from ytsearch.acoustid_search import YouTubeAcoustidManager
from ytsearch.video_ranking import rank_videos

def search_by_track(yt, track):
    if not track.acoustid:
        return ''
    # TODO: Refine queries.
    query = track.artist + " " + track.title
    return yt.search(query)

def search_by_item(yt, item):
    results = {}
    for name in item.tracks:
        results[name] = search_by_track(yt, item.tracks[name])
    return results

if __name__=='__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('items', metavar='ITEM', type=str, nargs='+',
        help='Something')
    args = parser.parse_args()


    yt = YouTubeSearchManager(defaults.GOOGLE_API_KEY,
                              max_results=defaults.MAX_YOUTUBE_RESULTS,
                              use_cache=False)

    ac = YouTubeAcoustidManager(defaults.ACOUSTID_API_KEY,
                                defaults.AUDIO_CACHE_DIR,
                                defaults.VIDEO_CACHE_DIR,
                                clear_cache=True)
    for iaid in args.items:
        results = {}
        item = IAItem(iaid)
        yt_results = search_by_item(yt, item)
        for name in yt_results:
            results[name] = ''
            videos = rank_videos(yt_results[name], item.tracks[name])
            for v in videos:
                if ac.match(v['id'], item.tracks[name].acoustid):
                    results[name] = v['id']
                    break

        print(results, len(results))
