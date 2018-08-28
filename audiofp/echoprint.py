import sys
import subprocess
import json
import zlib
import base64
import itertools
import json
import os

from time import time

class Echoprint:
	def __init__(self, codes, offsets):
		self.codes = codes
		self.offsets = offsets

class FingerprintException(Exception):
	pass

# Echoprint codegen doesn't like special characters in filepaths, and escaping
# doesn't work for whatever reason. This function is an ongoing effort to
# figure out which characters cause problems.
def preprocess_path(path):
	processed_path = path.replace('`', '')
	processed_path = processed_path.replace('$', 'S')
	return processed_path

def generate_fingerprint(audio_filepath, length=120):

	processed_path = preprocess_path(audio_filepath)
	# If the filepath contains special characters, move it to a new path with
	# those characters removed/replaced.
	if processed_path != audio_filepath:
		os.rename(audio_filepath, processed_path)

	try:
		proc = subprocess.run(['echoprint-codegen', processed_path], 
							  stdout=subprocess.PIPE, encoding='UTF-8', check=True)
	except subprocess.CalledProcessError:
		raise FingerprintException()

	# If we had to move the file, move it back
	if processed_path != audio_filepath:
		os.rename(processed_path, audio_filepath)
	
	res = json.loads(proc.stdout.strip())
	return decode_echoprint_string(res[0]['code'])

def compare_fingerprints(reference_fp, query_fp, match_threshold=0.3):
	reference_codeset = set(reference_fp.codes)
	query_codeset = set(query_fp.codes)
	
	rating = len(reference_codeset.intersection(query_codeset)) / len(reference_codeset)
	return rating


def split_seq(iterable, size):
	it = iter(iterable)
	item = list(itertools.islice(it, size))
	while item:
		yield item
		item = list(itertools.islice(it, size))

def decode_echoprint_string(echoprint_b64_zipped):
	'''
	Decode an echoprint string as output by `echoprint-codegen`.
	The function returns offsets and codes as list of integers.
	'''
	zipped = base64.urlsafe_b64decode(echoprint_b64_zipped)
	unzipped = zlib.decompress(zipped).decode()

	N = len(unzipped)

	offsets = [int(''.join(o), 16) for o in split_seq(unzipped[:int(N/2)], 5)]
	codes = [int(''.join(o), 16) for o in split_seq(unzipped[int(N/2):], 5)]
	return Echoprint(codes, offsets)