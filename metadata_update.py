import sys
import logging
from time import sleep
from copy import copy

import ujson as json
from internetarchive import get_item
import arrow
from ytsearch.exceptions import *

logger = logging.getLogger("metadata_update")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

NOW = '{}Z'.format(arrow.now().isoformat().split('.')[0])


def write_metadata(item, md, target='metadata'):
	retries = 50
	while retries > 0:
		retries -= 1
		r = item.modify_metadata(md, target=target)
		if r.ok:
			logger.info('Success: {}/{} updated.'.format(item.identifier, target))
			return True
		elif 'no changes' in r.text:
			logger.info('{}/{} already updated, skipped.'.format(item.identifier, 
																target))
			return False
		elif 'no file entry of that name found' in r.text:
			logger.warning('{}/{} does not exist, skipped.'.format(item.identifer,
																   target))
			return False
		else:
			logger.warning('{}/{} failed, retrying. {} retries left.'.format(
				item.identifier, target, retries))
			sleep(1)

	logger.error('{}/{} failed to update - {}'.format(item.identifier, target,
													  r.content))
	raise MetadataUpdateError('{}/{}'.format(item.identifier, target))


def contains_match(files_map):
	for f in files_map:
		if files_map[f]:
			return True
	return False

def update_metadata(results_map):
	for iaid, files_map in results_map.items():
		if not contains_match(files_map):
			continue

		item = get_item(iaid)
		if item.item_metadata.get('is_dark', False):
			logger.warning('Skipping darked item {}.'.format(item.identifier))
			continue

		matches = False
			
		# Update file metadata
		for f in files_map:
			if not files_map[f] or f == 'full_album':
				continue

			logger.debug('Updating {}/{}...'.format(item.identifier, f))

			file_eid = copy(
				item.get_file(f).__dict__.get('external-identifier', list()))
			if not isinstance(file_eid, list):
				file_eid = [file_eid]

			file_eid_match_date = copy(
				item.get_file(f).__dict__.get('external-identifier-match-date', list()))
			if not isinstance(file_eid_match_date, list):
				file_eid_match_date = [file_eid_match_date]

			matched_file_eid = 'urn:youtube:{}'.format(files_map[f])
			if matched_file_eid in file_eid:
				logger.debug('{}/{} already in metadata.'.format(item.identifier, f))
				#continue

			file_eid.append(matched_file_eid)
			file_eid = list(set(file_eid))

			file_eid_match_date = [x for x in file_eid_match_date if not x.startswith('youtube')]
			file_eid_match_date.append('youtube:{}'.format(NOW))

			file_md = {
					'external-identifier': file_eid,
					'external-identifier-match-date': file_eid_match_date,
			}
			if write_metadata(item, file_md, 'files/{}'.format(f)):
				matches = True

		# Update item metadata
		item_md = dict()
		if 'full_album' in files_map:
			matched_item_eid = 'urn:youtube:{}'.format(
									files_map['full_album'].split('&t=', 1)[0])
			item_eid = copy(item.metadata.get('external-identifier', list()))
			if not isinstance(item_eid, list):
				item_eid = [item_eid]
			if matched_item_eid not in item_eid:
				item_eid.append(matched_item_eid)
				item_md['external-identifier'] = item_eid
				matches = True
		
		if matches:
			item_md['external_metadata_update'] = NOW
			write_metadata(item, item_md)


if __name__ == '__main__':
	j = json.loads(sys.argv[-1])
	update_metadata(j)