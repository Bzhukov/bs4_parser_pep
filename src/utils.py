import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from requests import RequestException
from tqdm import tqdm

from constants import EXPECTED_STATUS, PEPS_URL
from exceptions import ParserFindTagException


def get_response(session, url):
    """Перехват ошибки RequestException."""
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        logging.exception(
            f'Возникла ошибка при загрузке страницы {url}',
            stack_info=True
        )


def find_tag(soup, tag=None, attrs=None, string=None):
    """Перехват ошибки поиска тегов."""
    searched_tag = soup.find(tag, attrs=(attrs or {}), string=(string or ''))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs} {string}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def find_tags(soup, tag, attrs=None):
    """Перехват ошибки поиска тегов."""
    searched_tags = soup.find_all(tag, attrs=(attrs or {}))
    if searched_tags is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tags


def counter(status, dict):
    """Счетчик количества статусов."""
    try:
        dict[status] = dict[status] + 1
    except KeyError:
        dict[status] = 1
    return dict


def search_tables_info_in_section(section, session):
    """Поиск в информации нужной секции."""
    sections = find_tags(section, 'section')
    counted_results = {}
    for sub_section in sections:
        table_header = find_tag(sub_section, 'h3').text
        tables = find_tags(sub_section, 'table')
        for table in tables:
            trs = find_tags(table.tbody, 'tr')
            for tr in tqdm(trs, desc=table_header[:25]):
                tds = find_tags(tr, 'td')
                status_on_main_page = tds[0].text
                if not status_on_main_page == '':
                    status_on_main_page = status_on_main_page[1:]
                link = tds[2].a['href']
                pep_link = urljoin(PEPS_URL, link)
                response = get_response(session, pep_link)
                if response is None:
                    return
                pep_soup = BeautifulSoup(response.text, features='lxml')
                status_tag = find_tag(pep_soup, string='Status')
                status_value = status_tag.parent.next_sibling.next_sibling.text
                counted_results = counter(status_value, counted_results)
                if status_value not in EXPECTED_STATUS[status_on_main_page]:
                    logging.info(
                        f'Несовпадающие статусы: \n{pep_link} \n'
                        f'Статус в карточке:{status_value} \n'
                        f'Ожидаемые статусы:'
                        f'{EXPECTED_STATUS[status_on_main_page]}')
    return counted_results


def summ(dict1, dict2):
    """Сложение словарей."""
    for key in dict2.keys():
        try:
            dict1[key] = dict1[key] + dict2[key]
        except KeyError:
            dict1[key] = dict2[key]
    return dict1
