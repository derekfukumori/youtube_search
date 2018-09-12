from spotify.util import nostdout
import audiofp.echoprint as fp
from metadata.music_metadata import Album, Track

def get_artists(sp_md):
	""" Given a Spotify track or album metadata dict (as returned by spotipy), 
		return a list of associated artists. """
	return [a['name'] for a in sp_md['artists']]	

# TODO: Extends Album?
class SpotifyAlbum(Album):
	def __init__(self, spotipy_client, sp_album_md):
		self.spotipy_client = spotipy_client
		self.source = 'spotify:album'
		self.id = sp_album_md.get('id', None)
		self.artists = get_artists(sp_album_md)
		self.title = sp_album_md.get('name', None)
		self.tracks = self.populate_tracks(sp_album_md)
		self.publisher = sp_album_md.get('label', None)
		
	def populate_tracks(self, sp_album_md):
		""" Given a Spotify album metadata dict (as returned by spotipy), return a
		list of SpotifyTrack objects corresponding to the tracks on that album. """
		sp_tracks = []

		# Spotify returns at most 50 tracks at a time; for albums with more
		# than 50 tracks, we have to iterate.
		for _ in range(50):
			with nostdout():
				qr = self.spotipy_client.album_tracks(sp_album_md['id'], offset=len(sp_tracks))
			for sp_track_md in qr['items']:
				sp_tracks.append(SpotifyTrack(self.spotipy_client, sp_track_md))
			if len(sp_tracks) == sp_album_md['total_tracks']:
				break
			elif len(sp_tracks) > sp_album_md['total_tracks']:
				#TODO: more meaningful exception
				raise Exception("Unexpected number of Spotify tracks returned")
		else:
			#TODO: more meaningful exception
			raise Exception('Could not retrieve Spotify tracks')

		# Set the track ordering (see note in SpotifyTrack.__init__).
		for i in range(len(sp_tracks)):
			sp_tracks[i].ordinal = i+1

		return sp_tracks

# TODO: Extends Track?
class SpotifyTrack(Track):
	def __init__(self, spotipy_client, sp_track_md):
		self.spotipy_client = spotipy_client
		self.source = 'spotify:track'
		self.id = sp_track_md.get('id', None)
		self.artists = get_artists(sp_track_md)
		self.title = sp_track_md.get('name', None)
		self.duration = sp_track_md['duration_ms']/1000
		# Ordinal can't be determined from track metadata directly for multidisc
		# albums, so we set the ordinal from SpotifyAlbum.populate_tracks()
		self.ordinal = None
		self.fingerprint = None
		self.fingerprint_attempted = False
	def get_fingerprint(self):
		if self.fingerprint == None and not self.fingerprint_attempted:
			self.fingerprint_attempted = True
			try:
				with nostdout():
					audioanalysis = self.spotipy_client.audio_analysis(self.id)
				# If Spotify returns a series of 5xx errors, spotipy returns None 
				# rather than raising an exception, so we raise one ourselves.
				if audioanalysis == None:
					raise spotipy.client.SpotifyException('5xx', -1, "Unable to retrieve audioanalysis")
			except spotipy.client.SpotifyException as e:
				logger.warning('Warning: unable to retrieve audio analysis for track {}: {}'.format(self.id, e))
				return None
			
			echoprintstring = audioanalysis['track']['echoprintstring']
			if not echoprintstring:
				# Some tracks return an empty audioanalysis object. Treat these cases 
				# as if no audioanalysis object exists.
				logger.warning("Warning: track {} contains empty echoprintstring".format(self.id))
				return None

			self.fingerprint = fp.decode_echoprint_string(echoprintstring)
		return self.fingerprint