import musicbrainzngs as mb
from musicbrainz.metadata import *
import json
import metadata.comparison
from fuzzywuzzy import fuzz
from exceptions import *

RELEASE_GROUP_INCLUDES = [
	"artists",
	"releases",
	"discids",
	"media",
	"artist-credits",
	#"annotation",
	#"aliases",
	#"tags",
	#"user-tags",		# Requires user authentication
	#"ratings",
	#"user-ratings",	# Requires user authentication
	"area-rels",
	"artist-rels",
	"label-rels",
	"place-rels",
	"event-rels",
	"recording-rels",
	"release-rels",
	"release-group-rels",
	"series-rels",
	"url-rels",
	"work-rels",
	"instrument-rels"
]

RELEASE_INCLUDES = [
	"artists",
	"labels",
	"recordings",
	"release-groups",
	#"media",
	"artist-credits",
	#"discids",
	#"isrcs",
	"recording-level-rels",
	#"work-level-rels",
	#"annotation",
	#"aliases",
	#"tags",
	#"user-tags",		# Requires user authentication
	#"area-rels",
	"artist-rels",
	#"label-rels",
	#"place-rels",
	#"event-rels",
	"recording-rels",
	#"release-rels",
	#"release-group-rels",
	#"series-rels",
	"url-rels",
	#"work-rels",
	#"instrument-rels",
]

# TODO: Handle rate-limiting (will likely have to wrap all musicbrainz calls -- contextlib?)

mb.set_useragent("Archive.org Audiophile CD Collection",
				 "0.0.1",
				 "derekfukumori@archive.org")

def generate_release_groups(mb_release_group_query):
	for rg in mb_release_group_query['release-group-list']:
		d = mb.get_release_group_by_id(rg['id'], includes=RELEASE_GROUP_INCLUDES)
		yield d['release-group']

def generate_releases(mb_release_group):
	pass

def upc_match(ia_album, mb_release_group):
	upc = ia_album.get_eid('upc')
	if not upc: return None
	for release in mb_release_group['release-list']:
		if upc == release.get('barcode', None): return release['id']
	return None

def correlate_tracks(ia_album, mb_release):
	#TODO: Create a class for this?
	results = {}
	accum_rating = 0
	mb_tracks = []
	for mb_medium in mb_release['medium-list']:
		for mb_track in mb_medium['track-list']:
			mb_tracks.append(mb_track)

	# TODO: Is skipping HTOA tracks always the best policy? (Probably)
	ia_tracks = [t for t in ia_album.tracks if t.title != "Hidden Track One Audio"]

	for ia_track in ia_tracks:
		
		highest_match_rating = 0
		matched_track = None
		
		for mb_track in mb_tracks:
			match_rating = get_track_match_rating(ia_track, mb_track)
			if match_rating > highest_match_rating:
				highest_match_rating = match_rating
				matched_track = mb_track
				if highest_match_rating > 0.95: #Is 0.95 strict/loose enough?
					break
		if matched_track:
			accum_rating += highest_match_rating
			mb_tracks.remove(matched_track)
			#print(matched_track['recording']['id'])
			results[ia_track.id] = matched_track['recording']['id']

	norm_rating = accum_rating/len(ia_tracks)
	return norm_rating, results

def get_track_match_rating(ia_track, mb_track):
	mb_recording = mb_track['recording']
	#TODO: Weighting?
	rating = fuzz.token_sort_ratio(ia_track.title, mb_recording['title'])/100
	rating *= get_track_duration_distance(ia_track, mb_track)
	# TODO: Consider tracklist position. A musicbrainz track has two fields for
	# this, 'position' and 'number'. One probably represents the position on that
	# particular CD/LP (relevant for multidisc albums), and the other the position
	# in the work as a whole. figure out what makes sense for how IA metadata
	# is structured (if there is a uniform structure...)
	return rating

def get_track_duration_distance(ia_track, mb_track):
	mb_track_duration = int(mb_track['recording']['length'])/1000
	duration_diff = abs(ia_track.duration - mb_track_duration)
	return 1 - min(duration_diff/ia_track.duration, 1)


def match_album(ia_album, query_fmt='artist:"{artist}" AND release:"{title}"'):
	# TODO: Support queries for albums with multiple artists
	query = query_fmt.format(artist = ia_album.artists[0],
							 title = ia_album.title)

	r = mb.search_release_groups(query)

	# NB: The initial release-group query returns a very limited set of information.
	# Here, we retrieve detailed information about a given release group
	# to attempt to determine the release corresponding to the given album.
	# Doing this via a release group resource, rather than retrieving individual
	# releases, allows us to cut down on API calls.
	for mb_releasegroup_md in generate_release_groups(r):

		# Attempt to match by UPC first
		mb_release_upcmatch_id = upc_match(ia_album, mb_releasegroup_md)

		if mb_release_upcmatch_id:
			mb_release_md = mb.get_release_by_id(mb_release_upcmatch_id, includes=RELEASE_INCLUDES)['release']
			mb_release = MusicBrainzRelease(mb_release_md)
			rating, matches = metadata.comparison.match_album(ia_album, mb_release)
			if rating >= 0.9: #TODO: Too strict/loose?
				matches['full_album'] = mb_releasegroup_md['id']
				return matches

		# If no UPC match exists, iterate through releases and find the best.
		mb_release_ids = [mbr['id'] for mbr in mb_releasegroup_md.get('release-list', [])
						  if mbr['id'] != mb_release_upcmatch_id]

		for mb_release_id in mb_release_ids:
			mb_release_md = mb.get_release_by_id(mb_release_id, includes=RELEASE_INCLUDES)['release']
			mb_release = MusicBrainzRelease(mb_release_md)
			rating, matches = metadata.comparison.match_album(ia_album, mb_release)
			if rating >= 0.95: #TODO: Too strict/loose?
				matches['full_album'] = mb_releasegroup_md['id']
				return matches

	return {}

	# i = musicbrainzngs.get_release_by_id(d['release-group-list'][0]['release-list'][0]['id'], includes=includes)
	# print(json.dumps(d))
	# print(json.dumps(i))


# Album 'distance' or confidence?
# How do we encode confidence when certain metadata fields are missing?
# e.g. how do we treat an item/mbrelease with a UPC match v. without one?
# Should it be composed of track-level matches? Date/publisher/title/artist/etc?
# Compilations?