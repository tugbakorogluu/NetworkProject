'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util


class Server:
    '''
    This is the main Server Class. You will  write Server code inside this class.
    '''
    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))
        self.clients = {}

    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it
        '''
        try:
            while True:
                # receive data from client
                data, addr = self.sock.recvfrom(1024) 
                # parse the packet
                type, seq_no, message, _ = util.parse_packet(data.decode())
                # process the message
                if type == 'data':
                    # split the message into parts
                    message_parts = message.split()
                    # get the command
                    command = message_parts[0]

                    if command == "join":
                        # get the username
                        username = message_parts[2]  
                        self.join(username, addr)

                    elif command == "request_users_list":
                        # check if the address is in the clients dictionary
                        if addr not in self.clients:
                            # send error message to the server
                            print("Error: Address not recognized")
                        else:
                            # request the list of active users
                            self.request_users_list(self.clients[addr], addr)

                    elif command == "send_message":
                        try:
                            # get the number of active users
                            num_active_users = int(message_parts[3])
                            # get the list of active users
                            active_users = message_parts[4:4 + num_active_users]
                            # get the message text
                            text = ' '.join(message_parts[4 + num_active_users:])
                            # get the sender
                            sender = self.clients.get(addr, "Unknown")
                            # create the forward message
                            forward_message_content = f"{sender}: {text}"
                            forward_message = util.make_message('msg', 4, forward_message_content)
                            # print the message to the server
                            print(f"msg: {sender}")
                            # forward the message to the active users
                            self.send_message(sender, active_users, forward_message)

                        except IndexError:
                            # handle index error
                            pass
                        except ValueError:
                           # handle value error
                           pass

                    elif command == "disconnect":
                        try:
                            # get the username
                            username = message_parts[2]
                            # check if the address is in the clients dictionary
                            if addr in self.clients:
                                # delete the client from the clients dictionary
                                del self.clients[addr]
                                # print the disconnect message to the server
                                print(f"disconnected: {username}")
                            else:
                                # print the error message to the server
                                print(f"disconnect attempted by non-existent or already disconnected user: {username}")
                        except IndexError:
                            # handle index error
                            pass
                    else:
                        # handle unknown message
                        self.err_unknown_message(addr)


        except KeyboardInterrupt:
            self.sock.close()
        except Exception as e:
            self.sock.close()


    def join(self, username, addr):
        '''
        This method is used to join the server
        '''
        # check if server is full
        if len(self.clients) >= util.MAX_NUM_CLIENTS:
            # send error message to the client
            error_message = util.make_message("ERR_SERVER_FULL", 2)
            self.sock.sendto(util.make_packet("data", 0, error_message).encode(), addr)
            # print disonnect message to server
            print("disconnected: server full")
        elif username in self.clients.values():
            # send error message to the client if username is already taken
            error_message = util.make_message("ERR_USERNAME_UNAVAILABLE", 2)
            self.sock.sendto(util.make_packet("data", 0, error_message).encode(), addr)
            # print disonnect message to server
            print("disconnected: username not available")
        else:
            # add the client to the clients dictionary
            self.clients[addr] = username
            # send successful join message to the client
            print(f"join: {username}")

    
    def request_users_list(self, username, addr):
        '''
        This method is used to request the list of active users
        '''
        # get the list of users sorted A - Z
        user_list = ', '.join(sorted(self.clients.values()))
        # send the list of users to the client
        response_msg = util.make_message("RESPONSE_USERS_LIST", 3, user_list)
        response_packet = util.make_packet("data", 0, response_msg).encode()
        self.sock.sendto(response_packet, addr)
        # print the request_users_list message to the server
        print(f"request_users_list: {username}")

    
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
                    self.sock.sendto(util.make_packet("data", 0, message).encode(), rec_addr)
            else:
                # print the error message to the server
                print(f"msg: {sender} to non-existent user {user}")

    
    def err_unknown_message(self, addr):
        '''
        This method is used to handle errors
        '''
        error_message = util.make_message("ERR_UNKNOWN_MESSAGE", 2)
        self.sock.sendto(util.make_packet("data", 0, error_message).encode(), addr)
        if addr in self.clients:
            # delete the client from the clients dictionary
            del self.clients[addr]
            # print the disconnect message to the server
            print("disconnected: server received an unknown message")


# Do not change below part of code
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

