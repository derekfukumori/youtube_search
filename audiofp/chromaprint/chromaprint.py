import sys
import subprocess
import chromaprint_compare_c
from math import ceil

class FingerprintException(Exception):
    pass

class ChromaprintMatch:
	def __init__(self, score, segments):
		self.score = score
		self.segments = segments
		self.offset = frame_index_to_seconds(segments[0]['pos1'] - segments[0]['pos2'])

def generate_fingerprint(audio_file, length=120):
	try:
		#TODO: Duration restriction?
		proc = subprocess.run(['fpcalc', '-raw', '-plain', audio_file, '-length', str(ceil(length)), '-overlap'], 
			   stdout=subprocess.PIPE, encoding='ascii', check=True)
	except subprocess.CalledProcessError:
		raise FingerprintException()
	
	fingerprint = [int(n) for n in proc.stdout.rstrip().split(',')]
	return fingerprint

def match_fingerprints(reference_fp, query_fp, match_threshold=0.3):
	segments = chromaprint_compare_c.compare_fingerprints(reference_fp, query_fp)
	match_score = 0.0
	for s in segments:
		match_score += (1000 - s['score'])/1000 * s['duration']/len(query_fp)
	#print("    Score:", match_score, '; Segments:', segments, file=sys.stderr)
	return ChromaprintMatch(match_score, segments) if match_score >= match_threshold else None

def frame_index_to_seconds(frame_index, sample_rate=11025):
	return frame_index * 4096 / (3*sample_rate)