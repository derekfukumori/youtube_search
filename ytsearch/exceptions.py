import enum

class ExitCodes(enum.Enum):
	IAMetadataError = 2,
	IAMediatypeError = 3,
	ConnectionError = 4

class DownloadException(Exception):
    pass

class MetadataException(Exception):
    pass

class MediaTypeException(Exception):
    pass