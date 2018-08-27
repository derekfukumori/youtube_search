import musicbrainzngs as mb
import json

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
	#"artist-credits",
	#"discids",
	#"isrcs",
	"recording-level-rels",
	#"work-level-rels",
	#"annotation",
	#"aliases",
	#"tags",
	#"user-tags",		# Requires user authentication
	#"area-rels",
	#"artist-rels",
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

mb.set_useragent("Archive.org Audiophile CD Collection",
				 "0.0.1",
				 "derekfukumori@archive.org")

def rate_recording(track, mb_recording):
	pass

def rate_release(album, mb_release):
	print(mb_release)

def get_detailed_release_groups(mb_release_group_query):
	for rg in mb_release_group_query['release-group-list']:
		d = mb.get_release_group_by_id(rg['id'], includes=RELEASE_GROUP_INCLUDES)
		yield d['release-group']

def match_album(album, query_fmt='artist:"{artist}" AND release:"{title}"'):

	#query_fmt = 'artist:"{artist}"'

	query = query_fmt.format(artist = album.artist,
							 title = album.title,
							 creator = album.creator)
	
	print(query)

	print(album.item.item_metadata['metadata'])

	r = mb.search_release_groups(query)

	# NB: The initial release-group query returns a very limited set of information.
	# Here, we retrieve detailed information about a given release group
	# to attempt to determine the release corresponding to the given album.
	# Doing this via a release group resource, rather than retrieving individual
	# releases, allows us to cut down on API calls.
	for release_group in get_detailed_release_groups(r):
		#print(json.dumps(release_group))
		pass

		# release_list = [mb.get_release_by_id(r['id'], includes=RELEASE_INCLUDES)['release']
		# 				for r in release_group['release-list']]

		# #print(release_list)


		# for release in release_list:
		# 	pass#print(json.dumps(release))
	

	# i = musicbrainzngs.get_release_by_id(d['release-group-list'][0]['release-list'][0]['id'], includes=includes)
	# print(json.dumps(d))
	# print(json.dumps(i))


# Album 'distance' or confidence?
# How do we encode confidence when certain metadata fields are missing?
# e.g. how do we treat an item/mbrelease with a UPC match v. without one?
# Should it be composed of track-level matches? Date/publisher/title/artist/etc?
# Compilations?