import sys
import ast
import time
import requests
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def archive_video(ytid):
	logger.info("Archiving {}".format(ytid))
	while True:
		try:
			r = requests.post('http://crawl-db00.us.archive.org/crawling/yt/m.py/add',
						  	  data={'vid':ytid})
			logger.info(r.json())
			if not 'success' in r.json() or not r.json()['success']:
				logger.warning('Archiving failed, retrying')
				sleep(1)
				continue
			logger.info('Success')
			break
		except requests.exceptions.RequestException as e:
			logger.warning("RequestException while archiving: {}".format(e))
			sleep(1)
			continue

def archive_dict(item_results_dict):
	for iaid, results in item_results_dict.items():
		if 'full_album' in results:
			archive_video(results['full_album'])
		else:
			for filename, ytid in results.items():
				if ytid:
					archive_video(ytid)
	

def follow(fd):
	while True:
		line = fd.readline()
		if not line:
			time.sleep(30)
			continue
		yield line


if __name__ == '__main__':
	with open(sys.argv[1], 'r') as yt_results_fd:
		yt_results = follow(yt_results_fd)
		for item_results in yt_results:
			try:
				item_results_dict = ast.literal_eval(item_results)
			except SyntaxError as e:
				logger.warning("SyntaxError while parsing output")
				continue
			archive_dict(item_results_dict)
			# for iaid, results in item_results_dict.items():
			# 	if 'full_album' in results:
			# 		archive_video(results['full_album'])
			# 	else:
			# 		for filename, ytid in results.items():
			# 			if ytid:
			# 				archive_video(ytid)