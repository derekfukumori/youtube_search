from metadata.music_metadata import Album, Track

class MusicBrainzRelease(Album):
	def __init__(self, mb_release_md):
		self.source = 'mb_release_id'
		self.id = mb_release_md['id']
		self.artists = [a['artist']['name'] for a in mb_release_md['artist-credit']]
		self.title = mb_release_md['title']
		# TODO: What are the cases for more than one publisher, and are they useful/important?
		self.publisher = mb_release_md['label-info-list'][0]['label']['name']
		self.date = mb_release_md.get('date', None)
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


class MusicBrainzRecording(Track):
	def __init__(self, mb_recording_md):
		self.source = 'mb_recording_id'
		self.id = mb_recording_md['id']
		self.artists = [a['artist']['name'] for a in mb_recording_md['artist-credit']]
		self.title = mb_recording_md['title']
		self.duration = int(mb_recording_md['length'])/1000 if 'length' in mb_recording_md else None
		# Ordinal can't be determined from recording metadata directly, so we set
		# the ordinal from MusicBrainzRelease.populate_tracks()
		self.ordinal = None