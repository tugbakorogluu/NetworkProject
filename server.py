'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util


class Server:
    '''
    This is the main Server Class. 
    '''
    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))
        self.clients = {}
        self.client_info = {}

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it
        '''
        try:
            while True:
                data, addr = self.sock.recvfrom(1024)
                print(f"LOG: Ham paket alındı {addr}: {data}")
                self.process_packet(data, addr)
        except KeyboardInterrupt:
            self.sock.close()
        
    def process_packet(self, data, addr):
        try:
            decoded_data = data.decode()
            body, received_checksum = decoded_data.rsplit('|', 1)
            body_with_pipe = body + '|'
            
            calculated_checksum = util.generate_checksum(body_with_pipe.encode())

            if received_checksum != calculated_checksum:
                print(f"LOG: Checksum uyuşmuyor, {addr} adresinden gelen paket yoksayıldı.")
                return
            
            packet_type, seq_num_str, message, _ = util.parse_packet(decoded_data)
            print(f"LOG: Paket çözümlendi: tip={packet_type}, sıra_no={seq_num_str}, mesaj='{message}'")
            seq_num = int(seq_num_str)

            # process the message
            if packet_type == "start":
                self.client_info[addr] = seq_num
                print(f"LOG: Bağlantı başlatıldı: {addr}.")
            elif packet_type == "data":
                if addr not in self.client_info:
                    self.client_info[addr] = -1

                expected_seq = self.client_info[addr] + 1
                if seq_num == expected_seq:
                    self.client_info[addr] = seq_num
                    
                    message_parts = message.split()
                    command = message_parts[0]

                    if command == "join":
                        username = message_parts[2]  
                        self.join(username, addr)

                    elif command == "request_users_list":
                        if addr not in self.clients:
                            print("Error: Address not recognized")
                        else:
                            self.request_users_list(self.clients[addr], addr)

                    elif command == "send_message":
                        try:
                            num_recipients = int(message_parts[2])
                            recipients = message_parts[3:3 + num_recipients]
                            text = ' '.join(message_parts[3 + num_recipients:])
                            sender_username = self.clients.get(addr, "Unknown")
                            
                            forward_message_content = f"{sender_username}: {text}"
                            forward_message = util.make_message('msg', 4, forward_message_content)

                            if len(recipients) == 1 and recipients[0] == 'all':
                                print(f"LOG: msj: {sender_username} -> tümü")
                                broadcast_list = [username for client_addr, username in self.clients.items() if client_addr != addr]
                                self.send_message(sender_username, broadcast_list, forward_message)
                            else:
                                print(f"LOG: msj: {sender_username} -> {', '.join(recipients)}")
                                self.send_message(sender_username, recipients, forward_message)
                        except (IndexError, ValueError):
                            pass

                    elif command == "disconnect":
                        try:
                            username = message_parts[2]
                            if addr in self.clients:
                                del self.clients[addr]
                                print(f"LOG: bağlantı kesildi: {username}")
                            else:
                                print(f"LOG: Var olmayan veya zaten bağlantısı kesilmiş kullanıcı tarafından bağlantı kesme denemesi: {username}")
                        except IndexError:
                            pass
                    else:
                        self.err_unknown_message(addr)
                else:
                    print(f"LOG: {addr} adresinden beklenmeyen sıra numarası. Beklenen: {expected_seq}, gelen: {seq_num}")
                
            elif packet_type == "end":
                print(f"LOG: Bağlantı kapatıldı: {addr}.")
                if addr in self.client_info:
                    del self.client_info[addr]

            if addr in self.client_info:
                ack_seq_num = self.client_info[addr] + 1
                ack_packet = util.make_packet('ack', ack_seq_num, '')
                print(f"LOG: Gelen pakete karşılık {addr} adresine ACK gönderildi: {ack_packet}")
                self.sock.sendto(ack_packet.encode(), addr)

        except ValueError:
            print(f"LOG: {addr} adresinden gelen paket işlenirken hata: Hatalı biçimlendirilmiş paket")
        except Exception as e:
            print(f"LOG: {addr} adresinden gelen paket işlenirken beklenmeyen bir hata oluştu: {e}")


    def join(self, username, addr):
        '''
        This method is used to join the server
        '''
        # check if server is full
        if len(self.clients) >= util.MAX_NUM_CLIENTS:
            # send error message to the client
            error_message = util.make_message("ERR_SERVER_FULL", 2)
            packet_to_send = util.make_packet("data", 0, error_message)
            print(f"LOG: Gönderiliyor {addr}: {packet_to_send}")
            self.sock.sendto(packet_to_send.encode(), addr)
            # print disonnect message to server
            
        elif username in self.clients.values():
            # send error message to the client if username is already taken
            error_message = util.make_message("ERR_USERNAME_UNAVAILABLE", 2)
            packet_to_send = util.make_packet("data", 0, error_message)
            print(f"LOG: Gönderiliyor {addr}: {packet_to_send}")
            self.sock.sendto(packet_to_send.encode(), addr)
            # print disonnect message to server
            
        else:
            # add the client to the clients dictionary
            self.clients[addr] = username
            # send successful join message to the client
            print(f"LOG: join: {username}")

    
    def request_users_list(self, username, addr):
        '''
        This method is used to request the list of active users
        '''
        # get the list of users sorted A - Z
        user_list = ', '.join(sorted(self.clients.values()))
        # send the list of users to the client
        response_msg = util.make_message("RESPONSE_USERS_LIST", 3, user_list)
        response_packet = util.make_packet("data", 0, response_msg)
        print(f"LOG: Gönderiliyor {addr}: {response_packet}")
        self.sock.sendto(response_packet.encode(), addr)
        # print the request_users_list message to the server
        print(f"LOG: request_users_list: {username}")

    
    def send_message(self, sender, active_users, message):
        '''
        This method is used to send a message to active users
        '''
        # send the message to the active users
        for user in active_users:
            # check if the user is in the clients dictionary
            if user in self.clients.values():
                # get the address of the recipient
                recipient_address = [addr for addr, username in self.clients.items() if username == user]
                # send the message to the recipient
                for rec_addr in recipient_address:
                    packet_to_send = util.make_packet("data", 0, message)
                    print(f"LOG: Gönderiliyor {rec_addr}: {packet_to_send}")
                    self.sock.sendto(packet_to_send.encode(), rec_addr)
            else:
                # print the error message to the server
                print(f"LOG: msj: {sender} -> var olmayan kullanıcı {user}")

    
    def err_unknown_message(self, addr):
        '''
        This method is used to handle errors
        '''
        error_message = util.make_message("ERR_UNKNOWN_MESSAGE", 2)
        packet_to_send = util.make_packet("data", 0, error_message)
        print(f"LOG: Gönderiliyor {addr}: {packet_to_send}")
        self.sock.sendto(packet_to_send.encode(), addr)
        if addr in self.clients:
            # delete the client from the clients dictionary
            del self.clients[addr]
            # print the disconnect message to the server
            print("LOG: disconnected: server received an unknown message")


if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our module completion
        '''
        print("Server")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW | --window=WINDOW The window size, default is 3")
        print("-h | --help Print this help")

    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "p:a:w", ["port=", "address=","window="])
    except getopt.GetoptError:
        helper()
        exit()

    PORT = 15000
    DEST = "localhost"
    WINDOW = 3

    for o, a in OPTS:
        if o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW = a

    SERVER = Server(DEST, PORT,WINDOW)
    try:
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
