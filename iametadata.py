import internetarchive
import os.path

# def get_ia_metadata(item_id):
#     print("ffff")
#     return internetarchive.get_item(item_id)

audio_extensions = ['.mp3', '.flac', '.ogg']

def get_original_audio_files(item):
    return [f for f in item.item_metadata['files'] if f['source'] == 'original'\
            and os.path.splitext(f['name'])[1] in audio_extensions]

def get_file_metadata(item, filename):
    for file_metadata in item.item_metadata['files']:
        if file_metadata['name'] == filename:
            return file_metadata
    return {}

def get_acoustid(file_metadata):
    acoustid_str = ''
    if 'external-identifier' in file_metadata:
        if isinstance(file_metadata['external-identifier'], str):
            if 'acoustid' in file_metadata['external-identifier']:
                acoustid_str = file_metadata['external-identifier'][13:]
        else:
            for identifier in file_metadata['external-identifier']:
                if 'acoustid' in identifier:
                    acoustid_str = identifier[13:]
    return acoustid_str
