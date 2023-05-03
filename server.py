import openai
from dotenv import load_dotenv
import os
import argparse
from typing import List, Dict, Tuple
import requests
import ipfshttpclient
import socket
import threading
import time
from datetime import datetime  


load_dotenv()

class Server:
    def __init__(self, host: str, port: int = 8000, id: int = 1) -> None:
        self.host = host
        self.port = port
        self.id = id
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.API_KEY = openai.api_key
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(5)
        self.clients = {}
        self.generate_available = 0
        self.vote_count = {"Y":0, "N":0}
        self.voting_end = False
        self.voting_start_time = None
        self.voting_duration = 30
        print(f"Server started on {host}:{port}")
    
    def generate_image(self, prompt: str) -> Dict:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="256x256"
        )
        return response

    def send_image(self, prompt, client):
        print(f"Received prompt: {prompt}")
        # print(self.generate_available)
        try:
            # self.generate_available = 1
            image_response = self.generate_image(prompt)
            image_url = image_response['data'][0]['url']
            print("Generated image URL:", image_url)
            self.send_to_all_clients(f"ImageURL: {image_url}\n Send Y/N to vote to mint this image:\n" )
            print(f"shared image to", [client.getpeername() for client in self.clients])
            # vote_count_thread = threading.Thread(target=self.send_final_vote_count)
            # vote_count_thread.start()
            # self.reset_votes()
        except Exception as e: 
            print("Exception:", e)
            self.send_to_all_clients(f"Error: {e}")

    def send_to_all_clients(self, message: str):
        for client in self.clients:
            try:
                client.send(message.encode()) 
            except (BrokenPipeError, OSError):
                print(f"Failed to send message to client {client.getpeername()}. Removing from clients list.")
                client.close()
                self.clients.pop(client)
    
    def process_vote(self, message: str, client) -> None:
        vote = message[0]
        # timestamp = message[2]
        self.vote_count[vote] += 1
        message = f"Received vote: {vote} from {client.getpeername()}"
        self.send_to_all_clients(f"Received vote: {vote} from {client.getpeername()}")
        # message = f"Received vote: {vote}, Timestamp: {timestamp} from {client.getpeername()}"
        print(message)
        return message 

    
    def reset_votes(self):
        self.vote_count = {"Y": 0, "N": 0}
        self.voting_end = False

    def send_final_vote_count(self):
        time.sleep(30)
        self.send_to_all_clients(f"Final vote count: {self.vote_count}")
        self.vote_count.clear()

    def handle_client(self, client):
        addr = client.getpeername()
        self.clients[client] = "active"
        while True:
            try:
                request = client.recv(1024).decode().strip()
            except OSError:
                break
            if request == "quit":
                self.clients.pop(client)
                print(f"Client {client} disconnected")
            elif request[:3] == "gen":
                prompt = request
                self.send_image(prompt, client)
            elif request in ["Y", "N"]:
                self.vote_count[request] += 1
                vote_message = self.process_vote(request, client)
                print(self.vote_count["Y"] , self.vote_count["N"], len(self.clients))
                if (self.vote_count["Y"]//2 + self.vote_count["N"]//2) == len(self.clients):
                    self.voting_end = True
                    Y = self.vote_count["Y"]//2
                    N = self.vote_count["N"]//2
                    print(f"Voting ended. Results: 'Y:'{Y}, N:{N}")
                    self.send_to_all_clients(f"Voting ended. Results: 'Y:'{Y}, N:{N}")
                    self.reset_votes()            

    
    def run(self):
        while True:
            client, addr = self.server.accept()
            print(f"New connection from {addr[0]}:{addr[1]}")
            client_thread = threading.Thread(target=self.handle_client, args=(client,))
            client_thread.start()

if __name__ == "__main__":
    server = Server("localhost", 8000)
    server.run()


    