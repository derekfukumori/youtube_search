import json
import sys
from apiclient.discovery import build
from isodate import parse_duration
from defaults import *

class YouTubeSearchManager:
    """Handles YouTube video searches.

    Args:
        api_key      (str): Google API key.
        max_results  (int): Maximum number of video results to be returned for a
                            given query.
        use_cache   (bool): Flag indicating whether to use the search cache.
        cache_path   (str): Path to the search cache file.
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
    def search(self, query, duration):
        """Performs a YouTube search for the given query string.

        If caching is enabled, search will first attempt to return a cached copy
        of the results for the given query, and will cache the results if no
        such results already exist.

        Args:
            query (str): The query string.

        Returns:
            A list of dicts corresponding to YouTube videos. Each dict contains
            fields 'id', 'title', 'duration' and 'description'.
        """
        if self._use_cache and query in self._cache\
        and len(self._cache[query]) >= self._max_results:
            return self._cache[query][:self._max_results]

        # Set the expected video duration.
        # Video duration often differs slightly from file duration. If the file
        # duration falls within ten seconds of a YouTube duration threshold,
        # don't specify an expected duration.
        expected_duration = "any"
        if duration < 230:
            expected_duration = "short"
        elif duration > 250 and duration < 1190:
            expected_duration = "medium"
        elif duration > 1210:
            expected_duration = "long"

        response = self._youtube.search().list(
            q = query,
            part = "id",
            maxResults = self._max_results,
            order = "relevance",
            type = "video",
            safeSearch = "none",
            topicId = "/m/04rlf",
            videoDuration = expected_duration
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
