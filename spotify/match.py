import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import audiofp.echoprint as fp
import json
import time
import logging

logger = logging.getLogger('spotify-match')
logger.setLevel(logging.WARNING)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('[%(name)s]: %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class SpotifyMatcher:
	def __init__(self, credentials, ia_dir='.'):
		self.client = spotipy.Spotify(client_credentials_manager=credentials)
		self.ia_dir = ia_dir
		self.sp_fp_cache = {}
		self.ia_fp_cache = {}

	def match_album(self, album, query_fmt='{artist} {title}'):
		logger.debug('- Matching album: {}'.format(album.identifier))
		logger.debug('\tArtist: {}'.format(album.artist))
		logger.debug('\tTitle:  {}'.format(album.title))

		query = query_fmt.format(artist = album.artist,
							 	 title = album.title,
							 	 creator = album.creator)
		r = self.client.search(query, type='album')

		logger.debug('Search returned {} result(s) for query "{}"'.format(len(r['albums']['items']), query))
		
		for sp_album in r['albums']['items']:
			logger.debug('- Matching against: {}'.format(sp_album['uri']))
			logger.debug('\tArtist(s): {}'.format(str.join(', ', [a['name'] for a in sp_album['artists']])))
			logger.debug('\tTitle:     {}'.format(sp_album['name']))

			matches = {}
			sp_tracks = [t for t in self.client.album_tracks(sp_album['id'])['items']]

			# This is a very imperfect method of preventing singles from matching
			# against full albums. 
			if len(album.tracks) == 1 and len(sp_tracks) > 1:
				continue

			# To determine a full album match, every track in the item must have
			# a successful fingerprint match.
			for ia_track in album.tracks:
				logger.debug('\t- Matching track: {}'.format(ia_track.name))
				logger.debug('\t\tArtist: {}'.format(ia_track.artist))
				logger.debug('\t\tTitle:  {}'.format(ia_track.title))
				if ia_track not in self.ia_fp_cache:
					#TODO exceptions
					dl_path = ia_track.download(destdir=self.ia_dir)
					self.ia_fp_cache[ia_track] = fp.generate_fingerprint(dl_path)
				
				matched_track = self.match_against(self.ia_fp_cache[ia_track],
										   		   self.fingerprint_gen(sp_tracks),
										   		   match_threshold=0.15,
										   		   short_circuit=False)
				
				if not matched_track:
					logger.debug('\t\tTrack match failed')
					break
				
				logger.debug('\t\tTrack match successful')

				sp_tracks.remove(matched_track)
				matches[ia_track.name] = 'track:{}'.format(matched_track['id'])
			else:
				logger.debug('\tAlbum match sucessful')
				results = {'full_album': 'album:{}'.format(sp_album['id'])}
				results.update(matches)
				return results
			logger.debug('\tAlbum match failed')
		return {}

	def match_tracks(self, tracks, album, query_fmt='{artist} {title}'):
		logger.debug('- Matching individual tracks')
		results ={}
		for ia_track in tracks:
			logger.debug('\t- Matching track: {}'.format(ia_track.name))
			logger.debug('\t\tArtist: {}'.format(ia_track.artist))
			logger.debug('\t\tTitle:  {}'.format(ia_track.title))
			query = query_fmt.format(artist = ia_track.artist,
							 	 	 title = ia_track.title,
							 	 	 creator = ia_track.creator)
			r = self.client.search(query, type='track', limit=10)
			logger.debug('\t\tSearch returned {} result(s) for query "{}"'.format(len(r['tracks']['items']), query))
			sp_tracks = [t for t in r['tracks']['items']]
			#TODO exceptions
			dl_path = ia_track.download(destdir=self.ia_dir)
			query_fp = fp.generate_fingerprint(dl_path)
			matched_track = self.match_against(query_fp, self.fingerprint_gen(sp_tracks))
			if matched_track:
				results[ia_track.name] = 'track:{}'.format(matched_track['id'])
		return results

	def match_against(self, query_fp, sp_fp_gen, match_threshold=0.25, short_circuit=True):
		best_match = None
		best_match_rating = 0

		for sp_track, reference_fp in sp_fp_gen:
			match_rating = fp.compare_fingerprints(reference_fp, query_fp)
			#logger.debug('\t\t- Matching against: {}\tRating: {}'.format(sp_track['uri'], match_rating))

			if match_rating > best_match_rating:
				best_match = sp_track
				best_match_rating = match_rating
				if short_circuit and best_match_rating > match_threshold: break
		if best_match:
			logger.debug('\t\t- Best match: {}'.format(best_match['uri']))
			logger.debug('\t\t\tArtist(s): {}'.format(str.join(', ', [a['name'] for a in best_match['artists']])))
			logger.debug('\t\t\tTitle:  {}'.format(best_match['name']))
			logger.debug('\t\t\tRating: {}'.format(best_match_rating))
		return best_match if best_match_rating > match_threshold else None

	def fingerprint_gen(self, sp_tracks):
		for t in sp_tracks:
			#TODO: exceptions
			if t['id'] not in self.sp_fp_cache:
				self.sp_fp_cache[t['id']] = self.client.audio_analysis(t['id'])['track']['echoprintstring']
			yield t, self.sp_fp_cache[t['id']]

	# def get_spotify_fingerprint_map(self, sp_tracks):
	# 	fp_map = {}
	# 	for t in sp_tracks:
	# 		#try:
	# 		fp_map[t['id']] = self.client.audio_analysis(t['id'])['track']['echoprintstring']
	# 		#except
	# 	return fp_map
	
	

