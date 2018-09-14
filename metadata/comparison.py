from fuzzywuzzy import fuzz

DEFAULT_ALBUM_WEIGHTS = {'artists':         1.0,
						 'title':           1.0,
						 'date':            0.0,
						 'publishers':      1.0,
						 'catalog_numbers': 1.0,
						 'tracks':          1.0,
						 # TODO: Country? Useful for musicbrainz, useless for Spotify
						 # TODO: Format? Useful for musicbrainz, useless for Spotify
						}

DEFAULT_TRACK_WEIGHTS = {'artists':  1.0,
						 'title':    1.0,
						 'duration': 1.0,
						 'ordinal':  0.0 # TODO: Fix ordinals for multidisc IA items.
						}

def get_weighted_match_rating(match_ratings, weights):
	accum_match_rating = 0
	for field in match_ratings:
		accum_match_rating += match_ratings[field] * weights.get(field, 0)
	weights_sum = sum(list(weights.values()))
	return accum_match_rating/weights_sum

def match_album(album_a, album_b, album_weights=DEFAULT_ALBUM_WEIGHTS, track_weights=DEFAULT_TRACK_WEIGHTS):
	track_correlation_rating, track_matches = correlate_album_tracks(album_a, album_b, track_weights)
	#track_correlation_rating, track_matches = correlate_album_tracks(album_a, album_b)
	ratings = {'artists': get_artists_match_rating(album_a, album_b),
			   'title': get_string_match_rating(album_a.title, album_b.title),
			   'publishers': get_list_match_rating(album_a.publishers, album_b.publishers),
			   'catalog_numbers': get_list_match_rating(album_a.catalog_numbers, album_b.catalog_numbers),
			   'tracks': track_correlation_rating
			  }
	return get_weighted_match_rating(ratings, album_weights), track_matches

def get_track_match_rating(track_a, track_b, track_weights=DEFAULT_TRACK_WEIGHTS):
	ratings = {'artists': get_artists_match_rating(track_a, track_b),
			   'title': get_string_match_rating(track_a.title, track_b.title),
			   'duration': get_track_duration_distance(track_a, track_b),
			   #TODO: Ordinal
			  }
	return get_weighted_match_rating(ratings, track_weights)

def get_string_match_rating(str_a, str_b):
	if not str_a or not str_b: return 0
	return fuzz.token_sort_ratio(str_a, str_b)/100

def get_list_match_rating(list_a, list_b):
	if not list_a or not list_b: return 0
	local_list_a = list(list_a) # Shallow copy for safe list manipulation
	local_list_b = list(list_b) # Shallow copy for safe list manipulation
	accum_match_rating = 0
	for item_a in local_list_a:
		highest_match_rating = 0
		best_match = None
		for item_b in local_list_b:
			match_rating = fuzz.token_sort_ratio(item_a, item_b)/100
			if match_rating > highest_match_rating:
				highest_match_rating = match_rating
				best_match = item_b
		accum_match_rating += highest_match_rating
		local_list_b.remove(best_match)
	norm_match_rating = accum_match_rating/min(len(list_a), len(list_b))
	return norm_match_rating

# TODO: Rename args to reference_album and query_album
def correlate_album_tracks(album_a, album_b, track_weights=DEFAULT_TRACK_WEIGHTS):
	matches = {}
	accum_match_rating = 0

	# TODO: How do we deal with HTOA tracks in archive items?

	tracks_a = list(album_a.tracks) # Shallow copy
	tracks_b = list(album_b.tracks) # Shallow copy

	for track_a in tracks_a:
		highest_match_rating = 0
		best_match = None
		for track_b in tracks_b:
			match_rating = get_track_match_rating(track_a, track_b, track_weights)
			if match_rating > highest_match_rating:
				highest_match_rating = match_rating
				best_match = track_b
				if highest_match_rating > 0.95:
					break
		if best_match:
			accum_match_rating += highest_match_rating
			tracks_b.remove(best_match)
			matches[track_a.id] = track_b.id

	norm_rating = accum_match_rating/len(album_a.tracks)
	return norm_rating, matches

# TODO: This is currently a copy of get_list_match_rating(). Are there cases where
# additional processing needs to be performed for comparisons, or is this redundant?
# TODO: This comparison might have a lot of tricky cases depending on how artists
# are described in metadata in each respective source. This will take some manual
# testing to determine the most common edge cases.
def get_artists_match_rating(a, b):
	a_artists = list(a.artists) # Shallow copy
	b_artists = list(b.artists) # Shallow copy
	accum_match_rating = 0
	for artist_a in a_artists:
		highest_match_rating = 0
		best_match = None
		for artist_b in b_artists:
			match_rating = fuzz.token_sort_ratio(artist_a, artist_b)/100
			if match_rating > highest_match_rating:
				highest_match_rating = match_rating
				best_match = artist_b
		accum_match_rating += highest_match_rating
		b_artists.remove(best_match)
	norm_match_rating = accum_match_rating/min(len(a.artists), len(b.artists))
	return norm_match_rating

# TODO: Rename this, as it returns a match-rating rather than a distance value
def get_track_duration_distance(track_a, track_b):
	if track_a.duration == None or track_b.duration == None:
		return 0
	duration_diff = abs(track_a.duration - track_b.duration)
	return 1 - min(duration_diff/track_a.duration, 1)