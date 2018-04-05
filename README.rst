==============
youtube_search
==============

Matches Internet Archive music items to corresponding YouTube videos using acoustid verification.

Usage
=====
``search.py itemid [...]``
``search.py -sf itemid/filename [...]``

``search.py`` takes as arguments a list of item ids. Individual files can matched using the ``-sf`` flag, in which case arguments should be of the form [id]/[filename_url]. The output is a JSON file of the form ``{identifier0: {filename0: id0, filename1: id1, ...}, ...}``, where each ``id`` is a YouTube video id. If no video was found for a given file, its associated id is ``'0'``.

The ``-gk GOOGLE_API_KEY`` and ``-ak ACOUSTID_API_KEY`` options can be used to set different API keys. The default values are my own keys, as defined in ``defaults.py``.

The ``YouTubeAcoustidManager`` class, contained in ``ytsearch/acoustid_search.py`` is responsible for downloading YouTube audio and performing acoustid comparisons. Audio files are saved to disk with the name ``[youtube_video_id].[ext]``. Prior to downloading the audio for a YouTube video, ``YouTubeAcoustidManager`` will check to see if a audio file for the corresponding video already exists in the audio cache directory (defined in ``defaults.py``). By default, audio files are not deleted after downloading. To enable automatic deletion after the audio file has been fingerprinted, use the ``-cac`` flag.

In the case that no separate audio stream exists for a given YouTube video, the video stream is downloaded and audio is extracted using FFmpeg (FFmpeg command line tools are required for this, available here: https://www.ffmpeg.org/). Video files are downloaded to a separate video directory, as defined in ``defaults.py``, which should be distinct from the audio directory to avoid filename collisions. Video files are deleted after audio extraction.
