import internetarchive
import logging
import re
import enum
import os
from os.path import splitext
from copy import copy
from ytsearch.exceptions import *
from requests.exceptions import ConnectionError
from requests.exceptions import ReadTimeout

MAX_RETRIES = 10

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class AudioFiletype(enum.Enum):
    """Enum representing audio filetypes. Ordering represents the preferred
    download format for audio fingerprinting, from most to least desirable.
    """
    MP3 = enum.auto(),
    OGG = enum.auto(),
    FLAC = enum.auto(),
    M4A = enum.auto()

def filename_to_audio_filetype(filename):
    """ Given a filename, return the AudioFiletype value corresponding to the
    file's extension. If the file is not one of the enumerated types, return None.
    """
    ext = splitext(filename)[1]
    if ext.lower() == '.mp3':
        return AudioFiletype.MP3
    elif ext.lower() == '.ogg':
        return AudioFiletype.OGG
    elif ext.lower() == '.flac':
        return AudioFiletype.FLAC
    elif ext.lower() == '.m4a':
        return AudioFiletype.M4A

def get_track_duration(track_md):
    """ Get the duration of a track in seconds, given the track's metadata.
    If no valid duration format is present, return zero.
    """
    if 'length' in track_md:
        # Seconds as a float
        match = re.match('^\d+(\.\d*)?$', track_md['length'])
        if match:
            return float(track_md['length'])
        #TODO: Do durations ever take the form HH:MM:SS?
        # MM:SS
        match = re.match('(\d+):(\d{2})$', track_md['length'])
        if match:
            return 60*float(match.group(1)) + float(match.group(2))
    return 0

def get_track_ordinal(track_md):
    """ Get the ordinal of a track representing its placement on an album, given
    the track's metadata. If no ordering is specified in metadata, use the
    numerals in the track's filename.
    NB: This (usually) gives incorrect results for multidisc items.
    """
    ordinal = track_md['track'] if 'track' in track_md else track_md['name']
    ordinal = re.sub('[^0-9]+', '', ordinal)
    return int(ordinal) if ordinal else 0

def get_item_artist(item_md):
    """ Get the primary artist of an item, given the item's metadata
    """
    artist = ''
    if 'artist' in item_md:
        if isinstance(item_md['artist'], str):
            artist = item_md['artist']
        else:
            artist = item_md['artist'][0]
    elif 'creator' in item_md:
        if isinstance(item_md['creator'], str):
            artist = item_md['creator']
        else:
            artist = item_md['creator'][0]
    return artist


class IATrack:
    def __init__(self, parent_album, metadata):
        self.parent_album = parent_album
        self.metadata = metadata
        self.name = metadata['name']
        self.orig_filetype = filename_to_audio_filetype(self.name)
        self.title = metadata['title']
        self.artist = metadata['artist'] if 'artist' in metadata else metadata['creator']
        self.creator = metadata.get('creator', '')
        self.album_title = metadata['album']
        self.duration = get_track_duration(metadata)
        self.ordinal = get_track_ordinal(metadata)
        self.derivatives = {}
        
    def add_derivative(self, filetype, filename):
        self.derivatives[filetype] = filename

    def get_dl_filename(self):
        """ Get the filename of the preferred download format for this track.
        """
        for ftype in AudioFiletype:
            if ftype == self.orig_filetype:
                return self.name
            elif ftype in self.derivatives:
                return self.derivatives[ftype]

    def get_eid(self, eid_source):
        eids = copy(self.metadata.get('external-identifier', []))
        eids = eids if isinstance(eids, list) else [eids]
        for eid in eids:
            if eid.startswith('urn:{}'.format(eid_source)):
                return eid.split(':', 2)[-1]
        return None

    def download(self, destdir='.'):
        path = '{}/{}/{}'.format(destdir.rstrip('/'),
                             self.parent_album.identifier,
                             self.get_dl_filename())

        # If a file already exists at this path, return
        if os.path.isfile(path):
             return path

        for _ in range(MAX_RETRIES):
            try:
                errors = self.parent_album.item.download(files=[self.get_dl_filename()], 
                                                         destdir=destdir,
                                                         silent=True)
                if errors:
                    raise DownloadException(path)
            except ReadTimeout:
                continue
            else:
                break
        else:
            raise DownloadException(path)

        return path


class IAAlbum:
    def __init__(self, iaid):
        for _ in range(MAX_RETRIES):
            try:
                self.item = internetarchive.get_item(iaid)
            except ReadTimeout:
                continue
            else:
                break
        else:
            raise DownloadException(iaid)

        if not self.item.item_metadata or 'error' in self.item.item_metadata:
            raise MetadataException(iaid)

        if self.item.item_metadata['metadata']['mediatype'] != 'audio':
            raise MediaTypeException(iaid)

        self.identifier = iaid
        self.artist = get_item_artist(self.item.item_metadata['metadata'])
        self.creator = self.item.item_metadata['metadata'].get('creator', '')
        self.tracks = []
        for file_md in self.item.files:
            if file_md['source'] == 'original' and filename_to_audio_filetype(file_md['name']):
                try:
                    self.tracks.append(IATrack(self, file_md))
                except KeyError as e:
                    logger.warning('{}: File "{}" does not contain metadata entry {}'.format(iaid, file_md['name'], e))
        if not self.tracks:
            logger.error('{}: Unable to find valid tracks'.format(iaid))
            raise MetadataException(iaid)
        self.tracks.sort(key=lambda t: t.ordinal)
        self.track_map = dict((track.name, track) for track in self.tracks)

        # Associate track objects with their non-sample derivative audio files.
        for file_md in self.item.files:
            filetype = filename_to_audio_filetype(file_md['name'])
            if filetype and file_md['source'] == 'derivative' \
            and file_md['original'] in self.track_map \
            and not splitext(file_md['name'])[0].endswith('_sample'):
                self.track_map[file_md['original']].add_derivative(filetype, file_md['name'])
        
        # Note: whatcd items often have release information in the item-level
        # 'album' field, e.g. '[Album Title] / Original Release / CD / FLAC / Lossless'.
        # The current workaround is to pull the album title from file metadata.
        self.title = self.tracks[0].album_title
        self.duration = sum(track.duration for track in self.tracks)

    def get_eid(self, eid_source):
        eids = copy(self.item.item_metadata['metadata'].get('external-identifier', []))
        eids = eids if isinstance(eids, list) else [eids]
        for eid in eids:
            if eid.startswith('urn:{}'.format(eid_source)):
                return eid.split(':', 2)[-1]
        return None
