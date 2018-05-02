import internetarchive
import os.path

audio_extensions = ['.mp3', '.flac', '.ogg']

class IATrack:
    def __init__(self, metadata):
        self.metadata = metadata
        self.name = metadata['name']
        self.title = metadata['title']
        self.artist = metadata['artist']
        self.album = metadata['album']
        self.length = float(metadata['length'])
        self.track_ordering = metadata['track'] if 'track' in metadata else self.name
        self.acoustid = ''
        if 'external-identifier' in metadata:
            if isinstance(metadata['external-identifier'], str):
                if 'acoustid' in metadata['external-identifier']:
                    self.acoustid = metadata['external-identifier'][13:]
            else:
                for identifier in metadata['external-identifier']:
                    if 'acoustid' in identifier:
                        self.acoustid = identifier[13:]
    def __index__(self, index):
        return self.metadata[index]


class IAItem:
    def __init__(self, iaid):
        self.item = internetarchive.get_item(iaid)
        self.artist = self.item.item_metadata['metadata']['artist']
        album_val = self.item.item_metadata['metadata']['album']
        self.album = album_val if isinstance(album_val, str) else album_val[0]
        self.tracks = dict((md['name'], IATrack(md)) for md in self.item.files
                      if md['source'] == 'original'
                      and os.path.splitext(md['name'])[1] in audio_extensions)
        self.length = 0
        for track in self.tracks.values():
            self.length += track.length
    def metadata(self):
        return self.item.item_metadata




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
