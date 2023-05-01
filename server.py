import openai
from dotenv import load_dotenv
import os
import argparse
from typing import List, Dict, Tuple
import requests
import ipfshttpclient
import socket
import threading

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
        self.image_votes = {} #keep track of votes per image
        print(f"Server started on {host}:{port}")
    
    def generate_image(self, prompt: str) -> Dict:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="256x256"
        )
        return response

    def send_image(self, prompt, client):
        print(self.generate_available)
        try:
            self.generate_available = 1
            image_response = self.generate_image(prompt)
            image_url = image_response['data'][0]['url']
            print("Generated image URL:", image_url)
            self.send_to_all_clients(image_url)
            self.image_votes[image_url] = {"Y": 0, "N": 0} #initialize votes
            print(f"shared image to", [client.getpeername() for client in self.clients])
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

    def handle_client(self, client):
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
            elif request[:4] == "vote": 
                vote = request.split()[1]
                image_url = self.clients[client]
                if image_url in self.image_votes:
                    self.image_votes[image_url][vote] += 1
                    self.send_to_all_clients(f"Vote updated for {image_url}: {self.image_votes[image_url]}")
                    print(f"Image {image_url} vote updated: {self.image_votes[image_url]}")
                else:
                    print(f"Error: Image {image_url} not found in votes")

    
    def run(self):
        while True:
            client, addr = self.server.accept()
            print(f"New connection from {addr[0]}:{addr[1]}")
            client_thread = threading.Thread(target=self.handle_client, args=(client,))
            client_thread.start()

if __name__ == "__main__":
    server = Server("localhost", 8000)
    server.run()


    
