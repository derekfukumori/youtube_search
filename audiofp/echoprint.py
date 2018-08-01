import sys
import subprocess
import json
import zlib
import base64
import itertools
import json

from time import time

class FingerprintException(Exception):
	pass

def generate_fingerprint(audio_file, length=120):
	try:
		#TODO: Duration restriction?
		# proc = subprocess.run(['fpcalc', '-raw', '-plain', audio_file, '-length', str(ceil(length)), '-overlap'], 
		# 	   stdout=subprocess.PIPE, encoding='ascii', check=True)
		proc = subprocess.run(['echoprint-codegen', audio_file], 
							  stdout=subprocess.PIPE, encoding='ascii', check=True)
	except subprocess.CalledProcessError:
		raise FingerprintException()
	
	res = json.loads(proc.stdout.strip())
	return res[0]['code']

def match_fingerprints(reference_fp, query_fp, match_threshold=0.3):
	reference_offsets, reference_codes = decode_echoprint(reference_fp)
	query_offsets, query_codes = decode_echoprint(query_fp)

	reference_codeset = set(reference_codes)
	query_codeset = set(query_codes)
	
	rating = len(reference_codeset.intersection(query_codeset)) / len(reference_codeset)
	return rating > match_threshold


def split_seq(iterable, size):
	it = iter(iterable)
	item = list(itertools.islice(it, size))
	while item:
		yield item
		item = list(itertools.islice(it, size))

def decode_echoprint(echoprint_b64_zipped):
	'''
	Decode an echoprint string as output by `echoprint-codegen`.
	The function returns offsets and codes as list of integers.
	'''
	zipped = base64.urlsafe_b64decode(echoprint_b64_zipped)
	unzipped = zlib.decompress(zipped).decode()

	N = len(unzipped)

	offsets = [int(''.join(o), 16) for o in split_seq(unzipped[:int(N/2)], 5)]
	codes = [int(''.join(o), 16) for o in split_seq(unzipped[int(N/2):], 5)]
	return offsets, codes