import sys
import json

with open(sys.argv[1]) as f:
	lines = f.readlines()


total_tracks = 0
total_items = 0

sp_track_matches = 0
sp_full_matches = 0
sp_partial_matches = 0
sp_item_level_matches = 0

yt_track_matches = 0
yt_partial_matches = 0
yt_full_matches = 0
yt_item_level_matches = 0


for l in lines:
	if not l.startswith('{'): continue
	d = json.loads(l)
	for iaid, tracks in d.items():
		total_items += 1

		sp_fully_matched = True
		sp_partially_matched = False
		yt_fully_matched = True
		yt_partially_matched = False

		for name, matches in tracks.items():
			if name != 'full_album':
				total_tracks += 1
				
				if 'spotify' in matches:
					sp_track_matches += 1
					sp_partially_matched = True
				else:
					sp_fully_matched = False

				if 'youtube' in matches:
					yt_track_matches += 1
					yt_partially_matched = True
				else:
					yt_fully_matched = False

			else:
				if 'spotify' in matches:
					sp_item_level_matches += 1
				if 'youtube' in matches:
					yt_item_level_matches += 1
		if sp_fully_matched:
			sp_full_matches += 1
		elif sp_partially_matched:
			sp_partial_matches += 1

		if yt_fully_matched:
			yt_full_matches += 1
		elif yt_partially_matched:
			yt_partial_matches += 1

print("Youtube:")
print("Matched {} of {} tracks ({:.02f}%)".format(yt_track_matches, total_tracks, 100*yt_track_matches/total_tracks))
print("Fully matched {} of {} items ({:.02f}%)".format(yt_full_matches, total_items, 100*yt_full_matches/total_items))
print("Partially matched {} of {} items ({:.02f}%)".format(yt_partial_matches, total_items, 100*yt_partial_matches/total_items))
print("Found {} item-level-matches ({:.02f}%)".format(yt_item_level_matches, 100*yt_item_level_matches/total_items))
print()
print('Spotify')
print("Matched {} of {} tracks ({:.02f}%)".format(sp_track_matches, total_tracks, 100*sp_track_matches/total_tracks))
print("Fully matched {} of {} items ({:.02f}%)".format(sp_full_matches, total_items, 100*sp_full_matches/total_items))
print("Partially matched {} of {} items ({:.02f}%)".format(sp_partial_matches, total_items, 100*sp_partial_matches/total_items))
print("Found {} item-level matches ({:.02f}%)".format(sp_item_level_matches, 100*sp_item_level_matches/total_items))