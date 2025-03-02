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
    columns = create_kanboard_columns(kanboard_client, kanboard_project['id'], wekan_board['lists'])

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

def create_kanboard_columns(kanboard_client: kanboard.Client, project_id: int, wekan_lists: list[wekan_types.WekanBoard.List]) -> list[kanboard_types.Column]:
    columns = kanboard_client.get_columns(project_id=project_id)

    column_title_position_map: dict[str, int] = {}
    wekan_list: wekan_types.WekanBoard.List
    for wekan_list in sorted(wekan_lists, key=lambda wekan_list: wekan_list['sort']):
        column_id = create_kanboard_column(kanboard_client, project_id, columns, wekan_list['title'])
        column_title_position_map[wekan_list['title']] = wekan_list['sort'] + 1

    return columns

def create_kanboard_column(kanboard_client: kanboard.Client, project_id: int, existing_columns: list[kanboard_types.Column], column_title: str) -> int:
    column = next((column for column in existing_columns if column['title'] == column_title), None)
    if column is not None:
        return column['id']

    column_id = kanboard_client.add_column(project_id=project_id, title=column_title)
    return column_id

def main() -> None:
    load_dotenv()

    migrate()

if __name__ == '__main__':
    main()
