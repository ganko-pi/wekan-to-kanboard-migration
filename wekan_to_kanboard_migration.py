import json
import kanboard
import os
from dotenv import load_dotenv

def migrate() -> None:
    kanboard_api_token = os.getenv('KANBOARD_API_TOKEN')
    input_directory = os.getenv('INPUT_DIRECTORY')

    kanboard_client = kanboard.Client('http://localhost/kanboard/jsonrpc.php', 'jsonrpc', kanboard_api_token, 'X-API-Auth')

    for file in os.listdir(input_directory):
        if not file.endswith('.json'):
            continue

        migrate_wekan_board(kanboard_client, os.path.join(input_directory, file))

def migrate_wekan_board(kanboard_client: kanboard.Client, json_file_path: str) -> None:
    pass

def main() -> None:
    load_dotenv()

    migrate()

if __name__ == '__main__':
    main()
