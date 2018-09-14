from metadata.music_metadata import Album, Track

def get_artists(mb_md):
	# MusicBrainz artist-credit lists are sometimes structured as e.g. 
	# [{artist-object}, 'feat.', {artist-object}, ...], so we skip over 
	# any list members that are strings rather than dicts.
	return [a['artist']['name'] for a in mb_md['artist-credit'] if not isinstance(a, str)]

# TODO: Return catalog number as well?
def get_publishers(mb_release_md):
	# TODO: What are the cases for more than one publisher, and are they useful/important?
	for mb_label_md in mb_release_md.get('label-info-list', []):
		if 'label' in mb_label_md:
			return mb_label_md['label']
	return None

class MusicBrainzRelease(Album):
	def __init__(self, mb_release_md):
		self.source = 'mb_release_id'
		self.id = mb_release_md['id']
		self.artists = get_artists(mb_release_md)
		self.title = mb_release_md['title']
		self.date = mb_release_md.get('date', None)
		self.publishers = []
		self.catalog_numbers = []
		self.populate_publishers_and_catalog_numbers(mb_release_md)
		# NB: This is a list of MusicBrainzRecording objects, whose IDs are
		# MusicBrainz recording IDs. MusicBrainz also has a 'track' structure,
		# corresponding to a recording's position on a particular release. Despite
		# the nomenclature, the 'track' structure isn't used here (yet).
		self.tracks = []
		self.populate_tracks(mb_release_md)
	def populate_tracks(self, mb_release_md):
		for mb_medium_md in mb_release_md['medium-list']:
			for mb_track_md in mb_medium_md['track-list']:
				self.tracks.append(MusicBrainzRecording(mb_track_md['recording']))
		for i in range(len(self.tracks)):
			self.tracks[i].ordinal = i+1
	def populate_publishers_and_catalog_numbers(self, mb_release_md):
		for mb_label_info_md in mb_release_md.get('label-info-list', []):
			if 'label' in mb_label_info_md:
				self.publishers.append(mb_label_info_md['label']['name'])
			if 'catalog-number' in mb_label_info_md:
				self.catalog_numbers.append(mb_label_info_md['catalog-number'])

class MusicBrainzRecording(Track):
	def __init__(self, mb_recording_md):
		self.source = 'mb_recording_id'
		self.id = mb_recording_md['id']
		self.artists = get_artists(mb_recording_md)
		self.title = mb_recording_md['title']
		self.duration = int(mb_recording_md['length'])/1000 if 'length' in mb_recording_md else None
		# Ordinal can't be determined from recording metadata directly, so we set
		# the ordinal from MusicBrainzRelease.populate_tracks()
		self.ordinal = None