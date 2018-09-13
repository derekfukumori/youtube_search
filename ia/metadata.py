import internetarchive
import logging
import re
import json
from metadata.util import to_list
from metadata.music_metadata import Album, Track
from os.path import splitext
from copy import copy
from exceptions import *
from requests.exceptions import ConnectionError
from requests.exceptions import ReadTimeout

MAX_RETRIES = 10

class IAAlbum(Album):
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

		ia_item_md = self.item.item_metadata['metadata']

		print(json.dumps(self.item.item_metadata['metadata']))
		self.source = 'ia_item'
		self.id = self.item.identifier
		self.artists = to_list(ia_item_md.get('artist', ia_item_md.get('creator', None)))
		self.title = ia_item_md['title'] # This works for ACDC, but won't for what.cd
		self.publisher = ia_item_md['publisher']
		self.track_map = {}
		self.populate_tracks()
		self.populate_derivatives()
		for t in self.tracks:
			print(t, t.derivatives)
		
	def populate_tracks(self):
		for ia_file_md in self.item.files:
			if ia_file_md['source'] == 'original' and filename_to_audio_filetype(ia_file_md['name']):
				try:
					ia_track = IATrack(ia_file_md)
				except KeyError as e:
					logger.warning('{}: File "{}" does not contain metadata entry {}'.format(iaid, ia_file_md['name'], e))
				self.tracks.append(ia_track)
				self.track_map[ia_track.id] = ia_track
		if not self.tracks:
			logger.error('{}: Unable to find valid tracks'.format(iaid))
			raise MetadataException(iaid)

	def populate_derivatives(self):
		for ia_file_md in self.item.files:
			filetype = filename_to_audio_filetype(ia_file_md['name'])
			if filetype and ia_file_md['source'] == 'derivative' \
			and ia_file_md['original'] in self.track_map \
			and not splitext(ia_file_md['name'])[0].endswith('_sample'):
				self.track_map[ia_file_md['original']].derivatives[filetype] = ia_file_md['name']

	def get_eid(self, source):
		eids = to_list(self.item.item_metadata['metadata'].get('external-identifier', []))
		for eid in eids:
			# eid sources can contain ':' (e.g. 'spotify:album'), so we have to compare
			# each token except the first ('urn') and the last (the ID number)
			if source.split(':') == eid.split(':')[1:-1]:
				return eid.split(':')[-1]
		return None

	# def get_eid(self, eid_source):
 #        eids = copy(self.item.item_metadata['metadata'].get('external-identifier', []))
 #        eids = eids if isinstance(eids, list) else [eids]
 #        for eid in eids:
 #            if eid.startswith('urn:{}'.format(eid_source)):
 #                return eid.split(':', 2)[-1]
 #        return None



class IATrack(Track):
	def __init__(self, ia_file_md):
		self.source = 'ia_track'
		self.id = ia_file_md['name']
		self.artists = to_list(ia_file_md['artist'])
		self.title = ia_file_md['title']
		self.duration = get_track_duration(ia_file_md)
		self.ordinal = get_track_ordinal(ia_file_md)
		self.derivatives = {}

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

def get_track_duration(ia_file_md):
	""" Get the duration of a track in seconds, given the track's metadata.
	If no valid duration format is present, return zero.
	"""
	if 'length' in ia_file_md:
		# Seconds as a float
		match = re.match('^\d+(\.\d*)?$', ia_file_md['length'])
		if match:
			return float(ia_file_md['length'])
		#TODO: Do durations ever take the form HH:MM:SS?
		# MM:SS
		match = re.match('(\d+):(\d{2})$', ia_file_md['length'])
		if match:
			return 60*float(match.group(1)) + float(match.group(2))
	return 0

def get_track_ordinal(ia_file_md):
	""" Get the ordinal of a track representing its placement on an album, given
	the track's metadata. If no ordering is specified in metadata, use the
	numerals in the track's filename.
	NB: This (usually) gives incorrect results for multidisc items.
	"""
	ordinal = ia_file_md['track'] if 'track' in ia_file_md else ia_file_md['name']
	ordinal = re.sub('[^0-9]+', '', ordinal)
	return int(ordinal) if ordinal else 0