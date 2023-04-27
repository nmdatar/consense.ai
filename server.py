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
        self.clients = []
        print(f"Server started on {host}:{port}")
    
    def generate_image(self, prompt: str) -> Dict:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="256x256"
        )
        return response
    
    def handle_client(self, client: socket.socket):
        self.clients.append(client)
        prompt = client.recv(1024).decode().strip()[4:]
        print(f"Received prompt: {prompt}")

        try:
            image_response = self.generate_image(prompt)
            image_url = image_response['data'][0]['url']
            print("Generated image URL:", image_url)
            self.send_to_all_clients(image_url)
            print(f"shared image to", [client.getpeername() for client in self.clients])
        except Exception as e:
            print("Exception:", e)
            self.send_to_all_clients("Error: {e}")

    def send_to_all_clients(self, message: str):
        for client in self.clients:
            client.send(message.encode())   
    
    def run(self):
        while True:
            client, addr = self.server.accept()
            print(f"New connection from {addr[0]}:{addr[1]}")
            client_thread = threading.Thread(target=self.handle_client, args=(client,))
            client_thread.start()
    
    def upload_to_ipfs(self, url:str) -> str:
        image_content = requests.get(url).content
        with ipfshttpclient.connect() as client:
            result = client.add_bytes(image_content)
            return result

if __name__ == "__main__":
    server = Server("localhost", 8000)
    server.run()


    