'''
This module defines the behaviour of a client in the Chat Application
Enhanced with Performance Monitoring
'''
import sys
import getopt
import socket
import random
from threading import Thread, Lock, Event
import os
import util
import time
from performance_monitor import performance_monitor

# Constants for retransmission logic
RETRY_TIMEOUT = 0.5  # 500ms
MAX_RETRIES = 5

class Client:
    # Define a global variable for the available commands
    HELP_MESSAGE = """
Available commands:
|  msg <number_of_users> <username1> <username2> ... <message> - Send a message to users
|  list - List All Active Users
|  help - Display this help page
|  perf - Show performance statistics
|  perf_report - Show detailed performance report
|  perf_reset - Reset performance statistics
|  quit - Disconnect and quit the application
"""

    def __init__(self, username, dest, port, window_size, on_message=None):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.name = username
        self.active = True
        self.seq_num = 0
        self.on_message = on_message
        self.pending_packets = {}
        self.pending_packets_lock = Lock()
        self.packet_updated = Event()
        self.forward = False
        self.data = ""
        self.user = ""
        self.my_username= ""
        self.recv_seq_num = -1
        self.current_message = {}
        self.ack_check = 0
        self.msg_start = 0
        self.msg_buffer = 0
        self.msg_seq_nums =[]

        # Performance monitoring
        self.perf_monitor = performance_monitor

    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message.
        Use make_message() and make_util() functions from util.py to make your first join packet
        Waits for userinput and then process it
        '''
        # send join message to server
        self.join()

        # start new threads to handle incoming messages and retransmissions
        Thread(target=self.receive_handler, daemon=True).start()
        Thread(target=self.retransmission_handler, daemon=True).start()
        
        try:
            while self.active:
                command = input()
                if command.lower() == 'quit':
                    # send disconnect message to server
                    time.sleep(1)
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
                elif command.lower() == 'perf':
                    # show current performance stats
                    self.show_performance_stats()
                elif command.lower() == 'perf_report':
                    # show detailed performance report
                    print(self.perf_monitor.get_performance_report())
                elif command.lower() == 'perf_reset':
                    # reset performance statistics
                    self.perf_monitor.reset_stats()
                    print("Performans istatistikleri sıfırlandı.")
                else:
                    # print message for incorrect user input
                    print("incorrect userinput format")
                if not self.active:
                    # break the loop if the client is no longer active
                    break
        finally:
            # stop performance monitoring
            self.perf_monitor.stop_monitoring()
            # close the socket
            self.sock.close()

    def show_performance_stats(self):
        """Display current performance statistics"""
        stats = self.perf_monitor.get_current_stats()
        print(f"""
=== PERFORMANS İSTATİSTİKLERİ ===
Oturum süresi: {stats['session_duration']:.1f}s
Gönderilen mesaj: {stats['total_messages_sent']}
Alınan mesaj: {stats['total_messages_received']}
Ortalama gecikme: {stats.get('avg_latency_ms', 0):.1f}ms
Mesaj/saniye: {stats['messages_per_second']:.1f}
Paket kaybı: {stats['packet_loss_rate']:.1f}%
        """)
        
        # Optimizasyon önerileri
        suggestions = self.perf_monitor.get_optimization_suggestions()
        if suggestions:
            print("\n=== OPTİMİZASYON ÖNERİLERİ ===")
            for suggestion in suggestions:
                print(suggestion)

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
                receive_time = time.time()
                data, _ = self.sock.recvfrom(1024)  
                packet_type, seq_num_str, message, _ = util.parse_packet(data.decode())

                # Record received message for performance monitoring
                self.perf_monitor.record_message_received(int(seq_num_str), len(data), receive_time)

                if packet_type == 'ack':
                    ack_seq_num = int(seq_num_str)
                    acked_packet_seq = ack_seq_num - 1
                    with self.pending_packets_lock:
                        if acked_packet_seq in self.pending_packets:
                            del self.pending_packets[acked_packet_seq]
                    continue

                self.error_handler(message)

                if self.active is False:
                    break

                if "RESPONSE_USERS_LIST" in message:
                    # split the message into parts
                    message_parts = message.split()
                    if len(message_parts) <= 2:
                        # print message to server for unknown message
                        self._show_message("ERROR: Received incorrectly formatted RESPONSE_USERS_LIST message.")
                        break
                    else:
                        # get the list of users
                        users = ' '.join(message_parts[2:])
                        # print the list of users
                        self._show_message(f"list: {users.replace(', ', ' ')}")
                else:
                    # split the message into parts
                    message_parts = message.split(' ', 2)
                    if len(message_parts) <= 2:
                        # print message to server for unknown message
                        self._show_message("ERROR: Received incorrectly formatted message.")
                        break
                    else:
                        _, _, content = message_parts
                        # print the message
                        self._show_message("msg: " + content)

            except Exception as e:
                break

    def _show_message(self, message):
        if self.on_message:
            self.on_message(message)
        else:
            print(message)

    def _send_reliable_packet(self, packet):
        """Helper function to send a packet and add it to the pending list."""
        with self.pending_packets_lock:
            seq_num_str, _ = packet.split('|', 2)[1:3]
            seq_num = int(seq_num_str)
            self.pending_packets[seq_num] = (packet, time.time(), 0) # packet, sent_time, retry_count
        
        # Record sent message for performance monitoring
        send_time = time.time()
        packet_size = len(packet.encode())
        self.perf_monitor.record_message_sent(seq_num, packet_size, send_time)
        
        self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))

    def join(self):
        '''
        Send a JOIN message to the server
        '''
        join_message = util.make_message("join", 1, self.name)
        join_packet = util.make_packet("data", self.seq_num, join_message)
        self._send_reliable_packet(join_packet)
        self.seq_num += 1
        return

    def quit(self):
        '''
        Send a QUIT message to the server
        '''
        disconnect_message = util.make_message("disconnect", 1, self.name)
        disconnect_message_packet = util.make_packet("data", self.seq_num, disconnect_message)
        self._send_reliable_packet(disconnect_message_packet)
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
            self._send_reliable_packet(message_packet)
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
        self._send_reliable_packet(list_message_packet)
        self.seq_num += 1
        return

    def retransmission_handler(self):
        """
        Periodically checks for packets that have not been acknowledged and retransmits them.
        """
        while self.active:
            time.sleep(RETRY_TIMEOUT)
            
            with self.pending_packets_lock:
                current_time = time.time()
                # Iterate over a copy of items, as we might modify the dict
                for seq_num, (packet, sent_time, retry_count) in list(self.pending_packets.items()):
                    if current_time - sent_time > RETRY_TIMEOUT:
                        if retry_count >= MAX_RETRIES:
                            # Too many retries, server is likely down
                            self._show_message("Server not responding. Disconnecting.")
                            self.active = False
                            # No need to remove from dict, the client will shut down
                            break
                        else:
                            # Retransmit
                            self._show_message(f"Timeout for packet {seq_num}. Retrying... ({retry_count + 1})")
                            
                            # Record retransmission for performance monitoring
                            self.perf_monitor.record_retransmission(seq_num)
                            
                            self.sock.sendto(packet.encode(), (self.server_addr, self.server_port))
                            # Update the packet's info in the dict
                            self.pending_packets[seq_num] = (packet, current_time, retry_count + 1)
            if not self.active:
                self.sock.close()
                break

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