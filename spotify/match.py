import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import audiofp.echoprint as fp
import json
import time

class SpotifyMatcher:
	def __init__(self, credentials, ia_dir='.'):
		self.client = spotipy.Spotify(client_credentials_manager=credentials)
		self.ia_dir = ia_dir

	def match_album(self, album, query_fmt='{artist} {title}'):
		query = query_fmt.format(artist = album.artist,
							 	 title = album.title,
							 	 creator = album.creator)
		r = self.client.search(query, type='album')

		ia_fp_map = {}
		
		for sp_album in r['albums']['items']:
			matches = {}
			sp_track_ids = [t['id'] for t in self.client.album_tracks(sp_album['id'])['items']]

			# This is a very imperfect method of preventing singles from matching
			# against full albums. 
			if len(album.tracks) == 1 and len(sp_tracks) > 1:
				continue

			# To determine a full album match, every track in the item must have
			# a successful fingerprint match.
			for t in album.tracks:
				if not t in ia_fp_map:
					#TODO exceptions
					ia_fp_map[t] = fp.generate_fingerprint(t.download(destdir=self.ia_dir))
				
				match = self.match_against(ia_fp_map[t], self.fingerprint_gen(sp_track_ids),
										   match_threshold=0.2)
				
				if not match:
					break
				
				sp_track_ids.remove(match)
				matches[t.name] = 'track:{}'.format(match)
			else:
				results = {'full_album': 'album:{}'.format(sp_album['id'])}
				results.update(matches)
				return results
		return {}

	def match_tracks(self, tracks, album, query_fmt='{artist} {title}'):
		results ={}
		for track in tracks:
			query = query_fmt.format(artist = track.artist,
							 	 	 title = track.title,
							 	 	 creator = track.creator)
			r = self.client.search(query, type='track', limit=10)
			sp_track_ids = [t['id'] for t in r['tracks']['items']]
			#TODO exceptions
			query_fp = fp.generate_fingerprint(track.download(destdir=self.ia_dir))
			match = self.match_against(query_fp, self.fingerprint_gen(sp_track_ids))
			if match:
				results[track.name] = 'track:{}'.format(match)
		return results

	def match_against(self, query_fp, sp_fp_gen, match_threshold=0.25):
		for track_id, reference_fp in sp_fp_gen:
			if fp.match_fingerprints(reference_fp, query_fp, 
									 match_threshold=match_threshold):
				return track_id
		return None

	def get_spotify_fingerprint_map(self, sp_tracks):
		fp_map = {}
		for t in sp_tracks:
			#try:
			fp_map[t['id']] = self.client.audio_analysis(t['id'])['track']['echoprintstring']
			#except
		return fp_map
	
	def fingerprint_gen(self, sp_track_ids):
		for t in sp_track_ids:
			#TODO: exceptions
			yield t, self.client.audio_analysis(t)['track']['echoprintstring']

