from download_handler import DownloadHandler
from server import Server
from support import *
import uuid, json, base64, sys

class FSU:
    def __init__(self, server_port):
        self.server = Server(server_addr=("127.0.0.1",server_port))
        if not is_dir(DOWNLOADS_FOLDER) and\
            not create_dir(DOWNLOADS_FOLDER):
            exit()
        if not is_dir(SHARE_FOLDER) and\
            not create_dir(SHARE_FOLDER):
            exit()
        if not is_dir(FSA_FOLDER) and\
            not create_dir(FSA_FOLDER):
            exit()
        if not is_dir(CHUNKS_FOLDER) and\
            not create_dir(CHUNKS_FOLDER):
            exit()

        self.is_running = True
        self.main_loop()

    def main_loop(self):
        print("\n### Welcome to Frango Sharing ###\n")

        while self.is_running:
            self.list_commands()
            opt = input('Option: ')
            self.filter_command_option(opt)
    
    def list_commands(self):
        print("Choose an option:")
        print("1 - Share a File")
        print("2 - Download a File from fsa")
        print("quit - Quit the Program")
        print("help - Commands List\n")

    def filter_command_option(self, opt):
        if opt == '1':
            self.share_file()
        elif opt == '2':
            self.download_file()
        elif opt == 'quit':
            print("See you soon! ;)")
            self.is_running = False
        elif opt == 'help':
            self.list_commands()
        else:
            print("Invalid Option\n")
    
    def share_file(self):
        file_path = input("Enter the full file path (Ex: '/Users/user/Downloads/file.pdf') :\n")
        file_name = input("Enter a name for your file on Frango Sharing:\n")
        print("")

        file_extension = file_path.split(sep='.')[-1]
        
        if is_file(file_path):
            random_uuid = str(uuid.uuid4())
            file_chunk_folder = "{}/{}".format(CHUNKS_FOLDER, random_uuid)
            create_dir(file_chunk_folder)

            # Get the number of chunks
            file_size = get_file_size(file_path)
            n_chunks = file_size // CHUNK_SIZE
            if file_size % CHUNK_SIZE != 0:
                n_chunks += 1

            self.chunk_file(file_path, file_chunk_folder, n_chunks)
            self.create_fsa(random_uuid, file_name, file_extension, n_chunks)
            self.server.register_seed(random_uuid)
            print("Completed: {}.fsa created at {}".format(file_name,FSA_FOLDER))
            print("Now you can share your file :D\n")

        else:
            print("Invalid path for a file\n")
    
    def download_file(self):
        fsa_path = input("Enter the full fsa path (Ex: '/Users/user/Downloads/file.fsa')\n")

        if not is_file(fsa_path):
            print("Invalid path for fsa file")
            return
        fsa_dict = self.get_fsa_dict(fsa_path)
        
        self.server.register_seed(fsa_dict['uuid']) # Starts sharing the chunks that will be downloaded
        download_handler = DownloadHandler(fsa_dict)
    
    '''
    Structure of fsa_dict:
    {
        'uuid' = file_uuid,
        'name' = file_name,
        'extension' = file_extension,
        'chunks' = file_n_chunks
    }
    '''
    def get_fsa_dict(self, path):
        with open(path, 'rb') as fsa_stream:
            fsa_data = base64.b64decode(fsa_stream.read()).decode('utf-8')
            fsa_dict = json.loads(fsa_data)
        return fsa_dict

    
    def create_fsa(self, file_uuid, file_name, file_extension, file_n_chunks):
        fsa_path = "{}/{}.fsa".format(FSA_FOLDER, file_name)
        data = {'uuid': file_uuid, 'name': file_name, 'extension': file_extension, 'chunks': file_n_chunks}
        data_encoded = json.dumps(data).encode('utf-8')
        data_base64 = base64.b64encode(data_encoded)
        with open(fsa_path, 'wb') as fsa_stream:
            fsa_stream.write(data_base64)
    
    def chunk_file(self, file_path, into_path, n_chunks):
        with open(file_path, 'rb') as f:
            for i in range(n_chunks):
                new_file_path = "{}/{}".format(into_path, str(i))
                offset = i * CHUNK_SIZE
                f.seek(offset, 0)
                data = f.read(CHUNK_SIZE)
                with open(new_file_path, 'wb') as chunk:
                    chunk.write(data)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Missing server's target port")
        exit()
    elif len(sys.argv) > 2:
        print("Too much arguments, provide only the server's target port")
        exit()
    elif not sys.argv[1].isdigit() or not int(sys.argv[1]) in range(1,65535):
        print("Provided port is invalid")
        exit()

    fsu = FSU(int(sys.argv[1]))