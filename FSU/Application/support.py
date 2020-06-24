import os

# Constants
TRACKER_ADDR = ('127.0.0.1', 2020)                  # Tuple of Tracker's IP adress and port
CHUNK_SIZE = 256                                    # Size of a chunk given in bytes
DOWNLOADS_FOLDER = '../Downloads'                    # Folder that contains successfully downloaded and joined chunks
SHARE_FOLDER = '../Share'                            # Parent folder for shared files
CHUNKS_FOLDER = '{}/Chunks'.format(SHARE_FOLDER)    # Folder that contains chunks to share with peers
FSA_FOLDER = '{}/FSA'.format(SHARE_FOLDER)          # Folder that contains generated fsa files

# Supporting methods
def create_dir(path):
    try:
        os.mkdir(path)
    except OSError:
        print ("Creation of the directory %s failed" % path)
        return False
    else:
        print ("Successfully created the directory %s " % path)
        return True

def is_dir(path):
    return os.path.isdir(path)

def is_file(path):
    return os.path.isfile(path)

def get_file_size(path):
    return os.stat(path).st_size

def get_directory_files(path):
    f = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        f.extend(filenames)
        break
    return f

def get_folders(path):
    return [name for name in os.listdir(path) if os.path.isdir(name)]

def merge_chunks(from_path, into_path, with_name, with_extension):
    chunks = get_directory_files(from_path)
    chunks.sort(key=(lambda e: int(e)))

    final_data_path = into_path + '/' + with_name + '.' + with_extension
    with open(final_data_path, 'ab') as final_data:
        for chunk in chunks:
            chunk_full_path = from_path + '/' + chunk
            with open(chunk_full_path, 'rb') as chunk_stream:
                chunk_data = chunk_stream.read()
                final_data.write(chunk_data)