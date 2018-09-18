import sys
import internetarchive as ia
import json
import logging
from exceptions import *
from ia.metadata import IAAlbum
from metadata.comparison import *

collection_id = sys.argv[-2]
iaid = sys.argv[-1]
try:
	ia_album = IAAlbum(iaid)
except MetadataException:
	sys.exit(1)

if 'album' in ia_album.tracks[0].metadata:
	ia_album_title = ia_album.tracks[0].metadata['album']
else:
	sys.exit(2)

results = {ia_album.id: []}

query = 'collection:{} AND creator:"{}" AND title:"{}"'.format(collection_id, ia_album.artists[0], ia_album_title)

s = ia.search_items(query, params={'scope':'all'})

for r in s.iter_as_results():
	results[ia_album.id].append(r['identifier'])

if results[ia_album.id]:
	print(json.dumps(results))