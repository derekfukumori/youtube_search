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

for track in album.tracks:
	dl_path = track.download(dest_dir='tmp/htoa')
	try:
		generate_fingerprint(dl_path)
	except AudioException:
		print(track.name)

