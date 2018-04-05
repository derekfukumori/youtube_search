import os
import sys
import glob
import acoustid
from ytsearch.youtube_download import download_audio_file_ytdl as download_audio_file

class YouTubeAcoustidManager:
    """Handles acoustid matching for YouTube videos.

    Args:
        api_key         (str): Acoustid API key.
        audio_cache_dir (str): Download directory for audio files.
        video_cache_dir (str): Download directory for video files (should be
                               distinct from audio_cache_dir)
        clear_cache    (bool): Flag indicating whether to clear the cached audio
                               file after acoustid comparison
    """
    def __init__(self, api_key, audio_cache_dir, video_cache_dir, clear_cache=False):
        self._api_key = api_key
        self._audio_cache_dir = audio_cache_dir.rstrip('/')
        self._video_cache_dir = video_cache_dir.rstrip('/')
        self._clear_cache = clear_cache

    def match(self, yt_id, target):
        """Checks if the given YouTube video matches the target acoustid

        Downloads the YouTube audio if not already cached, runs the fingerprint
        of that audio against the acoustid database, then checks the returned
        database matches against the target.

        Args:
            yt_id  (str): The YouTube video ID.
            target (str): The target acoustid database ID.

        Returns:
            True if the target is in the fingerprint match results. False otherwise.
        """

        cached_files = glob.glob(self._audio_cache_dir + '/' + yt_id + '.*')
        if cached_files:
            filepath = cached_files[0]
        else:
            filepath = download_audio_file(yt_id, self._audio_cache_dir, self._video_cache_dir)
        if filepath:
            try:
                matches = acoustid.match(self._api_key, filepath, parse=False)
            except acoustid.FingerprintGenerationError:
                print("Could not calculate fingerprint for " + filepath,
                      file = sys.stderr)
                # TODO: Error codes?
                sys.exit(1)
            if self._clear_cache:
                os.remove(filepath)
            if 'results' in matches:
                for match in matches['results']:
                    if match['id'] == target:
                        return True
        return False
