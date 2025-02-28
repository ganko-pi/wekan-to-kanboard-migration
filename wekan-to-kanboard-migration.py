import kanboard
import os
from dotenv import load_dotenv

def main():
    load_dotenv()

    kanboard_api_token = os.getenv('KANBOARD_API_TOKEN')

    kb = kanboard.Client('http://localhost/kanboard/jsonrpc.php', 'jsonrpc', kanboard_api_token, 'X-API-Auth')

if __name__ == '__main__':
    main()
