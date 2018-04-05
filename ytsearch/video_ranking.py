import fuzzywuzzy

def cull_videos(videos, track):
    #videos = [v for v in videos if in_duration_range(v, file_metadata)]
    #TODO: Cull by other criteria?
    videos = [v for v in videos if in_duration_range(v, track)]
    return videos

def rank_videos(videos, track):
    #TODO: Old ranking seemed to make things worse somehow -- revisit.
    videos = cull_videos(videos, track)
    return videos

def in_duration_range(video, track, duration_range=10):
    return abs(video['duration'] - track.length) < duration_range
