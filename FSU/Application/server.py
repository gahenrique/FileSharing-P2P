import socket, json
from threading import Thread
from support import get_directory_files, get_folders, is_dir, CHUNKS_FOLDER

class Server:
    '''
    SERVER_ADDR  - Tuple of Server's IP adress and port 
    TRACKER_ADDR    - Tuple of Tracker's IP adress and port
    '''
    def __init__(self, server_addr=('0.0.0.0', 24000), tracker_addr=('127.0.0.1', 2020), buffer_size=256, max_connections=10):
        self.SERVER_ADDR = server_addr
        self.TRACKER_ADDR = tracker_addr
        self.BUFFER_SIZE = buffer_size
        self.MAX_CONNECTIONS = max_connections
        
        self.clients = []

        # TODO: Set the thread as daemon is not recommended, use Events to finalize the thread instead
        # https://docs.python.org/3/library/threading.html#threading.Event
        t = Thread(target=self.host_server, daemon=True)
        t.start()

    def host_server(self):
        # Creating TCP socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:

            server_socket.bind(self.SERVER_ADDR)
            server_socket.listen(self.MAX_CONNECTIONS)

            # Waiting for connections
            while True:
                conn, addr = server_socket.accept()
                self.clients.append((conn, addr))
                t = Thread(target=self.clientHandler, args = (conn, addr))
                t.start()
    
    def get_serving_files(self):
        # Folder's name is equal to the file_uuid
        return get_folders(CHUNKS_FOLDER)

    '''
    Protocol:
    1. Client -> FILE_UUID
    2. While Server doesn't send .EOM.:
        2.1. Server -> Send serialized part of the list of available chunks for FILE_UUID
        2.2. Client -> Receives the serialized message
    3. While Client doesn't send .EOM.:
        3.1. Client -> Chunk Index
        3.2. Server -> Chunk binary
    '''
    def clientHandler(self, conn, addr):
        # Wait for request -> FILE_UUID
        # Send available chunks for file_uuid (Obs: message must end with .EOM. - End of Message)
        # While chunk index request
            # Send chunk
        msg = conn.recv(self.BUFFER_SIZE)
        file_uuid = msg.decode('utf-8')
        print("Request for {}, from {} received".format(file_uuid, addr))
        
        # TODO: Sort by less sended chunks
        available_chunks = self.get_available_chunks(file_uuid)
        available_chunks_encoded = "{}.EOM.".format(json.dumps(available_chunks)).encode('utf-8')
        conn.send(available_chunks_encoded)

        while True:
            msg = conn.recv(self.BUFFER_SIZE)
            chunk_id = msg.decode('utf-8')

            # Stop the execution of the block if .EOM. is detected
            if chunk_id == ".EOM.":
                conn.close()
                break
            
            chunk_path = "{}/{}/{}".format(CHUNKS_FOLDER, file_uuid, chunk_id)
            with open(chunk_path, 'rb') as chunk_stream:
                chunk_data = chunk_stream.read()
                conn.send(chunk_data)
                print("Chunk {} sended to {}".format(chunk_id, addr))

    '''
    Tracker Protocol:
    1. Server -> REGISTER IP:PORT FILE_UUID
    '''
    def register_seed(self, file_uuid):
        # REGISTER IP:PORT FILE_UUID
        tracker_msg = 'REGISTER {}:{} {}'.format(self.SERVER_ADDR[0],self.SERVER_ADDR[1],file_uuid).encode('utf-8')
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.sendto(tracker_msg, self.TRACKER_ADDR)
    
    def get_available_chunks(self, file_uuid):
        file_chunks_path = "{}/{}".format(CHUNKS_FOLDER, file_uuid)
        return get_directory_files(file_chunks_path)

# Server(tracker_addr=('127.0.0.1', 2020))