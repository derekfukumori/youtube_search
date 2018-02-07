==============
youtube_search
==============

Matches Internet Archive music items to corresponding YouTube videos using acoustid verification.

Usage
=====
``search.py -i /path/to/input_file -o /path/to/output_file``

The input file is a newline-separated list of Internet Archive item identifiers. By default, ``search.py`` will attempt to match every unique track contained in the item. If the ``-sf`` flag is used, then given a CSV of identifier/file URL pairs, ``search.py`` will match only the specified file. The output is a JSON file of the form ``{identifier0: {filename0: id0, filename1: id1, ...}, ...}``, where each ``id`` is a YouTube video id. If no video was found for a given file, its associated id is ``'0'``.

The ``-gk GOOGLE_API_KEY`` and ``-ak ACOUSTID_API_KEY`` options can be used to set different API keys. The default values are my own keys, as defined in ``defaults.py``.

The ``YouTubeSearchManager`` class, contained in ``ytsearch/youtube_search.py`` can cache the results for YouTube queries. The cache is a dictionary of the form ``{query_string0: [video0, video1, ...], ...}``, and is saved to disk as JSON. By default, reading from and writing to the cache is disabled. To enable, run ``search.py`` with the ``-yc`` flag. The ``-ytc /path/to/cache_file`` option can be used to specify the location of the cache file. The ``-ymax N`` option specifies the maximum number of videos returned for a YouTube search. The default location of the cache file and maximum number of search results are defined in ``defaults.py``.

The ``YouTubeAcoustidManager`` class, contained in ``ytsearch/acoustid_search.py`` is responsible for downloading YouTube audio and performing acoustid comparisons. Audio files are saved to disk with the name ``[youtube_video_id].mp4``. Prior to downloading the audio for a YouTube video, ``YouTubeAcoustidManager`` will check to see if a audio file for the corresponding video already exists in the audio cache directory (defined in ``defaults.py``). By default, audio files are not deleted after downloading. To enable automatic deletion after the audio file has been fingerprinted, use the ``-cac`` flag.

In the case that no separate audio stream exists for a given YouTube video, the video stream is downloaded and audio is extracted using FFmpeg (FFmpeg command line tools are required for this, available here: https://www.ffmpeg.org/). Video files are downloaded to a separate video directory, as defined in ``defaults.py``, which should be distinct from the audio directory to avoid filename collisions. Video files are deleted after audio extraction.
