import subprocess
import re

def create_database(reference_file, db_name='', db_dir='tmp/fingerprint'):

	db_path = db_dir.rstrip('/') + '/' + (db_name if db_name else reference_file.split('/')[-1]) + '.pklz'

	try:
		proc = subprocess.run(['python3', '../audfprint/audfprint.py', 'new', \
							   '--dbase', db_path, reference_file], stdout=subprocess.PIPE, 
							   encoding='UTF-8', check=True)
	except subprocess.CalledProcessError:
	 	#TODO: Exit codes
	 	print("Failed to generate fingerprint", file=sys.stderr)
	 	#TODO: Handle error
	 	return
	 	#exit(1)
	return db_path

def match_file(db_path, file_path):
	try:
		proc = subprocess.run(['python3', '../audfprint/audfprint.py', 'match', \
							   '--dbase', db_path, file_path], stdout=subprocess.PIPE, 
							   encoding='UTF-8', check=True)
	except subprocess.CalledProcessError:
	 	#TODO: Exit codes
	 	print("Failed to generate fingerprint", file=sys.stderr)
	 	#TODO: Handle error
	 	return False
	match = re.search('(\d+) of +(\d+) common hashes', proc.stdout)
	if match:
		score = float(match.group(1))/float(match.group(2))
		#print('      ', score)
		return score > 0.05
	return False