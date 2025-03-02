import json
import kanboard
import kanboard_types
import os
import wekan_types
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
    wekan_board: wekan_types.WekanBoard = load_json(json_file_path)

    wekan_board_title = wekan_board['title']

    kanboard_project = create_kanboard_project(kanboard_client, wekan_board_title)

def load_json(json_file_path: str) -> any:
    with open(json_file_path, 'r') as file:
        return json.load(file)

def create_kanboard_project(kanboard_client: kanboard.Client, project_name: str) -> kanboard_types.Project:
    project = kanboard_client.get_project_by_name(name=project_name)
    if project is not False:
        return project

    project_id = kanboard_client.create_project(name=project_name)
    project = kanboard_client.get_project_by_id(project_id=project_id)
    return project

def main() -> None:
    load_dotenv()

    migrate()

if __name__ == '__main__':
    main()
