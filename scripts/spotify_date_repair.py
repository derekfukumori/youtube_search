import sys
import arrow
import internetarchive as ia
from metadata import metadata_update

def to_list(x):
	return x if isinstance(x, list) else [x]

item = ia.get_item(sys.argv[-1])
for f in item.files:
	for eid in to_list(f.get('external-identifier', [])):
		if eid.startswith('urn:spotify:'):
			dates = to_list(f.get('external-identifier-match-date', []))
			for date in dates:
				if date.startswith('spotify:'): break
			else:
				dates.insert(0, 'spotify:{}'.format(metadata_update.NOW))
				md = {'external-identifier-match-date': dates}
				print('Writing date to {}/{}'.format(item.identifier, f['name']))
				target = 'files/{}'.format(f['name'])
				metadata_update.write_metadata(item, md, target)