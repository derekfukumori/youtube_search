import logging
import time
from apiclient.discovery import build
from isodate import parse_duration
from random import choice

logger = logging.getLogger('youtube_search')
fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(fmt)
logger.addHandler(ch)

def get_expected_duration(duration):
	if duration < 230:
		return "short"
	elif duration > 250 and duration < 1190:
		return "medium"
	elif duration > 1210:
		return "long"
	return "any"

def search(query, expected_duration='any', api_key=''):
	api_key = choice(api_key) if isinstance(api_key, list) else api_key
	yt = build('youtube', 'v3', developerKey=api_key) # ~600ms build time.
	
	results = []

	response = yt.search().list(
			q = query,
			part = "id",
			maxResults = 10,
			order = "relevance",
			type = "video",
			safeSearch = "none",
			topicId = "/m/04rlf",
			videoDuration = expected_duration
		).execute()

	for item in response['items']:
		video_id = item['id']['videoId']
		video_details = {'id': video_id}

		details_response = yt.videos().list(
			part = "contentDetails,snippet",
			id = video_id
		).execute()['items'][0]

		video_details['title'] = details_response['snippet']['title']
		#video_details['description'] = details_response['snippet']['description']
		video_details['duration'] = \
			parse_duration(details_response['contentDetails']['duration']).total_seconds()

		results.append(video_details)

	return results


def search_by_track(ia_track, query_fmt='{artist} {title}', api_key=''):
	# TODO: Support queries for albums with multiple artists
	query = query_fmt.format(artist = ia_track.artists[0], 
							 title  = ia_track.title)
	return search(query, expected_duration=get_expected_duration(ia_track.duration),
				  api_key=api_key)

def search_by_album(ia_album, query_fmt='{artist} {title}', api_key=''):
	# TODO: Support queries for albums with multiple artists
	query = query_fmt.format(artist = ia_album.artists[0], 
							 title  = ia_album.title)
	return search(query, expected_duration=get_expected_duration(ia_album.duration),
				  api_key=api_key)