import pytube
import sys
import glob
import subprocess
from os import remove
from os.path import exists, isfile
import audioread
import time

#TODO: retries (retrying library?).
def download_audio_file(yt_id, audio_dir, video_dir):
    """Downloads the audio of a YouTube video.

    Prioritizes audio streams. If no audio stream is present, downloads a
    video stream and extracts the audio with FFmpeg.

    Args:
        yt_id     (str): The YouTube video ID.
        audio_dir (str): Download location for audio streams.
        video_dir (str): Download location for video streams.

    Returns:
        The path of the downloaded file, or a blank stream on unsuccessful
        download or FFmpeg conversion.
    """
    try:
        yt = pytube.YouTube('https://www.youtube.com/watch?v=' + yt_id)
    except pytube.exceptions.RegexMatchError:
        print('Error: Could not download audio stream. Invalid YouTube video id '\
         + yt_id, file=sys.stderr)
        return ''

    #TODO: Determine which stream to prioritize; Error handling.
    stream = yt.streams.filter(only_audio=True).first()

    if stream:
        stream.download(audio_dir, yt_id)
        audio_path = audio_dir.rstrip('/') + '/' + yt_id + '.' \
                     + get_stream_extension(stream)
    else:
        #Download and extract audio from video stream.
        #TODO: Determine which stream to prioritize; Error handling.
        stream = yt.streams.first()
        stream.download(video_dir, yt_id)
        video_path = video_dir.rstrip('/') + '/' + yt_id + '.' \
                     + get_stream_extension(stream)
        audio_path =  audio_dir.rstrip('/') + '/' + yt_id + '.mp4'
        try:
            subprocess.run(['ffmpeg', '-i', video_path, '-vn', '-y', '-acodec', 'copy', \
            audio_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError:
            return ''
        finally:
            remove(video_path)

    if is_audio_valid(audio_path):
        return audio_path
    else:
        #TODO: Retries
        return ''

def get_stream_extension(stream):
    return stream.mime_type.split('/')[1]

def is_audio_valid(path):
    try:
        with audioread.audio_open(path) as f:
            pass
    except audioread.DecodeError:
        remove(path)
        return False
    except FileNotFoundError:
        return False
    return True
