import fuzzywuzzy

def cull_videos(videos, file_metadata):
    videos = [v for v in videos if in_duration_range(v, file_metadata)]
    #TODO: Cull by other criteria?
    return videos

def rank_videos(videos, item, file_metadata):
    #TODO: Old ranking seemed to make things worse somehow -- revisit.
    videos = cull_videos(videos, file_metadata)
    return videos

def in_duration_range(video, file_metadata, duration_range=10):
    return abs(video['duration'] - float(file_metadata['length'])) < duration_range
