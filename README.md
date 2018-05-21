# YouTube Matching
A utility for matching Internet Archive audio items to corresponding YouTube videos.

## Initialization
To build and install C extensions:

	python setup.py install

### Requirements
	pip install -r requirements.txt
	brew install ffmpeg
	brew install youtube-dl
This project also requires the [Chromaprint fpcalc utility](https://acoustid.org/chromaprint).

## Running
	python search.py [-c CONFIG_FILE][-sf][-f][-cac] INTERNETARCHIVE_ITEM_ID ...
    
The script takes as input any number of Internet Archive item identifiers. To match against individual files, use the `-sf` flag with input format `identifier/filename_url`. Output is printed to stdout with the following form:
	
    {'item_identifier':
    	{'filename0': '[YouTube video ID]',
        'filename1': '[YouTube video ID]',
        ...
        }
    }
    
If no match is found for a given file, the YouTube video ID field will be an empty string.

### Configuration
The `CONFIG_FILE` is an Internet Archive configuration file with the following fields:
	
    [ytsearch]
    google_api_keys = KEY0, KEY1, KEY2, ...
    youtube_dl_dir = path/to/youtube_downloads
    ia_dl_dir = path/to/internetarchive_downloads
    
* The `google_api_keys` field is a comma-separated list of YouTube Data API keys. At least one must be present in this field for the script to run.
* The `youtube_dl_dir` field is the destination directory for all files downloaded from YouTube.
* The `ia_dl_dir` field is the destination directory for all files downloaded from Internet Archive.

If no configuration file is provided, the user default config will be used, if one exists.

### File Management
By default, files downloaded from both YouTube and Internet Archive are kept on disk. To delete these files as each item is matched, run with the `-cac` flag.

### Full-Album Matching
To enable matching items against full-album videos, run with the `-f` flag. This will attempt to match the item first against full-album videos. If none is found, the script will then match against each individual track as normal. In the case of a full-album match, the output will look like the following:
	
    {'cd_18-tracks_bruce-springsteen':
    	{'full_album': 'vyqhSmqvTfs',
        "disc1/01. Bruce Springsteen - Growin' Up.flac": 'vyqhSmqvTfs&t=0',
        'disc1/02. Bruce Springsteen - Seaside Bar Song.flac': 'vyqhSmqvTfs&t=160',
        'disc1/03. Bruce Springsteen - Rendezvous.flac': 'vyqhSmqvTfs&t=375',
        'disc1/04. Bruce Springsteen - Hearts Of Stone.flac': 'vyqhSmqvTfs&t=546',
        ...
        }
    }
         
The YouTube video ID for the full-album video is given in the `full_album` field, and the fields for each individual track contain time offsets into the full-album video in the form of a YouTube query string (e.g. <https://www.youtube.com/watch?v=vyqhSmqvTfs&t=160> for the second track above).

## YouTube Data API Quotas
A potential bottleneck to this utility is the per-day limit on number of queries to the YouTube Data API. A single Google Developer project has a default quota of 1,000,000 units per day, with each API operation costing some number of units (searches cost 100 units; metadata retrieval costs 2-3 units). A single instance of this script running continuously uses in the ballpark of 1,500,000 units per day.

A single free-tier Google Developer account gives an allotment of 10 projects, with each project having its own 1,000,000 unit quota. A single process will thus use ~15% of an account's total daily quota. In practice, queries are assigned to an individual API key at a per-item level, and different items will require different numbers of queries, so there's a fair amount of variance in daily usage of each individual API key. It's probably best to maintain around a 2:1 key-to-process ratio to avoid running into 403 issues.