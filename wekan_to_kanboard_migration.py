import configparser
import datetime
import itertools
import json
import kanboard
import kanboard_types
import logging
import logging.config
import logging.handlers
import os
import pathlib
import pytz
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
    timezone_name = os.getenv('TIMEZONE_KANBOARD_SERVER')

    timezone = pytz.utc
    if timezone_name is not None and timezone_name != '':
        timezone = pytz.timezone(timezone_name)

    logging.info(f'Creating client for "{kanboard_api_uri}" with user "{kanboard_api_user}" to communicate with the Kanboard API.')
    kanboard_client = kanboard.Client(kanboard_api_uri, kanboard_api_user, kanboard_api_token, 'X-API-Auth')

    wekan_board_properties: dict[str, list] = {}
    for file in os.listdir(input_directory):
        if not file.endswith('.json'):
            continue

        json_file_path = os.path.join(input_directory, file)
        wekan_board: wekan_types.WekanBoard = load_json(json_file_path)
        extract_properties_dict('', wekan_board, wekan_board_properties)

        logging.info(f'Starting migration for JSON file "{json_file_path}".')
        migrate_wekan_board(kanboard_client, wekan_board, timezone)

    log_wekan_board_properties_with_different_values(wekan_board_properties)

def extract_properties_value(key: str, value: any, typed_dict_properties: dict[str, list]) -> None:
    wekan_board_properties_list = typed_dict_properties.get(key, [])
    typed_dict_properties[key] = wekan_board_properties_list

    if value not in wekan_board_properties_list:
        wekan_board_properties_list.append(value)

def extract_properties_list(key: str, value_list: list, typed_dict_properties: dict[str, list]) -> None:
    list_str = '[]'
    wekan_board_properties_list = typed_dict_properties.get(key, [])
    typed_dict_properties[key] = wekan_board_properties_list

    if list_str not in wekan_board_properties_list:
        wekan_board_properties_list.append(list_str)

    for value in value_list:
        if isinstance(value, dict):
            extract_properties_dict(key, value, typed_dict_properties)
            continue

        if isinstance(value, list):
            extract_properties_list(key, value, typed_dict_properties)
            continue

        extract_properties_value(key, value, typed_dict_properties)

def extract_properties_dict(key: str, typed_dict: dict, typed_dict_properties: dict[str, list]) -> None:
    dict_str = '{}'
    wekan_board_properties_list = typed_dict_properties.get(key, [])
    typed_dict_properties[key] = wekan_board_properties_list

    if dict_str not in wekan_board_properties_list:
        wekan_board_properties_list.append(dict_str)

    for dict_key, value in typed_dict.items():
        combined_key = f'{key} - {dict_key}'
        if key == '':
            combined_key = dict_key

        wekan_board_properties_list = typed_dict_properties.get(combined_key, [])
        typed_dict_properties[combined_key] = wekan_board_properties_list

        if isinstance(value, dict):
            extract_properties_dict(combined_key, value, typed_dict_properties)
            continue

        if isinstance(value, list):
            extract_properties_list(combined_key, value, typed_dict_properties)
            continue

        extract_properties_value(combined_key, value, typed_dict_properties)

def log_wekan_board_properties_with_different_values(wekan_board_properties: dict[str, list]) -> None:
    logging.debug(f'These are the properties of a wekan board with more than one different value:')
    log_wekan_board_properties_with_different_values_indented(wekan_board_properties, '  ')

def log_wekan_board_properties_with_different_values_indented(typed_dict_properties: dict[str, list], indent: str) -> None:
    for key, value in sorted(typed_dict_properties.items()):
        if len(value) <= 1:
            continue

        value_output = json.dumps(value)
        value_output_shortened_length = 80
        value_output_shortened = (value_output[:(value_output_shortened_length - 3)] + '...') if len(value_output) > value_output_shortened_length else value_output
        logging.debug(f'{indent}{key}: {len(value)} different values: {value_output_shortened}')

