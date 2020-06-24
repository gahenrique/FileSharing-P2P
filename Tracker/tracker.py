from threading import Thread
import socket, json

'''
Accepted messages:
<REGISTER UUID>
<GETSEEDS UUID>
'''
class Tracker:
    def __init__(self):
        self.IP_ADRESS = '0.0.0.0'
        self.PORT = 2020
        self.BUFFER_SIZE = 256

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.IP_ADRESS, self.PORT))

        # self.sharing_files = {"ffae3681-1961-41c1-b4cf-571a58e57bec": ["192.168.0.7:24000", "192.168.0.3:24000", "127.0.0.1:123"]}
        self.sharing_files = {}

        while True:
            data, addr = self.server_socket.recvfrom(self.BUFFER_SIZE)
            t = Thread(target=self.handle_incoming_message, args = (data, addr))
            t.start()
    
    '''
    Read the message and call the appropriate method
    '''
    def handle_incoming_message(self, data, addr):
        data_decoded = data.decode('utf-8')
        
        msg_splitted = data_decoded.split(' ')
        if len(msg_splitted) == 3:
            msg_addr_splitted = msg_splitted[1].split(':')
            if msg_splitted[0] == "REGISTER" and len(msg_addr_splitted) == 2:
                seed_addr = "{}:{}".format(addr[0], msg_addr_splitted[1])
                self.register_seed(seed_addr, msg_splitted[2])
        elif len(msg_splitted) == 2 and msg_splitted[0] == "GETSEEDS":
                self.send_seeds(msg_splitted[1], addr)
    
    def register_seed(self, seed_addr, file_uuid):
        # Register file_uuid if is not registered
        if file_uuid not in self.sharing_files:
            self.sharing_files[file_uuid] = []

        if not seed_addr in self.sharing_files[file_uuid]:
            self.sharing_files[file_uuid].append(seed_addr)
            print("{}:{} Registered Successfully\n{}".format(file_uuid, seed_addr, self.sharing_files))
        else:
            print("{}:{} Already registered".format(file_uuid, seed_addr))

    '''
    Returns a list of addresses
    Ex: adress = '127.0.0.1:8080'
    '''
    def send_seeds(self, file_uuid, addr):
        print("Attempt to get seeds from {}".format(addr))
        if file_uuid in self.sharing_files:
            requested_peers_data = json.dumps(self.sharing_files[file_uuid]).encode('utf-8')
            self.server_socket.sendto(requested_peers_data, addr)
            print("Seeds from {} successfully sended to {}".format(file_uuid, addr))
        else:
            print("Attempt from: {} to GETSEEDS failed. FileID: {} not registered".format(addr, file_uuid))

                

if __name__ == "__main__":
    Tracker()