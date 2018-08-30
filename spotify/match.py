import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import audiofp.echoprint as fp
import json
import time
import logging
import sys
import contextlib
import io
from exceptions import *

logger = logging.getLogger('spotify-match')
logger.setLevel(logging.WARNING)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('[%(name)s]: %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# Spotipy writes 'retrying...' messages to stdout with no way to suppress
# output, so we suppress manually.
@contextlib.contextmanager
def nostdout():
	save_stdout = sys.stdout
	sys.stdout = io.BytesIO()
	yield
	sys.stdout = save_stdout

def in_duration_range(sp_track, expected_duration, duration_range=20):
    return abs(sp_track['duration_ms']/1000 - expected_duration) < duration_range

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

		query = query_fmt.format(artist = album.artist.lower(),
							 	 title = album.title.lower(),
							 	 creator = album.creator.lower())

		
		with nostdout():
			try:
				r = self.client.search(query, type='album')
			except spotipy.client.SpotifyException:
				# Certain character sequences in queries cause Spotify search to
				# return 404 (e.g. the sequence -?). Pending figuring out all
				# of these sequences, just skip the track.
				logger.warning('Warning: invalid query format: {}'.format(query))
				return {}

		logger.debug('Search returned {} result(s) for query "{}"'.format(len(r['albums']['items']), query))
		
		for sp_album in r['albums']['items']:
			logger.debug('- Matching against: {}'.format(sp_album['uri']))
			logger.debug('\tArtist(s): {}'.format(str.join(', ', [a['name'] for a in sp_album['artists']])))
			logger.debug('\tTitle:     {}'.format(sp_album['name']))

			matches = {}
			sp_tracks = []

			# Spotify returns at most 50 tracks at a time; for albums with more
			# than 50 tracks, we have to iterate.
			for _ in range(50):
				with nostdout():
					qr = self.client.album_tracks(sp_album['id'], offset=len(sp_tracks))
				sp_tracks.extend(qr['items'])
				if len(sp_tracks) == sp_album['total_tracks']:
					break
				elif len(sp_tracks) > sp_album['total_tracks']:
					#TODO: more meaningful exception
					raise Exception("Unexpected number of Spotify tracks returned")
			else:
				#TODO: more meaningful exception
				raise Exception('Could not retrieve Spotify tracks')

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
					try:
						self.ia_fp_cache[ia_track] = fp.generate_fingerprint(dl_path)
					except AudioException:
						# AudioException occurs when echoprint-codegen determines 
						# that the audio file is essentially empty. This is the 
						# case for 'silent' tracks that mask hidden tracks.
						# Don't take these tracks into account when determining
						# an album match.
						logger.warning('Warning: file {}/{} contains invalid audio, skipping.'.format(
										ia_track.parent_album.identifier, ia_track.name))
						continue

				# Cull the comparison set by duration range
				query_tracks = [t for t in sp_tracks if in_duration_range(t, ia_track.duration)]

				matched_track = self.match_against(self.ia_fp_cache[ia_track],
										   		   self.fingerprint_gen(query_tracks),
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
		results = {}
		for ia_track in tracks:
			logger.debug('\t- Matching track: {}'.format(ia_track.name))
			logger.debug('\t\tArtist: {}'.format(ia_track.artist))
			logger.debug('\t\tTitle:  {}'.format(ia_track.title))
			query = query_fmt.format(artist = ia_track.artist.lower(),
							 	 	 title = ia_track.title.lower(),
							 	 	 creator = ia_track.creator.lower())
			
			with nostdout():
				try:
					r = self.client.search(query, type='track', limit=10)
				except spotipy.client.SpotifyException:
					# Certain character sequences in queries cause Spotify search to
					# return 404 (e.g. the sequence -?). Pending figuring out all
					# of these sequences, just skip the track.
					logger.warning('Warning: invalid query format: {}'.format(query))
					continue

			logger.debug('\t\tSearch returned {} result(s) for query "{}"'.format(len(r['tracks']['items']), query))
			sp_tracks = [t for t in r['tracks']['items']]
			# Cull the comparison set by duration range
			query_tracks = [t for t in sp_tracks if in_duration_range(t, ia_track.duration)]
			if not query_tracks:
				continue
			#TODO exceptions
			dl_path = ia_track.download(destdir=self.ia_dir)
			try:
				query_fp = fp.generate_fingerprint(dl_path)
			except AudioException:
				# See AudioException note in spotify.match.match_album
				logger.warning('Warning: file {}/{} contains invalid audio, skipping.'.format(
								ia_track.parent_album.identifier, ia_track.name))
				continue
			matched_track = self.match_against(query_fp, self.fingerprint_gen(query_tracks))

			if matched_track:
				results[ia_track.name] = 'track:{}'.format(matched_track['id'])
		return results

	def match_against(self, query_fp, sp_fp_gen, match_threshold=0.25, short_circuit=True):
		best_match = None
		best_match_rating = 0

		for sp_track, reference_fp in sp_fp_gen:
			if reference_fp == None:
				# reference_fp will be None if we were unable to pull audio analysis
				# for the given Spotify track -- see the note in fingerprint_gen().
				logger.warning('Warning: No fingerprint exists for track {}, skipping.'.format(sp_track['id']))
				continue
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
				try:
					with nostdout():
						audioanalysis =  self.client.audio_analysis(t['id'])

					# If Spotify returns a series of 5xx errors, the Spotipy library
					# returns None rather than raising an exception, so we raise
					# one ourselves.
					if audioanalysis == None:
						raise FingerprintException("5xx error when retrieving audioanalysis.")
					
					echoprintstring = audioanalysis['track']['echoprintstring']

					# Some tracks return an empty audioanalysis object. Treat
					# these cases as if no audioanalysis object exists.
					if not echoprintstring:
						raise FingerprintException("Spotify returned empty audioanalysis object.")

					self.sp_fp_cache[t['id']] = fp.decode_echoprint_string(echoprintstring)
				except (spotipy.client.SpotifyException, FingerprintException) as e:
					# If audio analysis for this track can't be retrieved, 
					# cache the fingerprint as None.
					logger.warning('Warning: unable to retrieve audio analysis for track {}: {}'.format(t['id'], e))
					self.sp_fp_cache[t['id']] = None
			yield t, self.sp_fp_cache[t['id']]
	
	

