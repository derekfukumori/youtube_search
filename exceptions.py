import enum

class ExitCodes(enum.Enum):
	IAMetadataError = 2,
	IAMediatypeError = 3,
	DarkedError = 4,
	ConnectionError = 5

class DownloadException(Exception):
    pass

class MetadataException(Exception):
    pass

class DarkedError(Exception):
	pass

class MediaTypeException(Exception):
    pass

class MetadataUpdateError(Exception):
	pass

class AudioException(Exception):
	pass

class FingerprintException(Exception):
	pass