def migrate_wekan_board(kanboard_client: kanboard.Client, wekan_board: wekan_types.WekanBoard, timezone: datetime.tzinfo) -> None:
    wekan_board_title = wekan_board['title']

    kanboard_project = create_kanboard_project(kanboard_client, wekan_board_title)
    (columns, wekan_list_id_kanboard_column_id_map) = create_kanboard_columns(kanboard_client, kanboard_project['id'], wekan_board['lists'])
    (tasks, wekan_card_id_kanboard_task_id_map) = populate_kanboard_columns_with_tasks(kanboard_client, kanboard_project['id'], columns,
        wekan_list_id_kanboard_column_id_map, wekan_board['cards'], timezone)
    populate_kanboard_tasks_with_subtasks(kanboard_client, kanboard_project['id'], tasks, wekan_card_id_kanboard_task_id_map, wekan_board['checklists'],
        wekan_board['checklistItems'])

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

    logging.info(f'Delete default columns in project "{project_name}".')
    delete_all_kanboard_columns(kanboard_client, project_id)

    project = kanboard_client.get_project_by_id(project_id=project_id)
    return project

def delete_all_kanboard_columns(kanboard_client: kanboard.Client, project_id: int):
    columns: list[kanboard_types.Column] = kanboard_client.get_columns(project_id=project_id)
    for column in columns:
        kanboard_client.remove_column(column_id=column['id'])

def create_kanboard_columns(kanboard_client: kanboard.Client, project_id: int, wekan_lists: list[wekan_types.WekanBoard.List]) -> (list[kanboard_types.Column], dict[str, int]):
    columns = kanboard_client.get_columns(project_id=project_id)

    column_title_position_map: dict[str, int] = {}
    wekan_list_id_kanboard_column_id_map: dict[str, int] = {}
    wekan_list: wekan_types.WekanBoard.List
    for wekan_list in sorted(wekan_lists, key=lambda wekan_list: wekan_list['sort']):
        column_id = create_kanboard_column(kanboard_client, project_id, columns, wekan_list['title'])
        column_title_position_map[wekan_list['title']] = wekan_list['sort'] + 1
        wekan_list_id_kanboard_column_id_map[wekan_list['_id']] = column_id

    columns = sort_kanboard_columns(kanboard_client, project_id, column_title_position_map)
    return (columns, wekan_list_id_kanboard_column_id_map)

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

def get_existing_active_kanboard_tasks(kanboard_client: kanboard.Client, project_id: int) -> list[kanboard_types.Task]:
    existing_active_tasks = kanboard_client.get_all_tasks(project_id=project_id, status_id=1)

    return existing_active_tasks

def get_existing_inactive_kanboard_tasks(kanboard_client: kanboard.Client, project_id: int) -> list[kanboard_types.Task]:
    existing_inactive_tasks = kanboard_client.get_all_tasks(project_id=project_id, status_id=0)

    return existing_inactive_tasks

def get_existing_kanboard_tasks(kanboard_client: kanboard.Client, project_id: int) -> list[kanboard_types.Task]:
    existing_active_tasks = get_existing_active_kanboard_tasks(kanboard_client, project_id)
    existing_inactive_tasks = get_existing_inactive_kanboard_tasks(kanboard_client, project_id)

    existing_tasks = [*existing_active_tasks, *existing_inactive_tasks]
    return existing_tasks

def populate_kanboard_columns_with_tasks(kanboard_client: kanboard.Client, project_id: int, columns: list[kanboard_types.Column], wekan_list_id_kanboard_column_id_map: dict[str, int], cards: list[wekan_types.WekanBoard.Card], timezone: datetime.tzinfo) -> (list[kanboard_types.Task], dict[str, int]) :
    existing_tasks = get_existing_kanboard_tasks(kanboard_client, project_id)

    task_id_position_map: dict[int, int] = {}
    wekan_card_id_kanboard_task_id_map: dict[str, int] = {}
    for card in cards:
        list_id = card['listId']
        column_id = wekan_list_id_kanboard_column_id_map[list_id]
        task_id = add_kanboard_task(kanboard_client, project_id, column_id, existing_tasks, card, timezone)
        task_id_position_map[task_id] = card['sort']
        wekan_card_id_kanboard_task_id_map[card['_id']] = task_id

    tasks = sort_active_kanboard_tasks(kanboard_client, project_id, task_id_position_map)
    return (tasks, wekan_card_id_kanboard_task_id_map)

