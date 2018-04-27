import sys
import subprocess
import chromaprint_compare_c

def generate_fingerprint(audio_file):
	try:
		#TODO: Duration restriction?
		proc = subprocess.run(['fpcalc', '-raw', '-plain', audio_file], 
			   stdout=subprocess.PIPE, encoding='ascii', check=True)
	except subprocess.CalledProcessError:
		#TODO: Exit codes
		print("Failed to generate fingerprint", file=sys.stderr)
		exit(1)
	
	fingerprint = [int(n) for n in proc.stdout.rstrip().split(',')]
	return fingerprint

def match_fingerprints(fpa, fpb):
	segments = chromaprint_compare_c.compare_fingerprints(fpa, fpb)
	
	match_score = 0.0
	for s in segments:
		match_score += (1000 - s['score'])/1000 * s['duration']/len(fpa)
	#print("    Score:", match_score, '; Segments:', segments, file=sys.stderr)
	print("      Score: ", match_score, "\tSegments: ", segments, file=sys.stderr)
	return match_score > 0.3