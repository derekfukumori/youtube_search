from copy import copy

def to_list(x):
	return x if isinstance(x, list) else [x]

def get_eid_map(item, filename=None):
	if filename == None:
		eids = to_list(copy(item.metadata.get('external-identifier', list())))
	else:
		eids = to_list(copy(item.get_file(filename).__dict__.get('external-identifier', list())))

	eid_map = dict()

	for e in eids:
		s = e.split(':')[1] # Source name, without the preceding 'urn:'
		if s in eid_map:
			eid_map[s].append(e)
		else:
			eid_map[s] = [e]

	return eid_map

def get_eid_date_map(item, filename):
	eid_match_dates = to_list(copy(item.get_file(filename).__dict__.get('external-identifier-match-date', list())))
	eid_date_map = dict()

	for d in eid_match_dates:
		s = d.split(':')[0] # Source name
		if s in eid_date_map:
			eid_date_map[s].append(d)
		else:
			eid_date_map[s] = [d]

	return eid_date_map


def map_to_list(d):
	l = []
	for s in sorted(list(d.keys())):
		l.extend(d[s])
	return l