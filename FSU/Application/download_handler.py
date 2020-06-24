import socket, json, time
from threading import Thread, Lock
from support import CHUNKS_FOLDER, DOWNLOADS_FOLDER, create_dir, is_dir, merge_chunks

class DownloadHandler:
    def __init__(self, fsa_dict, tracker_addr = ('127.0.0.1', 2020), buffer_size = 256):
        self.MAX_CONNECTIONS = 10          # The maximum number of seeds to connect each time
        self.TRACKER_ADDR = tracker_addr
        self.BUFFER_SIZE = buffer_size
        self.fsa_dict = fsa_dict
        self.completed = False             # Indicates if the download has ended

        self.threads = []
        self.mutex = Lock()
        self.number_chunks_downloaded = 0
        self.downloaded_chunks = [False for _ in range(fsa_dict['chunks'])]

        self.download()
    
    '''
    Algorithm:
    1. Get seeds from Tracker
    2. While download not completed:
        2.1. Release closed connections
        2.2. While there are available seeds to connect:
            2.2.1. If connections >= MAX_CONNECTIONS break the loop
            2.2.2. Pop a seed from available_seeds and try to connect
            2.2.3. Attempt to connect with seed
            2.2.4. If there is no available seeds, request Tracker for more
    3. Join the downloaded chunks into a single file
    '''
    def download(self):
        file_uuid = self.fsa_dict['uuid']
        
        available_seeds = self.request_seeds(file_uuid)
        print("Available Seeds: ",available_seeds)
        
        file_dir = "{}/{}".format(CHUNKS_FOLDER, file_uuid)
        if not is_dir(file_dir):
            create_dir(file_dir)

        start_time = time.time() # Get start time

        while self.number_chunks_downloaded < self.fsa_dict['chunks']:
            # Remove terminated threads
            for t in self.threads:
                if not t.is_alive():
                    print('Removing thread')
                    self.threads.remove(t)

            while len(available_seeds) > 0:
                if len(self.threads) >= self.MAX_CONNECTIONS:
                    # Limit the number of connections
                    break
                seed = available_seeds.pop()
                seed_addr = seed.split(':')
                seed_ip = seed_addr[0]
                seed_port = seed_addr[1]
                t = Thread(target=self.handle_connection, args=(file_uuid, seed_ip, seed_port))
                t.start()
                self.threads.append(t)

                if len(available_seeds) == 0:
                    # Request for more seeds
                    available_seeds = self.request_seeds(file_uuid)
        
        download_time = time.time() - start_time # Get time to complete the download
        chunks_path = "{}/{}".format(CHUNKS_FOLDER, file_uuid)
        merge_chunks(chunks_path, DOWNLOADS_FOLDER, self.fsa_dict['name'], self.fsa_dict['extension'])
        print("\nDownload of {} completed at {}\nCompleted in: {}seconds\n".format(self.fsa_dict['name'], DOWNLOADS_FOLDER, download_time))

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
    def handle_connection(self, file_uuid, seed_ip, seed_port):
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.settimeout(10)
        try:
            print("Attempt to connect with {}:{}".format(seed_ip, seed_port))
            tcp_socket.connect((seed_ip, int(seed_port)))

            request_available_chunks_msg = file_uuid.encode('utf-8')
            tcp_socket.send(request_available_chunks_msg)
            
            # Receiving available chunks
            # .EOM. stands for END OF MESSAGE
            available_chunks = ""
            while ".EOM." not in available_chunks:
                available_chunks_data = tcp_socket.recv(self.BUFFER_SIZE)
                available_chunks += available_chunks_data.decode('utf-8')
            available_chunks_list = json.loads(available_chunks[:-5])

            for chunk_index in available_chunks_list:
                self.mutex.acquire()
                if not self.downloaded_chunks[int(chunk_index)]:
                    self.downloaded_chunks[int(chunk_index)] = True
                    self.mutex.release()

                    request_chunk_msg = chunk_index.encode('utf-8')
                    tcp_socket.send(request_chunk_msg)

                    # There is no need to wait for .EOM. because CHUNK_SIZE is equal to BUFFER_SIZE
                    chunk_data = tcp_socket.recv(self.BUFFER_SIZE)
                    # It is possible to check if the chunk was properly received here
                    chunk_path = "{}/{}/{}".format(CHUNKS_FOLDER, file_uuid, chunk_index)
                    with open(chunk_path, 'wb') as chunk_stream:
                        chunk_stream.write(chunk_data)
                        self.mutex.acquire()
                        self.number_chunks_downloaded += 1
                        self.mutex.release()
                        print("Chunk {} downloaded from {}".format(chunk_index, (seed_ip, seed_port)))
                else:
                    self.mutex.release()

            # End of requests message
            tcp_socket.send('.EOM.'.encode('utf-8'))
            tcp_socket.close()

        except Exception as msg:
            # print("Exception Socket.error: {}, for: {}:{}".format(msg, seed_ip, seed_port))
            pass

    '''
    Method return an array of seeds
    Seed is a string in the format 'IP:PORT'

    Tracker Protocol:
    1. Client -> GETSEEDS FILE_UUID
    2. Tracker -> List of adresses
    '''
    def request_seeds(self, file_uuid):
        print("Attempt to request seeds for file_uuid: {}".format(file_uuid))

        tracker_msg = 'GETSEEDS {}'.format(file_uuid).encode('utf-8')
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.sendto(tracker_msg, self.TRACKER_ADDR)

        # Bigger size to prevent from multiple messages
        # If the number of seeds becomes to big, implements .EOM. into the protocol
        data, addr = udp_socket.recvfrom(2048)
        if addr == self.TRACKER_ADDR:
            data_decoded = data.decode('utf-8')
            seeds_list = json.loads(data_decoded)

        return seeds_list