def add_kanboard_task(kanboard_client: kanboard.Client, project_id: int, column_id: int, existing_tasks: list[kanboard_types.Task], card: wekan_types.WekanBoard.Card, timezone: datetime.tzinfo) -> int:
    existing_task = next((task for task in existing_tasks if task['title'] == card['title']), None)
    if existing_task is not None:
        logging.warning(f'Task "{card['title']}" in project with id {project_id} does already exist with id {existing_task['id']}. It is not ensured that all attributes are correct. Skipping creation.')
        return existing_task['id']

    card_due_at_str = card.get('dueAt', '')
    task_date_due = None
    if card_due_at_str != '':
        card_due_at_date_utc = datetime.datetime.fromisoformat(card_due_at_str)
        card_due_at_date = card_due_at_date_utc.astimezone(timezone)
        task_date_due = card_due_at_date.strftime('%Y-%m-%d %H:%M')

    task_id = kanboard_client.create_task(
        title=card['title'],
        project_id=project_id,
        column_id=column_id,
        date_due=task_date_due,
        description=card.get('description', '')
    )

    if card['archived']:
        kanboard_client.close_task(task_id=task_id)

    return task_id

def move_closed_kanboard_tasks_to_end_of_column(kanboard_client: kanboard.Client, project_id: int) -> None:
    existing_active_tasks = get_existing_active_kanboard_tasks(kanboard_client, project_id)
    existing_inactive_tasks = get_existing_inactive_kanboard_tasks(kanboard_client, project_id)

    existing_inactive_tasks.sort(key=lambda task: task['column_id'])

    for column_id, inactive_tasks in itertools.groupby(existing_inactive_tasks, key=lambda task: task['column_id']):
        active_tasks_in_column = filter(lambda active_task: active_task['column_id'] == column_id, existing_active_tasks)
        inactive_tasks_position = max(map(lambda active_task_in_column: active_task_in_column['position'], active_tasks_in_column), default=0) + 1

        for inactive_task in inactive_tasks:
            task_id = inactive_task['id']
            swimlane_id = inactive_task['swimlane_id']

            kanboard_client.move_task_position(
                project_id=project_id,
                task_id=task_id,
                column_id=column_id,
                position=inactive_tasks_position,
                swimlane_id=swimlane_id
            )

            inactive_tasks_position += 1

def sort_active_kanboard_tasks(kanboard_client: kanboard.Client, project_id: int, task_id_position_map: dict[int, int]) -> list[kanboard_types.Task]:
    # move closed tasks to end to prevent sorting issues
    move_closed_kanboard_tasks_to_end_of_column(kanboard_client, project_id)

    existing_active_tasks = get_existing_active_kanboard_tasks(kanboard_client, project_id)
    existing_active_tasks.sort(key=lambda task: task['column_id'])

    sorted_tasks: list[kanboard_types.Task] = []
    for column_id, tasks in itertools.groupby(existing_active_tasks, key=lambda task: task['column_id']):
        tasks_list = list(tasks)
        task_ids = list(map(lambda task: task['id'], tasks_list))
        task_id_position_map_for_column = {task_id: position for task_id, position in task_id_position_map.items()
            if task_id in task_ids}
        sorted_tasks_in_column = sort_kanboard_tasks_in_column(kanboard_client, project_id, column_id, tasks_list, task_id_position_map_for_column)
        sorted_tasks.extend(sorted_tasks_in_column)

    return sorted_tasks

def sort_kanboard_tasks_in_column(kanboard_client: kanboard.Client, project_id: int, column_id: int, tasks: list[kanboard_types.Task], task_id_position_map: dict[int, int]) -> list[kanboard_types.Task]:
    for index, (task_id, position) in enumerate(sorted(task_id_position_map.items(), key=lambda task_id_position_entry: task_id_position_entry[1])):
        task_id_position_map[task_id] = index + 1

    for task in tasks:
        current_position = task['position']
        target_position = task_id_position_map[task['id']]
        if current_position == target_position:
            continue

        task_id = task['id']
        swimlane_id = task['swimlane_id']
        logging.info(f'Moving task with id {task_id} from position {current_position} to position {target_position} in column with id {column_id} in project with id {project_id}.')
        kanboard_client.move_task_position(
            project_id=project_id,
            task_id=task_id,
            column_id=column_id,
            position=target_position,
            swimlane_id=swimlane_id
        )

        update_kanboard_task_positions(tasks, current_position, target_position)

    return tasks

