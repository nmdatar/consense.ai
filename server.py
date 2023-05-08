import openai
from dotenv import load_dotenv
import os
import argparse
from typing import List, Dict, Tuple
import requests
# import ipfshttpclient
import socket
import threading
import json
import time
import csv
from datetime import datetime

load_dotenv()

class Server:
    def __init__(self, host: str, port: int = 8000, id: int = 1, primary: bool = True, primary_host : str = 'localhost', primary_port : int = 8003) -> None:
        self.host = host
        self.port = port
        self.id = id
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.API_KEY = openai.api_key
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        self.clients = {}
        self.generate_available = True
        self.vote_available = False
        self.vote_count = {"Y":0, "N":0}
        self.primary = primary
        self.internal_port = self.port + 1
        
        self.receive_port = self.port + 2
        self.receive = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.await_port = self.port + 3
        self.await_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.await_socket.bind((self.host, self.await_port))
        self.await_socket.listen(5)
        self.receive.bind((self.host, self.receive_port))
        self.receive.listen(5)
        self.image_url = ""

        # Change primary_host etc if it is a secondary server
        if not self.primary:
            self.primary_host = primary_host
            self.primary_port = primary_port
        else:
            self.primary_host = self.host
            self.primary_port = self.await_port

        self.backup_servers = {}
        
        print(f"Server started on {self.host}:{self.port}")

    def append_new_client_log(self, client):
        with open('log.csv', mode='a') as log_file:
            fieldnames = ['timestamp', 'image_url', 'Y', 'N']
            writer = csv.DictWriter(log_file, fieldnames=fieldnames)

            if log_file.tell() == 0:  # Check if the file is empty
                writer.writeheader()

            writer.writerow(client)


    def append_log_entry(self, Y, N):
        print("hi")
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'image_url':  self.image_url,
            'Y': Y,
            'N': N
        }

        with open('log.csv', mode='a') as log_file:
            fieldnames = ['timestamp', 'image_url', 'Y', 'N']
            writer = csv.DictWriter(log_file, fieldnames=fieldnames)

            if log_file.tell() == 0:  # Check if the file is empty
                writer.writeheader()

            writer.writerow(log_entry)

    def clear_log_file(self):
        try:
            with open('log.csv', 'w') as log_file:
                pass
            print(f"Log file 'log.csv' has been cleared.")
        except Exception as e:
            print(f"Error clearing the log file 'log.csv': {e}")

    def maintain_heartbeat_socket(self) -> None:
        self.internal = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.internal.bind((self.host, self.internal_port))
        self.internal.listen(5)

        while True:
            heartbeat_server, addr = self.internal.accept()
            heartbeat_server.close()
    
    def initialize_states(self):
        with open("log.csv", "r") as file:
            reader = csv.reader(file)
            last_row = None
            for row in reader:
                last_row = row
            if last_row is None:
                return None
            else:
                self.image_url = last_row[1]
                self.vote_count = {"Y":last_row[2], "N":last_row[3]}


    def await_servers(self) -> None:
        while True:
            try: 
                new_server, addr = self.await_socket.accept()
                data = b''
                while True:
                    
                    chunk = new_server.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                print('Received all data from connecting server')
                data = data.decode()
                msg = json.loads(data)
                id = msg.pop('id')
                self.backup_servers[id] = msg
                self.update_backups()

            except Exception:
                break
        

    def update_backups(self) -> None:
        msg = {}
        if self.id in self.backup_servers.keys():
            self.backup_servers.pop(self.id)
        msg['backup_servers'] = self.backup_servers
        msg['primary_host'] = self.host
        msg['primary_port'] = self.internal_port
        msg = json.dumps(msg)
        
        for backup in self.backup_servers.values():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                host = backup['host']
                port = backup['receive_port']
                s.connect((host, port))
                s.sendall(msg.encode())
                s.close()

    def receive_updates(self) -> None:
        while not self.primary:
            
            try:
                main_server, addr = self.receive.accept()
                
                data = b''
                while True:
                    chunk = main_server.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                
                if data.startswith(b'timestamp'):  # Check if it's a CSV file
                    with open('log.csv', 'wb') as log_file:
                        log_file.write(data)
                else:
                    data = data.decode()
                    msg = json.loads(data)
                
                self.primary_host = msg['primary_host']
                self.primary_port = msg['primary_port']
                self.backup_servers = msg['backup_servers']
                
            except Exception:
                break

        return 
    
    def heartbeat(self) -> None:
        while True:
            if not self.primary:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        s.connect((self.primary_host, self.primary_port))
                        s.close()
                except Exception as e:

                    if self.id == int(min(self.backup_servers.keys())):
                        print("Taking Over ;)")
                        self.backup_servers.pop(str(self.id))
                        self.primary = True
                        self.primary_host = self.host
                        self.primary_port = self.internal_port
                        self.update_backups()
                        await_thread = threading.Thread(target=self.await_servers)
                        await_thread.start()
                        maintain_heartbeat_thread = threading.Thread(target=self.maintain_heartbeat_socket)
                        maintain_heartbeat_thread.start()
                        self.initialize_states()
                        print("previous info",self.image_url, self.vote_count)
                        self.reconnect()
                        return 
                        
                    else:
                        print('Connected to new master: ', self.primary_host, self.primary_port)
                        time.sleep(2)

            time.sleep(2)
        
    
    def generate_image(self, prompt: str) -> Dict:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="256x256"
        )
        return response

    def send_image(self, prompt, client):
        if self.generate_available == True:
            print(f"Received prompt: {prompt}")
            self.generate_available = False
            try:
                image_response = self.generate_image(prompt)
                self.image_url = image_response['data'][0]['url']
                print("Generated image URL:", self.image_url)
                self.append_log_entry("NONE", "NONE") 
                self.send_log_to_backup_servers()
                self.send_to_all_clients(f"ImageURL: {self.image_url}\n " )
                print(f"Shared image to", [client.getpeername() for client in self.clients])
            except Exception as e: 
                print("Exception:", e)
                self.send_to_all_clients(f"Error: {e}")
        else:
            print(f"Prompt rejected. Another image is generating")
            self.send_client(f"Prompt rejected. Another image is generating")

    def send_to_all_clients(self, message: str):
        for client in self.clients:
            try:
                client.send(message.encode()) 
            except BrokenPipeError:
                try:
                    peername = client.getpeername()
                    print(f"Failed to send message to client {peername}. Removing from clients list.")
                except OSError:
                    print("Failed to get client peer name. Removing from clients list.")
                self.clients.pop(client)
                client.close()

    def process_vote(self, message: str, client) -> None:
        vote = message[0]
        # timestamp = message[2]
        message = f"Received vote: {vote} from {client.getpeername()}"
        self.send_to_all_clients(f"Received vote: {vote} from {client.getpeername()}")
        self.append_log_entry(self.vote_count["Y"], self.vote_count["N"])
        self.send_log_to_backup_servers()
        # message = f"Received vote: {vote}, Timestamp: {timestamp} from {client.getpeername()}"
        print(message)
        self.generate_available = True
        return message 

    def reset_votes(self):
        self.vote_count = {"Y": 0, "N": 0}
        self.voting_end = False
    

    def send_client(self, client):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                host = backup['host']
                port = backup['receive_port']
                s.connect((host, port))
                s.sendall(client)
                s.close()

    def send_client_to_backup_servers(self, client) -> None:
        for backup in self.backup_servers.values():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                host = backup['host']
                port = backup['receive_port']
                s.connect((host, port))
                s.sendall(client)
                s.close()

    def send_log_to_backup_servers(self) -> None:
        with open('log.csv', 'rb') as log_file:
            log_data = log_file.read()

        for backup in self.backup_servers.values():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    host = backup['host']
                    port = backup['receive_port']
                    s.connect((host, port))
                    s.sendall(log_data)
                    s.close()
            except Exception as e:
                print(f"Failed to send log to backup server ({host}:{port}): {e}")
    
    def compile_vote(self):
        if (self.vote_count["Y"] + self.vote_count["N"]) == len(self.clients):
                    self.voting_end = True
                    Y = self.vote_count["Y"]
                    N = self.vote_count["N"]
                    if Y > N:
                        message = f"Voting end. Results: 'Y:'{Y}, N:{N}. Image will be minted"
                    elif N > Y:
                        message = f"Voting end. Results: 'Y:'{Y}, N:{N}. Image will not be minted"
                    elif N == Y:
                        message = f"Voting end. Results: 'Y:'{Y}, N:{N}. Image will not be minted"
                    print(message)
                    self.send_to_all_clients(message)
                    self.reset_votes()  
                    self.vote_available = False 

                    if self.primary:
                        self.append_log_entry(Y, N)
                        self.send_log_to_backup_servers()
                    self.clear_log_file()

    def handle_client(self, client) -> None:
        addr = client.getpeername()

        while True:
            try:
                request = client.recv(1024).decode().strip()
            except OSError:
                self.send_to_all_clients(f"invalid request")
                break
            if request == "quit":
                self.clients.pop(client)
                print(f"Client {client} disconnected")
            elif request.startswith('gen'):
                self.send_image(request, client)
                self.vote_available = True
            if request in ["Y", "N"]:
                if self.vote_available == True:
                    self.vote_count[request] += 1
                    vote_message = self.process_vote(request, client)
                    print(self.vote_count["Y"] , self.vote_count["N"], len(self.clients))
                    self.compile_vote() 
                else:
                    self.send_client(f"Voting is currently unavailable")

    def reconnect(self):
        self.send_to_all_clients(f"Reconnect. Continue vote if you haven't voted.")
    
    def run(self) -> None:
        if self.primary:
            await_thread = threading.Thread(target=self.await_servers)
            await_thread.start()
            maintain_heartbeat_socket = threading.Thread(target=self.maintain_heartbeat_socket)
            maintain_heartbeat_socket.start()

        else:
            rec_thread = threading.Thread(target=self.receive_updates)
            rec_thread.start()

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                msg = {}
                msg['host'] = self.host
                msg['id'] = self.id
                msg['receive_port'] = self.receive_port
                msg['primary_port'] = self.internal_port
                msg = json.dumps(msg)
                s.connect((self.primary_host, self.primary_port))
                s.sendall(msg.encode())
                s.close()

            time.sleep(2)
            heartbeat_thread = threading.Thread(target=self.heartbeat)
            heartbeat_thread.start()

        while True:
            client, addr = self.server.accept()
            print(f"New connection from {addr[0]}:{addr[1]}")

            if self.primary:
                self.clients[client] = addr
                client_thread = threading.Thread(target=self.handle_client, args=(client,))
                client_thread.start()
            else: 
                print('Client connected to non-primary server!')
                msg ='Tried to connect to a non-primary server. Failed.'
                client.send(msg.encode())
                client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Server Connection")
    parser.add_argument('--host', help='IPV4 Host', type=str)
    parser.add_argument('--port', help='Port', type=int)
    parser.add_argument('--pr', help='Primary/Secondary server', action='store_true')
    parser.add_argument('--prhost', help='Primary Host', type=str)
    parser.add_argument('--prport', help='Primary Host', type=int)
    parser.add_argument('--id', help='Server ID', type=int)
    args = parser.parse_args()
    print(args)
    server = Server(host=args.host, port=args.port, primary=args.pr, id=args.id, primary_host=args.prhost, primary_port=args.prport)
    server.run()