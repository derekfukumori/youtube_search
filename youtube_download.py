import pytube
import glob
import subprocess
from os import remove

#TODO: download locations, audio file verification, retries (retrying library?).
def download_audio_file(yt_id):
    """Downloads the audio of a YouTube video.

    Prioritizes audio streams. If no audio stream is present, downloads a
    video stream and extracts the audio with FFmpeg.

    Args:
        yt_id (str): The YouTube video ID.

    Returns:
        The path of the downloaded file, or a blank stream on unsuccessful
        download or FFmpeg conversion.
    """

    yt = pytube.YouTube('https://www.youtube.com/watch?v=' + yt_id)
    if yt.streams.filter(only_audio=True).first():
        #TODO: Determine which stream to download; Error handling.
        yt.streams.filter(only_audio=True).first().download('./tmp', yt_id)
        #TODO: Is there an efficient way of determining file extension pre-
        # or post-download?
        return glob.glob('./tmp/' + yt_id + '*')[0]
    else:
        #Download and extract audio from video stream.

        #TODO: Determine which stream to download; Error handling.
        yt.streams.first().download('./tmp/video', yt_id)
        video_path = glob.glob('./tmp/video/' + yt_id + '*')[0]
        audio_path = './tmp/' + yt_id + '.mp4'
        try:
            subprocess.run(['ffmpeg', '-i', video_path, '-vn', '-y', '-acodec', 'copy', \
            audio_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return audio_path
        except subprocess.CalledProcessError:
            return ''
        finally:
            remove(video_path)


def get_stream_extension(stream):
    return stream.mime_type.split('/')[1]
