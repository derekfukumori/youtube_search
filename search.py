import argparse
import sys
import json
import os
import iametadata as ia
from youtube_search import YouTubeSearchManager
from video_ranking import *
from internetarchive import get_item
#import json
from urllib.parse import unquote
import requests.exceptions
from defaults import *
import glob

#TODO: Construct formatted queries.
def search_by_file_metadata(youtube, item, file_metadata):
    print('\tSearching file \'' + file_metadata['name'] + '\'...')
    query = file_metadata['artist'] + " " + file_metadata['title']
    return match_by_acoustid(youtube.search(query), item, file_metadata)

def search_by_filename(youtube, item, filename):
    return search_by_file_metadata(youtube, item, ia.get_file_metadata(item, filename))

def search_by_item(youtube, item):
    results = {}
    for fm in ia.get_original_audio_files(item):
        results[fm['name']] = search_by_file_metadata(youtube, item, fm)
    return results

#TODO: acoustid API key as argument.
def match_by_acoustid(videos, item, file_metadata):
    acoustid_id = ia.get_acoustid(file_metadata)
    if not acoustid_id:
        return '0'

    #Cull the YouTube search list (currently by duration only)
    videos = cull_videos(videos, file_metadata)
    #TODO: Rework ranking
    #videos = rank_videos(videos, item, file_metadata)

    for v in videos:
        cached_files = glob.glob(AUDIO_CACHE_DIR.rstrip('/') + '/' + v['id'] + '.*')
        if cached_files:
            filepath = cached_files[0]
        else:
            filepath = download_audio_file(v['id'], AUDIO_CACHE_DIR, VIDEO_CACHE_DIR)
        if filepath:
            print('\t\tRunning acoustid match on \'' + v['id'] + '\' (\''\
                  + v['title'] + '\')...')
            acoustid_matches = acoustid.match(ACOUSTID_API_KEY, filepath, parse=False)
            if 'results' in acoustid_matches:
                for match in acoustid_matches['results']:
                    print('\t\t\t' + match['id'])
                    if match['id'] == acoustid_id:
                        print('\t\t\tMatch found')
                        return v['id']
    return '0'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch and JSONify file\
            metadata from [identifier,filepath] CSV file')
    parser.add_argument('-i', '--input', dest='input_file', metavar='INPUTFILE',
            default=IDENTIFIERS_FILE, help='Input CSV file')
    parser.add_argument('-o', '--output', dest='output_file', metavar='OUTPUTFILE',
            default=OUTPUT_FILE, help='Output JSON file')
    parser.add_argument('-sf', '--searchbyfilename', dest='search_by_filename',
            action='store_true', default=False, help='Search using an input \
            CSV of identifier/file URL pairs')
    parser.add_argument('-gk', '--google_api_key', dest='google_api_key',
            metavar='GOOGLE_API_KEY', default=GOOGLE_API_KEY, help='Google API key')
    parser.add_argument('-ak', '--acoustid_api_key', dest='acoustid_api_key',
            metavar='ACOUSTID_API_KEY', default=ACOUSTID_API_KEY, help='Acoustid API key')
    parser.add_argument('-yc', '--use_youtube_cache', dest='use_youtube_cache',
            action='store_true', default=False, help='Use YouTube search cache')
    parser.add_argument('-ycpath', '--youtube_cache_path', dest='youtube_cache_path',
            metavar = 'YOUTUBE_CACHE_PATH', default=YOUTUBE_CACHE_PATH,
            help='Path to YouTube search cache file')
    parser.add_argument('-ymax', '--max_youtube_results', dest='max_youtube_results',
            metavar='MAX_YOUTUBE_RESULTS', type=int, default=MAX_YOUTUBE_RESULTS,
            help='Maximum number of video results returned for a YouTube query')
    parser.add_argument('-r', '--userange', dest='use_range',
            action='store_true', default=False)
    parser.add_argument('-rs', '--rangestart', dest='range_start', metavar='RANGESTART',
            type=int, default=0)
    parser.add_argument('-re', '--rangeend', dest='range_end', metavar='RANGEEND',
            type=int, default=0)
    args = parser.parse_args()

    #Set up cache directories
    os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
    os.makedirs(VIDEO_CACHE_DIR, exist_ok=True)
    os.makedirs(METADATA_CACHE_DIR, exist_ok=True)

    try:
        with open(args.input_file) as f:
            items = f.readlines()
    except IOError:
        print("Error: Could not read input file.", file=sys.stderr)
        exit(1)

    #TODO: Results cache as argument
    yt = YouTubeSearchManager(args.google_api_key,
                              max_results=args.max_youtube_results,
                              use_cache=args.use_youtube_cache,
                              cache_path=args.youtube_cache_path)
    yt_results = {}

    rs = args.range_start if args.use_range else 0
    re = min(len(items), args.range_end + 1) if args.use_range else len(items)

    for i in range(rs,re):
        iaid,filename_url = items[i].rstrip().split(',')

        print('Searching item \'' + iaid + '\'...')

        #TODO: Sometimes internetarchive.get_item() fails(?) without raising an
        # exception, causing a KeyError when metadata['files'] is accessed.
        # Determine the value of ia_item when the failure occurs, and check validity before searching.
        try:
            ia_item = get_item(iaid)
        except requests.exceptions.ConnectionError:
            print('Error: Could not connect to Internet Archive.', file=sys.stderr)
            continue

        if not ia_item.item_metadata:
            print('Error: Internet Archive returned no metadata for item \'' + iaid
                  + '\'.', file=sys.stderr)
            continue

        if iaid not in yt_results:
            yt_results[iaid] = {}

        if args.search_by_filename:
            filename = unquote(filename_url)
            yt_results[iaid][filename] = search_by_filename(yt, ia_item, filename)
        else:
            yt_results[iaid] = search_by_item(yt, ia_item)

    try:
        with open(args.output_file, 'w') as f:
            json.dump(yt_results, f)
    except IOError:
        print("Error: Could not write to output file.", file=sys.stderr)

    if args.use_youtube_cache:
        yt.write_cache_to_disk()
