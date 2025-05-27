# Chat Application - with Reliable UDP
This repository contains the implementation of a chat application that uses UDP for message transmission and incorporates a custom reliable transport protocol to ensure message delivery. Ack. - This project was completed as part of a University programming assignment

## Description 
The chat application allows users to connect to a central server and exchange messages with other users. The server keeps track of all active clients and forwards messages between them. The project is divided into two main parts:
Part 1. A simple chat application using UDP, where basic messaging functionality is implemented.
Part 2. Enhancements to the chat application to include sequences, acknowledgements, and handling of packet loss to ensure reliable communication, similar to TCP.

## Features 
- Server: Handles client connections, manages active users, forwards messages, and ensures reliable delivery using custom protocol enhancements.
- Client: Connects to the server, sends and receives messages, and provides user commands for listing active users, sending messages, and disconnecting.
- Reliable Communication: Implements sequences, acknowledgements, and retransmissions to handle packet loss and ensure message delivery.

## Installation and Usage 
### Prerequisites 
- Python 3.6 or higher
- Linux/MacOS (Recommended) or Windows with WSL
### Running the server:
1. Start the server
  - python3 server_1.py -p <port_num>
### Running clients
1. Start the Client
  - python3 client_1.py -p <server_port_num> -u <username>
  
### Commands 
- Send Message: msg <number_of_users> <username1> <username2> ... <message>
- List Users: list
- Help: help
- Quit: quit

### Testing
To test the implementation, use the provided test scripts:
python3 TestPart1.py
python3 TestPart2.1.py
python3 TestPart2.2.py

#### Project Structure
- server_1.py: Server-side code for Part 1
- client_1.py: Client-side code for Part 1
- server_2.py: Server-side code for Part 2
- client_2.py: Client-side code for Part 2
- util.py: Utility functions and constants
- TestPart1.py: Test cases for Part 1
- TestPart2.1.py: Test cases for Part 2.1
- TestPart2.2.py: Test cases for Part 2.2

#### Technologies Used
- Python 3
- Socket Programming
- UDP
- Threading



