import json
from apiclient.discovery import build
from isodate import parse_duration
from defaults import *

class YouTubeSearchManager:
    def __init__(self, api_key, cache_path, search_cache='True', write_cache='True'):
        self._cache_path = cache_path
        self._search_cache = search_cache
        self._write_cache = write_cache
        self._youtube = build('youtube', 'v3', developerKey=api_key)
        self._cache = {}
        if self._search_cache or self._write_cache:
            try:
                with open(self._cache_path) as f:
                    self._cache = json.load(f)
            except (IOError, json.decoder.JSONDecodeError) as e:
                print("Error: Could not read YouTube results cache.")

    #TODO: Case-insensitive query caching?
    #TODO: Review caching logic.
    def search(self, query, n_results=MAX_VIDEO_RESULTS):

        if self._search_cache and query in self._cache:
            return self._cache[query]

        response = self._youtube.search().list(
            q = query,
            part = "id",
            maxResults = n_results,
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

            #TODO: Store full contentDetails and snippet?
            video_details['title'] = details_response['snippet']['title']
            video_details['description'] = details_response['snippet']['description']
            video_details['duration'] = \
                parse_duration(details_response['contentDetails']['duration']).total_seconds()

            results.append(video_details)

        if self._write_cache:
            self._cache[query] = results

        return results

    def write_cache_to_disk(self):
        try:
            with open(self._cache_path, 'w') as f:
                json.dump(self._cache, f)
        except IOError:
            print("Error: Could not write YouTube results cache.")


"""
def search(query):
    #TODO: Should only have to perform the build once.
    youtube = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
    response = youtube.search().list(
        q = query,
        part = "id",
        maxResults = MAX_VIDEO_RESULTS,
        type = "video"
    ).execute()

    results = []

    for item in response['items']:
        video_id = item['id']['videoId']
        video_details = {'id': video_id}

        details_response = youtube.videos().list(
            part = "contentDetails,snippet",
            id = video_id
        ).execute()['items'][0]

        video_details['title'] = details_response['snippet']['title']
        video_details['description'] = details_response['snippet']['description']
        video_details['duration'] = details_response['contentDetails']['duration']

        results.append(video_details)

    return results
"""
if __name__ == "__main__":
    #metadata = metadata.import_metadata_from_file(METADATA_FILE)
    try:
        #TODO Metadata file as argument.
        with open('data/wcd-rando-1000-metadata.json') as f:
            metadata = json.load(f)
    except IOError:
        metadata = {}

    #TODO Identifiers file as argument.
    identifiers = open(IDENTIFIERS_FILE)

    #TODO Read from cached YouTube search results
    yt_results = {}

    for line in identifiers:
    #for i in range(0,10):
        #line = identifiers.readline()

        iaid, filename = line.rstrip().split(',')
        iaid = unicode(iaid)
        filename = unquote(filename).decode('utf8')
        #TODO: Parameterize queries.
        try:
            query = metadata[iaid][filename]['artist'] + " " + metadata[iaid][filename]['title']
        except KeyError:
            print("Error: Metadata not found for " + iaid + "/" + filename)
            continue

        #TODO: Force search.
        if (query not in yt_results):
            print("Searching " + "\"" + query + "\"..." )
            results = search(query)
            yt_results[query] = results

        #TODO: Output file as argument
        with open('data/wcd-rando-1000-youtube-results.json', 'wb') as yt_out:
            json.dump(yt_results, yt_out)

    identifiers.close()
