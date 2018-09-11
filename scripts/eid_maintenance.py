import sys
import arrow
import internetarchive as ia
from metadata import metadata_update
from metadata.util import *

# The external-identifier-match-date field was added in June 2018.
# Mark all spotify and youtube matches without a date (i.e. added
# before June 2018) as being from 2018-05-01
DUMMY_DATE = '2018-05-01T00:00:00Z'

# This represents the list of eid sources that this script is intended to handle,
# which currently includes the following:
# 	- mb_recording_id
#	- mb_releasegroup_id
#	- spotify
#	- youtube
# Any eids corresponding to the following sources will have missing match-dates
# filled in with dummy dates, the value of which is the addeddate of the respective
# item. eids and eid match dates will also be ordered according to the scheme
# documented in metadata_update.py. 
handled_sources = list(metadata_update.source_validators.keys())

item = ia.get_item(sys.argv[-1])

DUMMY_DATE = item.item_metadata['metadata']['addeddate']
print(DUMMY_DATE)


for f in item.files:

	if not f.get('external-identifier', None):
		continue

	file_eid_map = get_eid_map(item, f['name'])
	file_eid_date_map = get_eid_date_map(item, f['name'])

	for source in handled_sources:
		if source in file_eid_map:
			if source not in file_eid_date_map:
				pass

	# updated = False
	# for src in ['spotify', 'youtube']:
	# 	if src in file_eid_map:
	# 		if src not in file_eid_date_map:
	# 			file_eid_date_map[src] = ['{}:{}'.format(src, DUMMY_DATE)] * len(file_eid_map[src])
	# 			updated = True
	# 		elif len(file_eid_map[src]) > len(file_eid_date_map[src]):
	# 			append = ['{}:{}'.format(src, DUMMY_DATE)] * (len(file_eid_map[src]) - len(file_eid_date_map[src]))
	# 			file_eid_date_map[src] = file_eid_date_map[src] + append
	# 			updated = True

	# if updated:
	# 	dates = []
	# 	for src in sorted(list(file_eid_date_map.keys())):
	# 		dates.extend(file_eid_date_map[src])
	# 	md = { 'external-identifier-match-date': dates }
	# 	target = 'files/{}'.format(f['name'])
	# 	metadata_update.write_metadata(item, md, target)
