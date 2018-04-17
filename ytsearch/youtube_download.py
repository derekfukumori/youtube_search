import sys
import glob
import subprocess
from os import remove
from os.path import exists, isfile
import pytube
import audioread

def download_audio_file_ytdl(yt_id, audio_dir, video_dir):
    """Downloads the audio of a YouTube video via youtube-dl.

    Args:
        yt_id     (str): The YouTube video ID.
        audio_dir (str): Download location for audio streams.
        video_dir (str): Download location for video streams.

    Returns:
        The path of the downloaded file, or a blank stream on unsuccessful
        download or FFmpeg conversion.
    """

    path_no_ext = audio_dir.rstrip('/') + '/' +  yt_id

    # Return cached file
    cached_files = glob.glob(path_no_ext + '.*')
    if cached_files:
        return cached_files[0]

    output_template = path_no_ext + '.%(ext)s'
    try:
        # TODO: It seems like youtube-dl provides an audio-only stream in cases
        # where pytube did not. Does it always? If not, define fallback behavior.
        subprocess.run(['youtube-dl', '--prefer-ffmpeg','--no-check-certificate', '-q', '-o', output_template,
                       '-f', 'bestaudio', 'https://www.youtube.com/watch?v=' + yt_id],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError:
        pass
    finally:
        pass

    dl_files = glob.glob(path_no_ext + '.*')
    if dl_files:
        return dl_files[0]

    return ''

#TODO: retries (retrying library?).
def download_audio_file_pytube(yt_id, audio_dir, video_dir):
    """Downloads the audio of a YouTube video via pytube.

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

    path_no_ext = audio_dir.rstrip('/') + '/' +  yt_id

    # Return cached file
    cached_files = glob.glob(path_no_ext + '.*')
    if cached_files:
        return cached_files[0]
    
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
        audio_path =  audio_dir.rstrip('/') + '/' + yt_id + '.' + get_stream_extension(stream)
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

# TODO: audioread doesn't play nicely with vorbis-encoded files. Determine a
# better way to validate files.
def is_audio_valid(path):
    # try:
    #     print('opening audio file' + path)
    #     with audioread.audio_open(path) as f:
    #         print('audio opened')
    #         pass
    # except audioread.DecodeError:
    #     print('error. removing audio file')
    #     remove(path)
    #     return False
    # except FileNotFoundError:
    #     print('file not found')
    #     return False
    return True
