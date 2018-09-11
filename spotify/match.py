import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import audiofp.echoprint as fp
import json
import time
import logging
import sys
from exceptions import *
from spotify.metadata import *
from spotify.util import nostdout

logger = logging.getLogger('spotify-match')
logger.setLevel(logging.WARNING)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
formatter = logging.Formatter('[%(name)s]: %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def in_duration_range(sp_track, expected_duration, duration_range=20):
    return abs(sp_track.duration - expected_duration) < duration_range

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
							 	 #creator = album.creator.lower()
							 	 )
		
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

		for sp_album_md in r['albums']['items']:
			sp_album = SpotifyAlbum(self.client, sp_album_md)

			logger.debug('- Matching against: {}'.format(sp_album.id))
			logger.debug('\tArtist(s): {}'.format(str.join(', ', sp_album.artists)))
			logger.debug('\tTitle:     {}'.format(sp_album.title))

			matches = {}

			# This is a very imperfect method of preventing singles from matching
			# against full albums. 
			if len(album.tracks) == 1 and len(sp_album.tracks) > 1:
				continue

			sp_tracks = sp_album.tracks

			# To determine a full album match, every track in the item must have
			# a successful fingerprint match.
			for ia_track in album.tracks:
				logger.debug('\t- Matching track: {}'.format(ia_track.name))
				logger.debug('\t\tArtist: {}'.format(ia_track.artist))
				logger.debug('\t\tTitle:  {}'.format(ia_track.title))

				# TODO: Move fingerprinting into IATrack object?
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
										   		   sp_tracks,
										   		   match_threshold=0.15,
										   		   short_circuit=False)
				
				if not matched_track:
					logger.debug('\t\tTrack match failed')
					break
				
				logger.debug('\t\tTrack match successful')

				sp_tracks.remove(matched_track)
				matches[ia_track.name] = 'track:{}'.format(matched_track.id)
			else:
				logger.debug('\tAlbum match sucessful')
				results = {'full_album': 'album:{}'.format(sp_album.id)}
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
							 	 	 title = ia_track.title.lower()
							 	 	# creator = ia_track.creator.lower())
							 	 	)
			
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
			#sp_tracks = [t for t in r['tracks']['items']]

			sp_tracks = [SpotifyTrack(self.client, sp_track_md) for sp_track_md in r['tracks']['items']]

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
			matched_track = self.match_against(query_fp, sp_tracks)

			if matched_track:
				results[ia_track.name] = 'track:{}'.format(matched_track.id)
		return results

	def match_against(self, query_fp, sp_tracks, match_threshold=0.25, short_circuit=True):
		best_match = None
		best_match_rating = 0

		for sp_track in sp_tracks:
			reference_fp = sp_track.get_fingerprint()
			if reference_fp == None:
				# reference_fp will be None if we were unable to pull audio analysis
				# for the given Spotify track -- see the note in spotify.metadata.SpotifyTrack
				logger.warning('Warning: No fingerprint exists for track {}, skipping.'.format(sp_track.id))
				continue
			match_rating = fp.compare_fingerprints(reference_fp, query_fp)
			logger.debug('\t\t- Matching against: {}\tRating: {}'.format(sp_track.id, match_rating))

			if match_rating > best_match_rating:
				best_match = sp_track
				best_match_rating = match_rating
				if short_circuit and best_match_rating > match_threshold: break
		if best_match:
			logger.debug('\t\t- Best match: {}'.format(best_match.id))
			logger.debug('\t\t\tArtist(s): {}'.format(str.join(', ', best_match.artists)))
			logger.debug('\t\t\tTitle:  {}'.format(best_match.title))
			logger.debug('\t\t\tRating: {}'.format(best_match_rating))
		return best_match if best_match_rating > match_threshold else None
