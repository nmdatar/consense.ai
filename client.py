import socket
import argparse
import sys
import select
import threading
from rich.console import Console

class Client:
    def __init__(self, host: str, port: int) -> None:
        #Create socket object
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port


    # check for error in command line prompt
    def check_error_command(self, request: str):
        request = request.split()
        errno = 0
        if len(request) == 0:
            errno = 1
        elif request[0] == "gen":
            if len(request) < 2:
                errno = 1
        elif request[0] == "vote":
            if len(request) != 2 or request[1] not in ["Y", "N"]:
                errno = 1
        

        return errno

    def send_request(self, request: str):
        self.clientsocket.send(request.encode())

    def receive_response(self):
        while True:

            try: 
                response = self.clientsocket.recv(1024)
                if response:
                    response = response.decode()
                    print(response)
                    print('> ')
                else:
                    self.clientsocket.close()
                    
            except Exception as e:
                break 


    def run(self) -> None:

        try: 
            # Connect to the server
            self.clientsocket.connect((self.host, self.port))

        except Exception:
            return 
        
        listen_thread = threading.Thread(target=self.receive_response)
        listen_thread.start()

        while True:
            request = input("> ")

            # Check if listen_thread has ended
            if not listen_thread.is_alive():
                print("Server closed the connection.")
                # self.clientsocket.close()
                return 
            
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
    parser = argparse.ArgumentParser(description='Client Info')
    parser.add_argument('--hosts', nargs='+', type=str, help='IPV4 Host')
    parser.add_argument('--ports', nargs='+', type=int, help='Port for connection')
    args = parser.parse_args()

    for host, port in zip(args.hosts, args.ports):
        print('Connecting to new server: ', host, port)
        client = Client(host=host, port=port)
        client.run()
    


