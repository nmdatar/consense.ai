import socket
import argparse
import sys
import select
import threading

class Client:
    def __init__(self) -> None:
        #Create socket object
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = 'localhost'
        port = 8000
        # Connect to the server
        self.clientsocket.connect((host, port))

    # check for error in command line prompt
    def check_error_command(self, request: str):
        request = request.split()
        errno = 0
        if len(request) == 0:
            errno = 1
        elif request[0] == "gen":
            if len(request) < 2:
                errno = 1
        
        return errno

    def send_request(self, request: str):
        self.clientsocket.send(request.encode())

    def receive_response(self):
        while True:
            response = self.clientsocket.recv(1024).decode()
            print("Image URL: ", response)
            return response

    def run(self):
        listen_thread = threading.Thread(target=self.receive_response)
        listen_thread.start()

        while True:
            request = input("Enter a command (gen <parameter>, 'quit' to quit): ")
            
            # Exit the loop and close the client socket
            if request == "quit": 
                self.send_request("quit")
                self.clientsocket.close()
                print("Client closed.")
                break
            elif self.check_error_command(request) == 0:
                self.send_request(request)
            else:
                print("Error: Invalid input. Please provide a valid command.")


if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description='Send a request to the server to generate an image.')
    # parser.add_argument('request', type=str, help='The request to send to the server, e.g., "gen white cat".')
    # args = parser.parse_args()

    client = Client()
    client.run()
    

