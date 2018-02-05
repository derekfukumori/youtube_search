import argparse
import sys
import iametadata as ia
from youtube_search import YouTubeSearchManager
from video_ranking import *
from internetarchive import get_item
#import json
from urllib.parse import unquote
import requests.exceptions
from defaults import *



#TODO: Construct formatted queries, list merging.
def search_by_file_metadata(youtube, item, file_metadata):
    query = file_metadata['artist'] + " " + file_metadata['title']
    return rank_videos(youtube.search(query), item, file_metadata)

def search_by_filename(youtube, item, filename):
    return search_by_file_metadata(youtube, item, ia.get_file_metadata(filename))

def search_by_item(youtube, item):
    results = {}
    for fm in ia.get_audio_files(item):
        results[fm['name']] = search_by_file_metadata(youtube, item, fm)
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch and JSONify file\
            metadata from [identifier,filepath] CSV file')
    parser.add_argument('-i', '--input', dest='input_file', metavar='INPUTFILE',
            default=IDENTIFIERS_FILE, help='Input CSV file')
    parser.add_argument('-o', '--output', dest='output_file', metavar='OUTPUTFILE',
            default=METADATA_FILE, help='Output path')
    # parser.add_argument('-sf', '--searchbyfilename', dest='search_by_filename',
    #         action='store_true', default=False)
    parser.add_argument('-r', '--userange', dest='use_range',
            action='store_true', default=False)
    parser.add_argument('-rs', '--rangestart', dest='range_start', metavar='RANGESTART',
            type=int, default=0)
    parser.add_argument('-re', '--rangeend', dest='range_end', metavar='RANGEEND',
            type=int, default=0)
    args = parser.parse_args()

    try:
        with open(args.input_file) as f:
            items = f.readlines()
    except IOError:
        print("Error: Could not read input file.", file=sys.stderr)
        exit(1)

    #TODO: Results cache as argument
    yt = YouTubeSearchManager(GOOGLE_API_KEY, "data/wcd-rando-1000-yt-cache.json")
    yt_results = {}

    #outfile = open("data/wcd-rando-1000-results.tsv", 'w')
    outfile = open(args.output_file, 'w')

    rs = args.range_start if args.use_range else 0
    re = args.range_end + 1 if args.use_range else len(items)


    for i in range(rs,re):
        iaid,filename_url = items[i].rstrip().split(',')
        filename = unquote(filename_url)

        print('Searching ' + iaid + '/' + filename + '...')

        if iaid not in yt_results:
            yt_results[iaid] = {}

        #TODO: Sometimes internetarchive.get_item() fails(?) without raising an
        # exception, causing a KeyError when metadata['files'] is accessed.
        # Determine the value of ia_item when the failure occurs, and check validity before searching.
        try:
            ia_item = get_item(iaid)
        except requests.exceptions.ConnectionError:
            print('Error: Could not retrieve metadata for ' + iaid + '.', file=sys.stderr)
            continue

        # yt_results[iaid][filename] = search_by_filename(yt, ia_item, filename)
        # if yt_results[iaid][filename] == '0':
        #     not_found += 1
        # else:
        #     found += 1
        #
        # file_metadata = ia.get_file_metadata(ia_item, filename)
        #
        # url = 'https://www.youtube.com/watch?v=' + yt_results[iaid][filename] if yt_results[iaid][filename] != '0' else ''
        # outfile.write(iaid + '/' + filename_url + '\t' + file_metadata['artist'] + '\t' + file_metadata['title'] + '\t' + url + '\n')

    #yt.write_cache_to_disk()
    #TODO: Write results to disk.
    outfile.close()
