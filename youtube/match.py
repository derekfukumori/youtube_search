from youtube.search import *
import glob
import subprocess
import audiofp.chromaprint.chromaprint as fp

def download_video(yt_id, destdir='.'):
	""" Downloads the audio of a YouTube video via youtube-dl.

	Args:
		yt_id     (str): The YouTube video ID.
		destdir   (str): Download location for audio streams.

	Returns:
		The path of the downloaded file, or None on unsuccessful
		download or FFmpeg conversion.
	"""

	path_no_ext = '{}/{}'.format(destdir.rstrip('/'), yt_id)
	cached_files = glob.glob(path_no_ext + '.*')
	if cached_files:
		return cached_files[0]

	output_template = path_no_ext + '.%(ext)s'
	try:
		# TODO: It seems like youtube-dl provides an audio-only stream in cases
		# where pytube did not. Does it always? If not, define fallback behavior.
		subprocess.run(['youtube-dl', '--prefer-ffmpeg','--no-check-certificate', '-q', '-o', output_template,
					   '-f', 'bestaudio', 'https://www.youtube.com/watch?v=' + yt_id],
					   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
	except subprocess.CalledProcessError:
		pass

	dl_files = glob.glob(path_no_ext + '.*')
	if dl_files:
		return dl_files[0]

	return None

def cull_by_duration(videos, expected_duration, duration_range=10):
	return [v for v in videos if abs(v['duration'] - expected_duration) < duration_range]

def match_tracks(tracks, album, ia_dir='.', yt_dir='.', query_fmt='{artist} {title}', api_key=''):
	results = {}
	for track in tracks:
		videos = search_by_track(track, query_fmt=query_fmt, api_key=api_key)
		videos = cull_by_duration(videos, track.duration)
		if not videos:
			continue
		
		# try:
		reference_fp = fp.generate_fingerprint(track.download(destdir=ia_dir))

		for v in videos:
			query_fp = fp.generate_fingerprint(download_video(v['id'], destdir=yt_dir))
			if fp.match_fingerprints(reference_fp, query_fp):
				results[track.name] = v['id']
				break
				
	return results

def match_album(album, ia_dir='.', yt_dir='.', query_fmt='{artist} {title}', api_key=''):
    results = {}
    videos = search_by_album(album, query_fmt=query_fmt, api_key=api_key)
    videos = cull_by_duration(videos, album.duration, duration_range=180)
    for v in videos:
        matches = {}

        # try:
        reference_fp = fp.generate_fingerprint(download_video(v['id'], destdir=yt_dir),
            								   length=v['duration']+1)
        # except FingerprintException:
        #     logger.warning('{}: Unable to fingerprint YouTube video "{}"'.format(album.identifier, v['id']))
        #     continue

        for track in album.tracks:
            matches[track.name] = None
            # try:
                # query_fp = fingerprint_ia_audio(track, remove_file=clear_cache)
            query_fp = fp.generate_fingerprint(track.download(destdir=ia_dir))
            # except FingerprintException:
            #     logger.warning('{}: Unable to fingerprint file "{}"'.format(album.identifier, track.name))
            #     continue
            # except DownloadException:
            #     logger.warning('{}: Failed to download file "{}"'.format(album.identifier, track.name))
            #     continue
            
            match = fp.match_fingerprints(reference_fp, query_fp, match_threshold=0.2)
            matches[track.name] = match if match else None
        # If at least half of the album's tracks produce a match, consider this 
        # video a potential match.
        if sum(bool(match) for match in matches.values())/len(album.tracks) >= 0.5:
            f = [t.ordinal for t in album.tracks]
            time_offsets = {}
            first_match = matches[album.tracks[0].name]
            time_offsets[album.tracks[0].name] = first_match.offset if first_match else 0
            ordered = True
            # Iterate through all tracks in album-order and ensure that their
            # respective time offsets are strictly increasing. If not, consider
            # this video an invalid match.
            for i in range(1,len(album.tracks)):
                match = matches[album.tracks[i].name]
                prev_offset = time_offsets[album.tracks[i-1].name]
                curr_offset = match.offset if match else prev_offset + album.tracks[i-1].duration
                if curr_offset < prev_offset:
                    ordered = False
                    break
                time_offsets[album.tracks[i].name] = curr_offset

            if not ordered:
                continue

            results['full_album'] = v['id']
            for track in album.tracks:
                results[track.name] = '{0}&t={1}'.format(v['id'], 
                                       max(0, int(time_offsets[track.name])))
            break

    return results