def update_kanboard_task_positions(tasks: list[kanboard_types.Task], old_position: int, new_position: int) -> None:
    lower_position = old_position
    higher_position = new_position
    position_correction = -1

    if new_position < old_position:
        lower_position = new_position
        higher_position = old_position
        position_correction = 1

    for task in tasks:
        if task['position'] < lower_position:
            continue

        if task['position'] > higher_position:
            continue

        if task['position'] == old_position:
            task['position'] = new_position
            continue

        task['position'] += position_correction

def populate_kanboard_tasks_with_subtasks(kanboard_client: kanboard.Client, project_id: int, tasks: list[kanboard_types.Task], wekan_card_id_kanboard_task_id_map: dict[str, int], checklists: list[wekan_types.WekanBoard.Checklist], checklist_items: list[wekan_types.WekanBoard.ChecklistItem]) -> None:
    if len(checklists) == 0:
        return

    checklist_titles = map(lambda checklist: checklist['title'], checklists)
    joined_checklist_titles = ', '.join(checklist_titles)
    logging.warning(f'Populating Kanboard tasks with subtasks from Wekan checklists. Checklist titles cannot be retained. Lost checklist titles: {joined_checklist_titles}')

    checklists_grouped_by_card_ids = itertools.groupby(checklists, key=lambda checklist: checklist['cardId'])
    checklists_of_cards_with_multiple_checklists = filter(lambda group: len(list(group[1])) > 1, checklists_grouped_by_card_ids)
    for card_id, checklists_group in checklists_of_cards_with_multiple_checklists:
        checklists_group_titles = map(lambda checklist: checklist['title'], checklists_group)
        joined_checklists_group_titles = ', '.join(checklists_group_titles)
        logging.warning(f'Checklists with titles {joined_checklists_group_titles} for Wekan card with id {card_id} are merged.')

    for checklist_item in checklist_items:
        card_id = checklist_item['cardId']
        task_id = wekan_card_id_kanboard_task_id_map[card_id]
        subtask_id = add_kanboard_subtask(kanboard_client, project_id, task_id, checklist_item)

def add_kanboard_subtask(kanboard_client: kanboard.Client, project_id: int, task_id: int, checklist_item: wekan_types.WekanBoard.ChecklistItem) -> int:
    existing_subtasks_of_task: list[kanboard_types.Subtask] = kanboard_client.get_all_subtasks(task_id=task_id)
    existing_subtask_with_title = next((subtask for subtask in existing_subtasks_of_task if subtask['title'] == checklist_item['title']), None)
    if existing_subtask_with_title is not None:
        subtask_id = existing_subtask_with_title['id']
        logging.info(f'Subtask "{checklist_item['title']}" in project with id {project_id} does already exist with id {subtask_id}. Skipping creation.')
        actual_status = existing_subtask_with_title['status']
        expected_status = 1 if checklist_item['isFinished'] else 0
        check_correct_kanboard_subtask_status(subtask_id, actual_status, expected_status)
        return existing_subtask_with_title['id']

    subtask_status = kanboard_types.Subtask.Status.NOT_STARTED
    if checklist_item['isFinished']:
        subtask_status = kanboard_types.Subtask.Status.FINISHED

    subtask_id = kanboard_client.create_subtask(
        task_id=task_id,
        title=checklist_item['title'],
        status=subtask_status.value
    )

    return subtask_id

def check_correct_kanboard_subtask_status(subtask_id: int, actual_status: int, expected_status: int) -> None:
    if actual_status != expected_status:
        logging.warning(f'Subtask with id {subtask_id} was expected to have status {expected_status} but has status {actual_status}.')

def main() -> None:
    load_dotenv()
    init_logging()

    migrate()

if __name__ == '__main__':
    main()
