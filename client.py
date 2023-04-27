import socket
import argparse
import sys
import select

class Client:
    def __init__(self) -> None:
        #Create socket object
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host = 'localhost'
        port = 8000
        # Connect to the server
        self.clientsocket.connect((host, port))

    # check for error in command line prompt
    def check_error_command(self, request_type: str, request: str):
        request = request.split()
        errno = 0
        commands = ["gen"]
        if len(request) == 0 or request[0] not in commands:
            errno = 1

        elif request[0] == "gen":
            if len(request) < 2:
                errno = 1
        
        return errno

    def send_request(self, request: str):
        self.clientsocket.send(request.encode())

    def receive_response(self):
        response = self.clientsocket.recv(1024).decode()
        return response

    def run(self, request: str):
        while True:
            error_code = self.check_error_command("gen", request)
            if error_code != 0:
                print("Error: Invalid input. Please provide a valid command.")
                
            elif request == "exit": # Exit the loop and close the client socket
                self.clientsocket.close()
                print("Client closed.")
                break
            else:
                self.send_request(request)
                response = self.receive_response()
                print("Image URL: ", response)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Send a request to the server to generate an image.')
    parser.add_argument('request', type=str, help='The request to send to the server, e.g., "gen white cat".')
    args = parser.parse_args()

    client = Client()
    client.run(args.request)
    

