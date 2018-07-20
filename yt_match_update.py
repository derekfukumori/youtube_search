import sys
from time import sleep
from copy import copy

import ujson as json
from internetarchive import get_item
import arrow


NOW = '{}Z'.format(arrow.now().isoformat().split('.')[0])


def update_metadata(item, md, target='metadata'):
	retries = 50
	while retries > 0:
		retries -= 1
		r = item.modify_metadata(md, target=target)
		if r.ok:
			print('success: {}/{} updated.'.format(item.identifier, target))
			return r
		elif 'no changes' in r.text:
			print('success: {}/{} already updated, skipped.'.format(item.identifier,
																	target))
			return r
		elif 'no file entry of that name found' in r.text:
			print('warning: {}/{} does not exist, skipped.'.format(item.identifier,
																	target))
			return r
		else:
			print('warning: {}/{} failed, retrying. {} retries left.'.format(
				  item.identifier, target, retries))
			sleep(1)

	print('error: {}/{} failed to update - {}'.format(item.identifier, target, r.content))


if __name__ == '__main__':
	j = json.loads(sys.argv[-1])
	identifier = list(j.keys())[0]

	item_eid = None
	item = None
	files = j[identifier]
	matches = False

	for f in files:
		file_eid = None

		if not files[f]:
			continue

		# Album match.
		if f == 'full_album':
			item_eid = 'urn:youtube:{}'.format(files[f].split('&t=', 1)[0])
			continue

		if item is None:
			item = get_item(identifier)
			if item.item_metadata.get('is_dark', False):
				print('warning: skipping darked item {}.'.format(item.identifier))
				sys.exit(0)

		file_eid = copy(
				item.get_file(f).__dict__.get('external-identifier', list()))
		if not isinstance(file_eid, list):
			file_eid = [file_eid]

		file_eid_match_date = copy(
				item.get_file(f).__dict__.get('external-identifier-match-date', list()))
		if not isinstance(file_eid_match_date, list):
			file_eid_match_date = [file_eid_match_date]

		feid = 'urn:youtube:{}'.format(files[f])
		# Don't update if it's already in there.
		# This prevents match-date from updating, too.
		if feid in file_eid:
			continue

		file_eid.append(feid)
		file_eid = list(set(file_eid))
		target = 'files/{}'.format(f)
		file_eid_match_date = [x for x in file_eid_match_date if not x.startswith('youtube')]
		file_eid_match_date.append('youtube:{}'.format(NOW))
		fmd = {
				'external-identifier': file_eid,
				'external-identifier-match-date': file_eid_match_date,
		}

		# Update file eid.
		r = update_metadata(item, fmd, target)
		if r is None:
			sys.exit(1)
		matches = True

	# if item is None, no matches. Exit.
	if item is None:
		sys.exit(0)

	md = dict()
	# Update eid if there was an album match.
	existing_item_eid = copy(item.metadata.get('external-identifier', list()))
	if not isinstance(existing_item_eid, list):
		existing_item_eid = [existing_item_eid]
	if item_eid and item_eid not in existing_item_eid:
		existing_item_eid.append(item_eid)
		md['external-identifier'] = existing_item_eid
		matches = True

	if matches is True:
		md['external_metadata_update'] = NOW

	# Only update external_metadata_update if item was updated.
	if [k for k in md if k != 'external_metadata_update'] or matches is True:
		r = update_metadata(item, md)
		if not r:
			sys.exit(1)