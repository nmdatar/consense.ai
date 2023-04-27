import openai
from dotenv import load_dotenv
import os
import argparse
from typing import List, Dict, Tuple
import requests
import ipfshttpclient

load_dotenv()

class Server:
    def __init__(self, host: str, port: int = 8001, id: int = 1) -> None:
        self.host = host
        self.port = port
        self.id = id
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.API_KEY = openai.api_key
        self.connections = List[Tuple[str, str]]
    
    def generate_image(self, prompt: str) -> Dict:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="256x256"
        )
        return response
    
    def send_urls(self, response: Dict) -> str:
        url = response['data'][0]['url']
        for connection in self.connections:
            connection[0].send(url.encode())
    
    def upload_to_ipfs(self, url:str) -> str:
        image_content = requests.get(url).content
        with ipfshttpclient.connect() as client:
            result = client.add_bytes(image_content)
            return result
 

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate an image and store it on IPFS.')
    parser.add_argument('prompt', type=str, help='The image prompt.')
    args = parser.parse_args()

    server = Server("localhost")

    # Validate the input using the check_error method
    error_code = server.check_error_command("gen", args.prompt)
    if error_code != 0:
        print("Error: Invalid input. Please provide a valid command.")
        exit(1)
    try:
        image_response = server.generate_image(args.prompt)
    except Exception as e:
        print("Exception:", e)
    

    image_url = image_response['data'][0]['url']
    print("Click on this to view your image: ", image_url)


    