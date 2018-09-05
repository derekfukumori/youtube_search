import sys
import internetarchive as ia
from metadata.music_metadata import *
from exceptions import *
from audiofp.echoprint import generate_fingerprint

iaid = sys.argv[-1]
try:
	album = IAAlbum(iaid)
except MetadataException:
	sys.exit(0)

htoa_present = False
silence_present = False
for track in album.tracks:
	lct = track.title.lower()
	if 'hidden track one audio' in lct:
		dl_path = track.download('tmp/silence_test')
		try:
			generate_fingerprint(dl_path)
		except AudioException:
			htoa_present = True
			continue
	if not silence_present and ('silence' in lct or 'untitled' in lct):
		dl_path = track.download('tmp/silence_test')
		try:
			generate_fingerprint(dl_path)
		except AudioException:
			silence_present = True
if htoa_present: print('htoa:{}'.format(iaid))
if silence_present: print('silence:{}'.format(iaid))

