import fuzzywuzzy

def in_duration_range(video, expected_duration, duration_range=10):
    return abs(video['duration'] - expected_duration) < duration_range

def videos_cull_by_duration(videos, expected_duration, duration_range=10):
	return [v for v in videos if in_duration_range(v, expected_duration, duration_range)]

def videos_cull_by_keywords(videos, keywords, match_threshold=0.8):
	pass