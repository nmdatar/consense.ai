import openai
from dotenv import load_dotenv
import os
import argparse
from typing import List, Dict, Tuple

load_dotenv()

class Server:
    def __init__(self, host: str, port: int = 8000, id: int = 1) -> None:
        self.host = host
        self.port = port
        self.id = id
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.API_KEY = openai.api_key
        self.connections = List[Tuple(str, str)]
    
    def generate_image(self, prompt: str) -> Dict:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        return response
    
    def send_urls(self, response: Dict) -> str:
        url = response['data'][0]['url']
        for connection in self.connections:
            connection.send(url.encode())


    def check_error(self, request_type: str, request: str):
        request = request.split()
        errno = 0
        commands = ["gen"]
        if len(request) == 0 or request[0] not in commands:
            errno = 1

        elif request[0] == "gen":
            if len(request < 2):
                errno = 1
        
        return errno





if __name__ == "__main__":
    