import sys
import json
import metadata.comparison
from ia.metadata import IAAlbum
from exceptions import *

ALBUM_WEIGHTS = {'artists':         1.0,
				 'title':           1.0,
				 'date':            1.0,
				 'publishers':      1.0,
				 'catalog_numbers': 1.0,
				 'tracks':          3.0,
				 # TODO: Country? Useful for musicbrainz, useless for Spotify
				 # TODO: Format? Useful for musicbrainz, useless for Spotify
				}

TRACK_WEIGHTS = {'artists':  1.0,
				 'title':    1.0,
				 'duration': 1.5,
				 'ordinal':  0.0 # TODO: Fix ordinals for multidisc IA items.
				}

input_dict = json.loads(sys.argv[-1])
for iaid_a in input_dict:
	try:
		ia_album_a = IAAlbum(iaid_a)
	except MetadataException:
		sys.exit(2)
	ia_album_a.title = ia_album_a.tracks[0].metadata['album']
	print(iaid_a)
	for iaid_b in input_dict[iaid_a]:
		try:
			ia_album_b = IAAlbum(iaid_b)
		except MetadataException:
			continue
		ia_album_b.title = ia_album_b.tracks[0].metadata['album']
		print('\t• {}'.format(iaid_b))
		artists_rating = metadata.comparison.get_artists_match_rating(ia_album_a, ia_album_b)
		title_rating = metadata.comparison.get_string_match_rating(ia_album_a.title, ia_album_b.title)
		date_rating = metadata.comparison.get_date_match_rating(ia_album_a.date, ia_album_b.date)
		publishers_rating = metadata.comparison.get_list_match_rating(ia_album_a.publishers, ia_album_b.publishers)
		catalog_numbers_rating = metadata.comparison.get_list_match_rating(ia_album_a.catalog_numbers, ia_album_b.catalog_numbers)
		tracks_rating, track_matches = metadata.comparison.correlate_album_tracks(ia_album_a, ia_album_b, TRACK_WEIGHTS)
		#print('\t\t- Artists: {0:.3f}; A:{1}\tB:{2}'.format(artists_rating, ia_album_a.artists, ia_album_b.artists))
		print('\t\t- Artists: {0:.3f}'.format(artists_rating))
		print('\t\t- Title:   {0:.3f} {1} {2}'.format(title_rating, ia_album_a.title, ia_album_b.title))
		print('\t\t- Date:    {0:.3f}'.format(date_rating))
		print('\t\t- Label:   {0:.3f}'.format(publishers_rating))
		print('\t\t- CatNum:  {0:.3f}'.format(catalog_numbers_rating))
		print('\t\t- Tracks:  {0:.3f}'.format(tracks_rating))



		# ratings = {'artists': get_artists_match_rating(album_a, album_b),
		#    'title': get_string_match_rating(album_a.title, album_b.title),
		#    'date': get_date_match_rating(album_a.date, album_b.date),
		#    'publishers': get_list_match_rating(album_a.publishers, album_b.publishers),
		#    'catalog_numbers': get_list_match_rating(album_a.catalog_numbers, album_b.catalog_numbers),
		#    'tracks': track_correlation_rating
		#  }
