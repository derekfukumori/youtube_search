import json
import sys
from apiclient.discovery import build
from isodate import parse_duration
from defaults import *

class YouTubeSearchManager:
    """Handles YouTube video queries
    """
    def __init__(self, api_key, max_results=10, use_cache='False', cache_path=''):
        self._cache_path = cache_path
        self._use_cache = use_cache
        self._max_results = max_results
        self._youtube = build('youtube', 'v3', developerKey=api_key)
        self._cache = {}
        #TODO Check if file exists rather than IOError. Except json.JSONDecodeError.
        if self._cache_path and self._use_cache:
            try:
                with open(self._cache_path) as f:
                    self._cache = json.load(f)
            except (IOError, json.decoder.JSONDecodeError) as e:
                print("Error: Could not read YouTube results cache.")

    #TODO: Case-insensitive query caching.
    def search(self, query):

        if self._use_cache and query in self._cache:
            return self._cache[query]

        response = self._youtube.search().list(
            q = query,
            part = "id",
            maxResults = self._max_results,
            type = "video"
        ).execute()

        results = []

        for item in response['items']:
            video_id = item['id']['videoId']
            video_details = {'id': video_id}

            details_response = self._youtube.videos().list(
                part = "contentDetails,snippet",
                id = video_id
            ).execute()['items'][0]

            video_details['title'] = details_response['snippet']['title']
            video_details['description'] = details_response['snippet']['description']
            video_details['duration'] = \
                parse_duration(details_response['contentDetails']['duration']).total_seconds()

            results.append(video_details)

        if self._use_cache:
            self._cache[query] = results

        return results

    def write_cache_to_disk(self):
        if self._cache_path and self._use_cache:
            try:
                with open(self._cache_path, 'w') as f:
                    json.dump(self._cache, f)
            except IOError:
                print("Error: Could not write YouTube results cache.", file=sys.stderr)
