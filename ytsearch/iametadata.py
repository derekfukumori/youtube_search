import internetarchive
import os.path
import re

audio_extensions = ['.mp3', '.flac', '.ogg']

class IATrack:
    def __init__(self, metadata, item_metadata):

        creators = metadata['creator'] if 'creator' in metadata else item_metadata['metadata']['creator']
        primary_creator = creators if isinstance(creators, str) else creators[0]

        creator_tokens = [t.lstrip() for t in primary_creator.split(',')]
        for t in creator_tokens:
            if re.compile("\d{4}-(\d{4})?").match(t):
                creator_tokens.remove(t)

        creator = (creator_tokens[1] + ' ' if len(creator_tokens) > 1 else '') + creator_tokens[0]

        if re.compile("\d+:\d{2}").match(metadata['length']):
            length_tokens = metadata['length'].split(':')
            formatted_length = float(length_tokens[0])*60 + float(length_tokens[1])
        elif re.compile("\d+(\.\d*)?").match(metadata['length']):
            formatted_length = float(metadata['length'])
        else:
            formatted_length = 0.0

        self.metadata = metadata
        self.name = metadata['name']
        self.title = metadata['title'] if 'title' in metadata else ''
        self.artist = creator
        self.album = item_metadata['metadata']['title'] if 'title' in item_metadata['metadata'] else ''
        self.length = formatted_length
        
    def __index__(self, index):
        return self.metadata[index]


class IAItem:
    def __init__(self, iaid):
        self.item = internetarchive.get_item(iaid)
        
        # self.tracks = dict((md['name'], IATrack(md)) for md in self.item.files
        #               if md['source'] == 'original'
        #               and os.path.splitext(md['name'])[1] in audio_extensions)

        ftypes = {ext:[] for ext in audio_extensions}
        for f in self.item.files:
            fname, ext = os.path.splitext(f['name'])
            if ext in audio_extensions and not fname.endswith('_sample') and not fname.startswith(iaid):
                ftypes[ext].append(f)
        
        if len(ftypes['.flac']) < len(ftypes['.mp3']):
            if len(ftypes['.mp3']) < len(ftypes['.ogg']):
                files= ftypes['.ogg']
            else:
                files = ftypes['.mp3']
        else:
            files = ftypes['.flac']

        self.tracks = dict((md['name'], IATrack(md, self.item.item_metadata)) for md in files)


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
