import kanboard
import os
from dotenv import load_dotenv

def migrate() -> None:
    kanboard_api_token = os.getenv('KANBOARD_API_TOKEN')

    kanboard_client = kanboard.Client('http://localhost/kanboard/jsonrpc.php', 'jsonrpc', kanboard_api_token, 'X-API-Auth')

def main() -> None:
    load_dotenv()

    migrate()

if __name__ == '__main__':
    main()
