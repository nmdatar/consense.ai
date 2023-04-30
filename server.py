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

    
    def run(self):
        while True:
            client, addr = self.server.accept()
            print(f"New connection from {addr[0]}:{addr[1]}")
            client_thread = threading.Thread(target=self.handle_client, args=(client,))
            client_thread.start()

'''
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# In-memory storage for votes
votes = {}

@app.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()

    if not data or 'id' not in data or 'vote' not in data:
       return jsonify({'error': 'Invalid request'}), 400

    vote_id = data['id']
    vote_value = data['vote']

    # Initialize the votes for the id, if not already present
    if vote_id not in votes:
       votes[vote_id] = {'upvotes': 0, 'downvotes': 0}

    # Update the vote count
    if vote_value == 'upvote':
       votes[vote_id]['upvotes'] += 1
    elif vote_value == 'downvote':
       votes[vote_id]['downvotes'] += 1
    else:
       # Invalid vote value
       return jsonify({'error': 'Invalid vote value'}), 400

    return jsonify({'message': 'Vote recorded'}), 200

@app.route('/get_votes', methods=['GET'])
def get_votes():
    vote_id = request.args.get('id')

    if not vote_id:
       return jsonify({'error': 'Invalid request'}), 400

    if vote_id not in votes:
       return jsonify({'error': 'Vote ID not found'}), 404

    return jsonify(votes[vote_id]), 200

if __name__ == '__main__':
    app.run(debug=True)
'''

if __name__ == "__main__":
    server = Server("localhost", 8000)
    server.run()


    
