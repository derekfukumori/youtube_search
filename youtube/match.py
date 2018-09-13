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

def match_tracks(ia_tracks, ia_album, ia_dir='.', yt_dir='.', query_fmt='{artist} {title}', api_key=''):
	results = {}
	for ia_track in ia_tracks:
		videos = search_by_track(ia_track, query_fmt=query_fmt, api_key=api_key)
		videos = cull_by_duration(videos, ia_track.duration)
		if not videos:
			continue
		
		# try:
		reference_fp = fp.generate_fingerprint(ia_track.download(destdir=ia_dir))

		for v in videos:
			query_fp = fp.generate_fingerprint(download_video(v['id'], destdir=yt_dir))
			if fp.match_fingerprints(reference_fp, query_fp):
				results[ia_track.id] = v['id']
				break
				
	return results

def match_album(ia_album, ia_dir='.', yt_dir='.', query_fmt='{artist} {title}', api_key=''):
    results = {}
    videos = search_by_album(ia_album, query_fmt=query_fmt, api_key=api_key)
    videos = cull_by_duration(videos, ia_album.duration, duration_range=180)

    for v in videos:
        matches = {}

        # try:
        reference_fp = fp.generate_fingerprint(download_video(v['id'], destdir=yt_dir),
            								   length=v['duration']+1)
        # except FingerprintException:
        #     logger.warning('{}: Unable to fingerprint YouTube video "{}"'.format(album.identifier, v['id']))
        #     continue

        for ia_track in ia_album.tracks:
            matches[ia_track.id] = None
            # try:
                # query_fp = fingerprint_ia_audio(track, remove_file=clear_cache)
            query_fp = fp.generate_fingerprint(ia_track.download(destdir=ia_dir))
            # except FingerprintException:
            #     logger.warning('{}: Unable to fingerprint file "{}"'.format(album.identifier, track.name))
            #     continue
            # except DownloadException:
            #     logger.warning('{}: Failed to download file "{}"'.format(album.identifier, track.name))
            #     continue
            
            match = fp.match_fingerprints(reference_fp, query_fp, match_threshold=0.2)
            matches[ia_track.id] = match if match else None
        # If at least half of the album's tracks produce a match, consider this 
        # video a potential match.
        if sum(bool(match) for match in matches.values())/len(ia_album.tracks) >= 0.5:
            f = [t.ordinal for t in ia_album.tracks]
            time_offsets = {}
            first_match = matches[ia_album.tracks[0].id]
            time_offsets[ia_album.tracks[0].id] = first_match.offset if first_match else 0
            ordered = True
            # Iterate through all tracks in album-order and ensure that their
            # respective time offsets are strictly increasing. If not, consider
            # this video an invalid match.
            for i in range(1,len(ia_album.tracks)):
                match = matches[ia_album.tracks[i].id]
                prev_offset = time_offsets[ia_album.tracks[i-1].id]
                curr_offset = match.offset if match else prev_offset + ia_album.tracks[i-1].duration
                if curr_offset < prev_offset:
                    ordered = False
                    break
                time_offsets[ia_album.tracks[i].id] = curr_offset

            if not ordered:
                continue

            results['full_album'] = v['id']
            for ia_track in ia_album.tracks:
                results[ia_track.id] = '{0}&t={1}'.format(v['id'], max(0, int(time_offsets[ia_track.id])))
            break

    return results