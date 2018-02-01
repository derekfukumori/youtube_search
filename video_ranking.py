#import fuzzywuzzy
from youtube_download import download_audio_file
#from pytube import YouTube
from defaults import *
import acoustid
import glob

def get_acoustid(file_metadata):
    acoustid_str = ''
    if 'external-identifier' in file_metadata:
        if isinstance(file_metadata['external-identifier'], str):
            if 'acoustid' in file_metadata['external-identifier']:
                acoustid_str = file_metadata['external-identifier'][13:]
        else:
            for identifier in file_metadata['external-identifier']:
                if 'acoustid' in identifier:
                    acoustid_str = identifier[13:]
    return acoustid_str


def rank_videos(videos, item, file_metadata):
    #TODO: Cull videos based on duration, or duration difference into heuristic value?

    acoustid_str = get_acoustid(file_metadata)

    #if use_acoustid:
    # if 'external-identifier' in file_metadata:
    #     if isinstance(file_metadata['external-identifier'], str):
    #         if 'acoustid' in file_metadata['external-identifier']:
    #             acoustid_str = file_metadata['external-identifier'][13:]
    #     else:
    #         for identifier in file_metadata['external-identifier']:
    #             if 'acoustid' in identifier:
    #                 acoustid_str = identifier[13:]

    if acoustid_str:
        print('\t' + 'acoustid: ' + acoustid_str)
    else:
        return '0'

    videos = [v for v in videos if in_duration_range(v, file_metadata)]

    # if not videos:
    #     return '0'

    for v in videos:
        cached_files = glob.glob('./tmp/' + v['id'] + '.*')
        if cached_files:
            filepath = cached_files[0]
        else:
            filepath = download_audio_file(v['id'])
        if filepath:
            acoustid_matches = acoustid.match(ACOUSTID_API_KEY, filepath, parse=False)
            if 'results' in acoustid_matches:
                for match in acoustid_matches['results']:
                    if match['id'] == acoustid_str:
                        return v['id']

    return '0'
    #return videos[0]['id']

#TODO: Duration range as argument?
def in_duration_range(video, file_metadata):
    return abs(video['duration'] - float(file_metadata['length'])) < 10
