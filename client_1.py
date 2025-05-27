'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import os
import util

'''
Write your code inside this class. 
In the start() function, you will read user-input and act accordingly.
receive_handler() function is active another thread and you have to listen 
for incoming messages in this function.
'''


class Client:
    '''
    This is the main Client Class.
    '''
    # Define a global variable for the available commands
    HELP_MESSAGE = """
Available commands:
|  msg <number_of_users> <username1> <username2> ... <message> - Send a message to users
|  list - List All Active Users
|  help - Display this help page
|  quit - Disconnect and quit the application
"""

    def __init__(self, username, dest, port, window_size):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.name = username
        self.active = True
        self.seq_num = 0

    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message.
        Use make_message() and make_util() functions from util.py to make your first join packet
        Waits for userinput and then process it
        '''
        # send join message to server
        self.join()

        # start a new thread to handle incoming messages
        Thread(target=self.receive_handler, daemon=True).start()
        try:
            while self.active:
                command = input()
                if command.lower() == 'quit':
                    # send disconnect message to server
                    self.quit()

                elif command.startswith('msg'):
                    # send message to server
                    self.msg(command)

                elif command.lower() == 'list':
                    # send request to server for list of users
                    self.list()

                elif command.lower() == 'help':
                    # print help message
                    print(self.HELP_MESSAGE)
                else:
                    # print message for incorrect user input
                    print("incorrect userinput format")
                if not self.active:
                    # break the loop if the client is no longer active
                    break
        finally:
            # close the socket
            self.sock.close()


    def error_handler(self, message):
        '''
        Handle error messages from the server
        '''
        # check for error recieved from server or user list response
        if "ERR_SERVER_FULL" in message:
            # print disonnect message to server for server full
            print("disconnected: server full")
            self.active = False
            self.sock.close()
        elif "ERR_USERNAME_UNAVAILABLE" in message:
            # print disonnect message to server for username not available
            print("disconnected: username not available")
            self.active = False
            self.sock.close()
        elif "ERR_UNKNOWN_MESSAGE" in message:
            # print disonnect message to server for unknown message
            print("disconnected: server received an unknown message")
            self.active = False
            self.sock.close()


    def receive_handler(self):
        '''
        Waits for a message from the server and processes it accordingly
        '''
        while self.active:
            try:
                # receive data from the server
                data, _ = self.sock.recvfrom(1024)  
                _, _, message, _ = util.parse_packet(data.decode())

                self.error_handler(message)

                if self.active is False:
                    break

                if "RESPONSE_USERS_LIST" in message:
                    # split the message into parts
                    message_parts = message.split()
                    if len(message_parts) <= 2:
                        # print message to server for unknown message
                        print("ERROR: Received incorrectly formatted RESPONSE_USERS_LIST message.")
                        break
                    else:
                        # get the list of users
                        users = ' '.join(message_parts[2:])
                        # print the list of users
                        print(f"list: {users.replace(', ', ' ')}")
                else:
                    # split the message into parts
                    message_parts = message.split(' ', 2)
                    if len(message_parts) <= 2:
                        # print message to server for unknown message
                        print("ERROR: Received incorrectly formatted message.")
                        break
                    else:
                        _, _, content = message_parts
                        # print the message
                        print("msg: " + content)

            except Exception as e:
                break


    def join(self):
        '''
        Send a JOIN message to the server
        '''
        join_message = util.make_message("join", 1, self.name)
        join_packet = util.make_packet("data", self.seq_num, join_message)
        self.sock.sendto(join_packet.encode(), (self.server_addr, self.server_port))
        return


    def quit(self):
        '''
        Send a QUIT message to the server
        '''
        disconnect_message = util.make_message("disconnect", 1, self.name)
        disconnect_message_packet = util.make_packet("data", self.seq_num, disconnect_message)
        self.sock.sendto(disconnect_message_packet.encode(), (self.server_addr, self.server_port))
        self.active = False
        print("quitting")
        return


    def msg(self, message):
        ''''
        Send a message to the server
        '''
        try:
            parts = message.split(' ', 1)
            user_list, text = parts[1].split(' ', 1)
            users = user_list.split(',')
            num_users = len(users)
            user_message_part = f"{num_users} " + " ".join(users) + " " + text
            user_msg_message = util.make_message('send_message', 4, user_message_part)
            message_packet = util.make_packet("data", self.seq_num, user_msg_message)
            self.sock.sendto(message_packet.encode(), (self.server_addr, self.server_port))
            self.seq_num += 1
            return
        except (ValueError, IndexError):
            print("incorrect userinput format")
            return

    
    def list(self):
        '''
        Send a LIST message to the server
        '''
        # send request to server for list of users
        list_message = util.make_message("request_users_list", 2)
        list_message_packet = util.make_packet("data", self.seq_num, list_message)
        self.sock.sendto(list_message_packet.encode(), (self.server_addr, self.server_port))
        return


# Do not change below part of code
if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our Client module completion
        '''
        print("Client")
        print("-u username | --user=username The username of Client")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW_SIZE | --window=WINDOW_SIZE The window_size, defaults to 3")
        print("-h | --help Print this help")


    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "u:p:a:w", ["user=", "port=", "address=", "window="])
    except getopt.error:
        helper()
        exit(1)

    PORT = 15000
    DEST = "localhost"
    USER_NAME = None
    WINDOW_SIZE = 3
    for o, a in OPTS:
        if o in ("-u", "--user="):
            USER_NAME = a
        elif o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW_SIZE = a

    if USER_NAME is None:
        print("Missing Username.")
        helper()
        exit(1)

    S = Client(USER_NAME, DEST, PORT, WINDOW_SIZE)
    try:
        # Start receiving Messages
        T = Thread(target=S.receive_handler)
        T.daemon = True
        T.start()
        # Start Client
        S.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()