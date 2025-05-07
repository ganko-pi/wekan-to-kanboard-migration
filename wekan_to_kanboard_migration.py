import configparser
import json
import kanboard
import kanboard_types
import logging
import logging.config
import logging.handlers
import os
import pathlib
import wekan_types
from dotenv import load_dotenv

def init_logging() -> None:
    logging_conf_file = 'logging.conf'
    logging_file_handler_name = 'fileHandler'
    logging_file_handler_section_name = f'handler_{logging_file_handler_name}'
    logging_file_handler_args_name = 'args'

    config = configparser.ConfigParser()
    config.read(logging_conf_file)
    file_handler_args_str = config[logging_file_handler_section_name][logging_file_handler_args_name]
    file_handler_args = eval(file_handler_args_str)
    log_path_str = file_handler_args[0]
    log_path = pathlib.Path(log_path_str)
    log_parent_path = log_path.parent

    log_parent_path.mkdir(parents=True, exist_ok=True)
    old_log_file_exists = log_path.is_file()

    logging.config.fileConfig(logging_conf_file)
    handlers = logging.getLogger().handlers
    file_handler: handler.RotatingFileHandler | None = next((handler for handler in handlers if handler.name == logging_file_handler_name), None)
    if file_handler is not None and old_log_file_exists:
        # without this check if no log file exists previously, logging.config.fileConfig creates a new empty file which would be rolled over immediately
        file_handler.doRollover()

def migrate() -> None:
    kanboard_api_uri = os.getenv('KANBOARD_API_URI')
    kanboard_api_user = os.getenv('KANBOARD_API_USER')
    kanboard_api_token = os.getenv('KANBOARD_API_TOKEN')
    input_directory = os.getenv('INPUT_DIRECTORY')

    logging.info(f'Creating client for "{kanboard_api_uri}" with user "{kanboard_api_user}" to communicate with the Kanboard API.')
    kanboard_client = kanboard.Client(kanboard_api_uri, kanboard_api_user, kanboard_api_token, 'X-API-Auth')

    for file in os.listdir(input_directory):
        if not file.endswith('.json'):
            continue

        migrate_wekan_board(kanboard_client, os.path.join(input_directory, file))

def migrate_wekan_board(kanboard_client: kanboard.Client, json_file_path: str) -> None:
    logging.info(f'Starting migration for JSON file "{json_file_path}".')
    wekan_board: wekan_types.WekanBoard = load_json(json_file_path)

    wekan_board_title = wekan_board['title']

    kanboard_project = create_kanboard_project(kanboard_client, wekan_board_title)
    columns = create_kanboard_columns(kanboard_client, kanboard_project['id'], wekan_board['lists'])

def load_json(json_file_path: str) -> any:
    logging.info(f'Loading contents of JSON file "{json_file_path}".')
    with open(json_file_path, 'r') as file:
        return json.load(file)

def create_kanboard_project(kanboard_client: kanboard.Client, project_name: str) -> kanboard_types.Project:
    project = kanboard_client.get_project_by_name(name=project_name)
    if project is not False:
        logging.info(f'Project "{project_name}" does already exist with id {project['id']}. Skipping creation.')
        return project

    logging.info(f'Creating project "{project_name}".')
    project_id = kanboard_client.create_project(name=project_name)
    logging.info(f'Created project "{project_name}" with id {project_id}.')
    project = kanboard_client.get_project_by_id(project_id=project_id)
    return project

def create_kanboard_columns(kanboard_client: kanboard.Client, project_id: int, wekan_lists: list[wekan_types.WekanBoard.List]) -> list[kanboard_types.Column]:
    columns = kanboard_client.get_columns(project_id=project_id)

    column_title_position_map: dict[str, int] = {}
    wekan_list: wekan_types.WekanBoard.List
    for wekan_list in sorted(wekan_lists, key=lambda wekan_list: wekan_list['sort']):
        column_id = create_kanboard_column(kanboard_client, project_id, columns, wekan_list['title'])
        column_title_position_map[wekan_list['title']] = wekan_list['sort'] + 1

    columns = sort_kanboard_columns(kanboard_client, project_id, column_title_position_map)
    return columns

def create_kanboard_column(kanboard_client: kanboard.Client, project_id: int, existing_columns: list[kanboard_types.Column], column_title: str) -> int:
    column = next((column for column in existing_columns if column['title'] == column_title), None)
    if column is not None:
        logging.info(f'Column "{column['title']}" in project with id {project_id} does already exist with id {column['id']}. Skipping creation.')
        return column['id']

    logging.info(f'Creating column "{column_title}" in project with id {project_id}.')
    column_id = kanboard_client.add_column(project_id=project_id, title=column_title)
    logging.info(f'Created column "{column_title}" with id {column_id} in project with id {project_id}.')
    return column_id

def sort_kanboard_columns(kanboard_client: kanboard.Client, project_id: int, column_title_position_map: dict[str, int]) -> list[kanboard_types.Column]:
    for index, (column_title, position) in enumerate(sorted(column_title_position_map.items(), key=lambda column_title_position_entry: column_title_position_entry[1])):
        column_title_position_map[column_title] = index + 1

    columns: list[kanboard_types.Column] = kanboard_client.get_columns(project_id=project_id)

    for column in columns:
        column_title = column['title']
        if column_title not in column_title_position_map:
            continue

        current_position = column['position']
        target_position = column_title_position_map[column_title]
        if current_position == target_position:
            continue

        column_id = column['id']
        logging.info(f'Moving column with id {column_id} from position {current_position} to position {target_position} in project with id {project_id}.')
        kanboard_client.change_column_position(project_id=project_id, column_id=column_id, position=target_position)

        update_kanboard_column_positions(columns, current_position, target_position)

    return columns

def update_kanboard_column_positions(columns: list[kanboard_types.Column], old_position: int, new_position: int) -> None:
    lower_position = old_position
    higher_position = new_position
    position_correction = -1

    if new_position < old_position:
        lower_position = new_position
        higher_position = old_position
        position_correction = 1

    for column in columns:
        if column['position'] < lower_position:
            continue

        if column['position'] > higher_position:
            continue

        if column['position'] == old_position:
            column['position'] = new_position
            continue

        column['position'] += position_correction

def main() -> None:
    load_dotenv()
    init_logging()

    migrate()

if __name__ == '__main__':
    main()
