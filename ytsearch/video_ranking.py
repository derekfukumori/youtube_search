import fuzzywuzzy

def cull_videos(videos, track):
    #videos = [v for v in videos if in_duration_range(v, file_metadata)]
    #TODO: Cull by other criteria?
    videos = [v for v in videos if in_duration_range(v, track.length)]
    return videos

def rank_videos(videos, track):
    #TODO: Old ranking seemed to make things worse somehow -- revisit.
    videos = cull_videos(videos, track)
    return videos

def in_duration_range(video, expected_duration, duration_range=10):
    return abs(video['duration'] - expected_duration) < duration_range

def videos_cull_by_duration(videos, expected_duration, duration_range=10):
	return [v for v in videos if in_duration_range(v, expected_duration, duration_range)]

def videos_cull_by_keywords(videos, keywords, match_threshold=0.8):
	pass