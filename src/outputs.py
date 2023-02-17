import csv
import datetime as dt
import logging

from prettytable import PrettyTable
from requests_cache.models.response import DATETIME_FORMAT

from constants import BASE_DIR


def control_output(results, cli_args):
    """Контроль вывода результатов парсинга."""
    output = cli_args.output
    if output == 'pretty':
        pretty_output(results)
    elif output == 'file':
        file_output(results, cli_args)
    else:
        default_output(results)


def default_output(results):
    """Вывод данных в терминал построчно."""
    for row in results:
        print(*row)


def pretty_output(results):
    """Вывод данных в формате PrettyTable."""
    table = PrettyTable()
    table.field_names = results[0]
    print('header',results[0])
    table.align = 'l'
    table.add_rows(results[1:])
    print('others', results[1:])
    print(table)


def file_output(results, cli_args):
    """Создание директории с результатами парсинга."""
    results_dir = BASE_DIR / 'results'
    results_dir.mkdir(exist_ok=True)
    parser_mode = cli_args.mode
    now = dt.datetime.now()
    now_formatted = now.strftime(DATETIME_FORMAT)
    now_formatted = now_formatted.replace(' ', '_')[:-4]
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = results_dir / file_name
    file_path=results_dir/'111.csv'
    print(file_path)
    with open(file_path, 'w', encoding='utf-8') as f:
        writer = csv.writer(f, dialect='unix')
        writer.writerows(results)
    logging.info(f'Файл с результатами был сохранён: {file_path}')