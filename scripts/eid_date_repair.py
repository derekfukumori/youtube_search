import sys
import arrow
import internetarchive as ia
from metadata import metadata_update

# The external-identifier-match-date field was added in June 2018.
# Mark all spotify and youtube matches without a date (i.e. added
# before June 2018) as being from 2018-05-01
DUMMY_DATE = '2018-05-01T00:00:00Z'

def to_list(x):
	return x if isinstance(x, list) else [x]

item = ia.get_item(sys.argv[-1])
for f in item.files:
	file_eid_map = {}
	file_eid_date_map = {}

	if not f.get('external-identifier', None):
		continue

	for e in to_list(f.get('external-identifier', [])):
		src = e.split(':')[1] # source name, without the preceding 'urn:'
		if src in file_eid_map:
			file_eid_map[src].append(e)
		else:
			file_eid_map[src] = [e]
	
	for d in to_list(f.get('external-identifier-match-date', [])):
		src = d.split(':')[0]
		if src in file_eid_date_map:
			file_eid_date_map[src].append(d)
		else:
			file_eid_date_map[src] = [d]

	updated = False
	for src in ['spotify', 'youtube']:
		if src in file_eid_map:
			if src not in file_eid_date_map:
				file_eid_date_map[src] = ['{}:{}'.format(src, DUMMY_DATE)] * len(file_eid_map[src])
				updated = True
			elif len(file_eid_map[src]) > len(file_eid_date_map[src]):
				append = ['{}:{}'.format(src, DUMMY_DATE)] * (len(file_eid_map[src]) - len(file_eid_date_map[src]))
				file_eid_date_map[src] = file_eid_date_map[src] + append
				updated = True

	if updated:
		dates = []
		for src in sorted(list(file_eid_date_map.keys())):
			dates.extend(file_eid_date_map[src])
		md = { 'external-identifier-match-date': dates }
		target = 'files/{}'.format(f['name'])
		metadata_update.write_metadata(item, md, target)
