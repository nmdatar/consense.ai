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
        self.generate_available = 0
        self.image_votes = {}
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

        # Change primary_host etc if it is a secondary server
        if not self.primary:
            self.primary_host = primary_host
            self.primary_port = primary_port
        else:
            self.primary_host = self.host
            self.primary_port = self.await_port

        self.backup_servers = {}
        
        print(f"Server started on {self.host}:{self.port}")

    def maintain_heartbeat_socket(self) -> None:
        self.internal = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.internal.bind((self.host, self.internal_port))
        self.internal.listen(5)

        while True:
            heartbeat_server, addr = self.internal.accept()
            heartbeat_server.close()

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

    def send_image(self, prompt, client) -> None:
        try:
            self.generate_available = 1
            image_response = self.generate_image(prompt=prompt)
            image_url = image_response['data'][0]['url']
            print("Generated image URL:", image_url)
            self.send_to_all_clients(image_url)
            print(f"shared image to", [client.getpeername() for client in self.clients])
        except Exception as e:
            print("Exception:", e)
            self.send_to_all_clients(f"Error: {e}")

    def send_to_all_clients(self, message: str) -> None:
        for client in self.clients:
            try:
                client.send(message.encode()) 
            except (BrokenPipeError, OSError):
                print(f"Failed to send message to client {client.getpeername()}. Removing from clients list.")
                client.close()
                self.clients.pop(client)

    def handle_client(self, client) -> None:
        addr = client.getpeername()
        self.clients[client] = "active"
        print("waiting for responses")
        while True:
            try:
                request = client.recv(1024).decode().strip()
            except OSError:
                break
            if request == "quit":
                self.clients.pop(client)
                print(f"Client {client} disconnected")
            elif request[:3] == "gen":
                self.clients[client] = "active"
                prompt = request
                self.send_image(prompt, client)
                print(f"Received prompt: {prompt}")

    
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