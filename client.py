import socket
import argparse
import sys
import select
import threading
from datetime import datetime
import queue

class Client:
    def __init__(self, host: str, port: int) -> None:
        #Create socket object
        self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.vote_queue = queue.Queue()
        self.voting_in_process = False
        # self.prompt_user_input_event = threading.Event()

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
    
    def user_requests(self, request):
        if request == "quit":
            self.send_request("quit")
            print("Client closed.")
        elif self.check_error_command(request) == 0:
            self.send_request(request)
        elif request == "":
            return
        else:
            print("Error: Invalid input. Please provide a valid command.")
    
    
    def handle_user_input(self):
        while True:
            print("Enter a command ('gen <parameter>', 'quit' or enter to refresh for proposed image):\n")
            request = input("")
            self.user_requests(request)

            
            if self.voting_in_process:
                print(f"Send Y/N to vote to mint this image:")
                vote = input("").upper()
                timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                vote_message = f"Vote: {vote}, Timestamp: {timestamp}"
                self.send_request(vote)
                self.voting_in_process = False

    def receive_response(self):
        while True:
            try: 
                response = self.clientsocket.recv(1024).decode().strip()
                if not response:
                    print(f"No response from server")
                    break
                elif "ImageURL" in response:
                    print(response)
                    self.voting_in_process = True
                elif "Reconnect" in response:
                    self.voting_in_process = True
                elif "Vote Ended" in response:
                    print(response)
                    self.voting_in_process = False

                else:
                    print(response)
                    
            except Exception as e:
                break 


    def run(self) -> None:

        try: 
            # Connect to the server
            self.clientsocket.connect((self.host, self.port))
            # self.prompt_user_input_event.set()
        
            listen_thread = threading.Thread(target=self.receive_response)
            listen_thread.start()

            user_input_thread = threading.Thread(target=self.handle_user_input)
            user_input_thread.start()

            # Wait for both threads to finish
            listen_thread.join()
            user_input_thread.join()

        except Exception:
            return 
        
        # Close the client socket
        self.clientsocket.close()
        print("Client closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Client Info')
    parser.add_argument('--hosts', nargs='+', type=str, help='IPV4 Host')
    parser.add_argument('--ports', nargs='+', type=int, help='Port for connection')
    args = parser.parse_args()

    for host, port in zip(args.hosts, args.ports):
        print('Connecting to new server: ', host, port)
        client = Client(host=host, port=port)
        client.run()
    

