import sys
import logging
from time import sleep
from copy import copy
import re
import ujson as json
from internetarchive import get_item
import arrow
from metadata.util import *
from exceptions import *

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
SPOTIFY_RE = re.compile('(track|album):[a-zA-Z0-9]{22}')
MUSICBRAINZ_RE = re.compile('[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}')

NOW = '{}Z'.format(arrow.now().isoformat().split('.')[0])


def verify_youtube_id(eid):
	return YOUTUBE_RE.fullmatch(eid)

def verify_spotify_id(eid):
	return SPOTIFY_RE.fullmatch(eid)

def verify_musicbrainz_id(eid):
	return MUSICBRAINZ_RE.fullmatch(eid)

source_validators = {'youtube':verify_youtube_id, 
					 'spotify':verify_spotify_id,
					 'mb_recording_id':verify_musicbrainz_id, 
					 'mb_releasegroup_id': verify_musicbrainz_id
					}

def contains_match(files_map):
	for f in files_map:
		if files_map[f]:
			return True
	return False

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
			logger.warning('{}/{} does not exist, skipped.'.format(item.identifier,
																   target))
			return False
		else:
			logger.warning('{}/{} failed, retrying. {} retries left. Status: {}'.format(
				item.identifier, target, retries, r))
			sleep(1)

	logger.error('{}/{} failed to update - {}'.format(item.identifier, target,
													  r.content))
	raise MetadataUpdateError('{}/{}'.format(item.identifier, target))

def get_updated_file_metadata(filename, matched_eids, item):

	# external-identifier formatting:
	# - All URNs for a given source should be grouped.
	# - Such groups should appear in alphabetical order by source name
	#   (e.g. urn:spotify:*, urn:youtube:*)
	# - URNs within a given group should be in descending order by match date.
	# - Dates in external-identifier-match-date should follow the same pattern,
	#   such that the date at index i of external-identifier-match-date
	#   corresponds to the match date of the resource at external-identifier[i]

	# The following is a bit kludgy, but handles eids/dates that don't
	# already conform to the described ordering.

	file_eid_map = get_eid_map(item, filename)
	file_eid_date_map = get_eid_date_map(item, filename)

	updated = False
	for source, eid in matched_eids.items():
		# Validate that this is a supported external source
		if not source in source_validators:
			raise MetadataException('Invalid external source \'{}\' provided by {}/{}'.format(
									source, item.identifier, filename))
		# Validate the identifier format for the given external source
		if not source_validators[source](eid):
			raise MetadataException('Invalid ID \'{}:{}\' provided by {}/{}'.format(
									source, eid, item.identifier, filename))

		matched_eid = 'urn:{}:{}'.format(source, eid)
		match_date = '{}:{}'.format(source, NOW)

		if matched_eid in file_eid_map.get(source, list()):
			continue
		
		if source in file_eid_map:
			file_eid_map[source].insert(0, matched_eid)
		else:
			file_eid_map[source] = [matched_eid]
		
		if source in file_eid_date_map:
			file_eid_date_map[source].insert(0, match_date)
		else:
			file_eid_date_map[source] = [match_date]

		updated = True

	if updated:
		updated_file_eid = map_to_list(file_eid_map)
		updated_file_eid_match_date = map_to_list(file_eid_date_map)

		return { 'external-identifier': updated_file_eid,
				 'external-identifier-match-date': updated_file_eid_match_date }
	return None

def get_updated_item_metadata(matched_eids, item):
	item_md = {'external_metadata_update': NOW}
	item_eid_map = get_eid_map(item)

	updated = False
	for source, eid in matched_eids.items():
		# Validate that this is a supported external source
		if not source in source_validators:
			raise MetadataException('Invalid external source \'{}\' provided by {}'.format(
									source, item.identifier))
		# Validate the identifier format for the given external source
		if not source_validators[source](eid):
			raise MetadataException('Invalid ID \'{}:{}\' provided by {}'.format(
									source, eid, item.identifier))

		matched_eid = 'urn:{}:{}'.format(source, eid)
		
		if matched_eid in item_eid_map.get(source, list()):
			continue

		if source in item_eid_map:
			item_eid_map[source].insert(0, matched_eid)
		else:
			item_eid_map[source] = [matched_eid]

		updated = True

	if updated:
		updated_item_eid = map_to_list(item_eid_map)
		item_md['external-identifier'] = updated_item_eid

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