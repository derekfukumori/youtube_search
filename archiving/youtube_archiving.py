import time
import requests
import logging

logger = logging.getLogger('youtube_archiver')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

MAX_RETRIES = 10

def archiver_submit(ytid):
	for _ in range(MAX_RETRIES):
		try:
			r = requests.post('http://crawl-db00.us.archive.org/crawling/yt/m.py/add',
							  data={'vid':ytid})
		except requests.exceptions.RequestException as e:
			logger.warning('Exception occurred during submission, retrying. {}'.format(e))
			time.sleep(1)
			continue
		else:
			if not 'success' in r.json() or not r.json()['success']:
				logger.warning('Submission failed, retrying.')
				time.sleep(1)
				continue
			logger.info(r.json())
			break
	else:
		logger.error('Max retries reached, aborting.')
		raise Exception()
		