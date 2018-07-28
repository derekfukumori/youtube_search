import sys
import logging
from time import sleep
from copy import copy
import re
import ujson as json
from internetarchive import get_item
import arrow
from ytsearch.exceptions import *

logger = logging.getLogger("metadata_update")
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)



# Note: YouTube does not have a strict definition of video id formatting.
# Currently, it's 11 characters long, consisting of alphanumeric characters,
# as well as '-' and '_'. If this changes in the future, this pattern will
# need to change to accommodate.
YOUTUBE_RE = re.compile('[a-zA-Z0-9\-\_]{11}(&t=\d+)?')
SPOTIFY_RE = re.compile('[a-zA-Z0-9]{22}')

NOW = '{}Z'.format(arrow.now().isoformat().split('.')[0])


def verify_youtube_id(eid):
	return YOUTUBE_RE.fullmatch(eid)

def verify_spotify_id(eid):
	return SPOTIFY_RE.fullmatch(eid)

source_validators = {'youtube':verify_youtube_id, 'spotify':verify_spotify_id}

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

def to_list(eid):
	return eid if isinstance(eid, list) else [eid]

def get_updated_file_metadata(filename, matched_eids, item):
	file_eid = to_list(copy(item.get_file(filename).__dict__.get('external-identifier', list())))
	file_eid_match_date = to_list(copy(item.get_file(filename).__dict__.get( 'external-identifier-match-date', list())))
	updated = False
	for source, eid in matched_eids.items():
		# Validate that this is a supported external source
		if not source in source_validators:
			raise MetadataError('Invalid external source \'{}\' provided by {}/{}'.format(
								source, item.identifier, filename))
		# Validate the identifier format for the given external source
		if not source_validators[source](eid):
			raise MetadataError('Invalid ID \'{}:{}\' provided by {}/{}'.format(
								source, eid, item.identifier, filename))

		#TODO: Ask Jake whether multiple eids for the same source is intentional


		matched_eid = 'urn:{}:{}'.format(source, eid)

		if matched_eid in file_eid:
			continue

		file_eid.append(matched_eid)
		file_eid = list(set(file_eid)) # Remove duplicates
		file_eid_match_date = [x for x in file_eid_match_date if not x.startswith(source)]
		file_eid_match_date.append('{}:{}'.format(source, NOW))
		updated = True
	if updated:
		return { 'external-identifier': file_eid,
				 'external-identifier-match-date': file_eid_match_date }
	return None

def get_updated_item_metadata(matched_eids, item):
	item_md = dict()
	item_eid = to_list(copy(item.metadata.get('external-identifier', list())))
	for source, eid in matched_eids.items():
		matched_eid = 'urn:{}:{}'.format(source, eid)
		if matched_eid in item_eid:
			continue
		item_eid.append(matched_eid)
		item_eid = list(set(item_eid)) # Remove duplicates
		item_md['external-identifier'] = item_eid
	item_md['external_metadata_update'] = NOW
	return item_md

def update_metadata(results_map):
	for iaid, files_map in results_map.items():
		if not contains_match(files_map):
			continue
		item = get_item(iaid)
		if item.item_metadata.get('is_dark', False):
			logger.warning('Skipping darked item {}.'.format(item.identifier))
			continue

		files_updated = False

		for f in files_map:
			if not files_map[f] or f == 'full_album':
				continue

			file_md = get_updated_file_metadata(f, files_map[f], item)
			if not file_md:
				continue

			if write_metadata(item, file_md, 'files/{}'.format(f)):
				files_updated = True

		item_md = get_updated_item_metadata(files_map.get('full_album', dict()), item)

		if files_updated or 'external-identifier' in item_md:
			write_metadata(item, item_md)

if __name__ == '__main__':
	j = json.loads(sys.argv[-1])
	update_metadata(j)