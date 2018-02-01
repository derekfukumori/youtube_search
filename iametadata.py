def get_file_metadata(item, filename):
    for file_metadata in item.item_metadata['files']:
        if file_metadata['name'] == filename:
            return file_metadata
    return {}

def get_acoustid(file_metadata):
    acoustid_str = ''
    if 'external-identifier' in file_metadata:
        if isinstance(file_metadata['external-identifier'], str):
            if 'acoustid' in file_metadata['external-identifier']:
                acoustid_str = file_metadata['external-identifier'][13:]
        else:
            for identifier in file_metadata['external-identifier']:
                if 'acoustid' in identifier:
                    acoustid_str = identifier[13:]
    return acoustid_str
