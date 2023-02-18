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


def find_tag(soup, tag=None, attrs=None, string=None, many=False):
    """Перехват ошибки поиска тегов."""
    if many is False:
        searched_tag = soup.find(tag, attrs=(attrs or {}),
                                 string=(string or ''))
    else:
        searched_tag = soup.find_all(tag, attrs=(attrs or {}),
                                     string=(string or ''))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs} {string}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def search_tables_info_in_section(section, session):
    """Поиск в информации нужной секции."""
    sections = find_tag(section, 'section', many=True)
    counted_results = {}
    for sub_section in sections:
        table_header = find_tag(sub_section, 'h3').text
        tables = find_tag(sub_section, 'table', many=True)
        for table in tables:
            trs = find_tag(table.tbody, 'tr', many=True)
            for tr in tqdm(trs, desc=table_header[:25]):
                tds = find_tag(tr, 'td', many=True)
                status_on_main = tds[0].text
                if not status_on_main == '':
                    status_on_main = status_on_main[1:]
                link = tds[2].a['href']
                pep_link = urljoin(PEPS_URL, link)
                response = get_response(session, pep_link)
                if response is None:
                    return
                pep_soup = BeautifulSoup(response.text, features='lxml')
                status_tag = find_tag(pep_soup, string='Status')
                status_value = status_tag.parent.next_sibling.next_sibling.text
                counted_results[status_value] = counted_results.get(
                    status_value, 0) + 1
                try:
                    if status_value not in EXPECTED_STATUS[status_on_main]:
                        logging.info(
                            f'Несовпадающие статусы: \n{pep_link} \n'
                            f'Статус в карточке:{status_value} \n'
                            f'Ожидаемые статусы:'
                            f'{EXPECTED_STATUS[status_on_main]}')
                except KeyError:
                    logging.error(
                        f'Неизвестный статус на главной:{status_on_main} '
                        f'\n{pep_link} \n'
                        f'Статус в карточке:{status_value} \n'
                    )
    total = sum(counted_results.values())
    counted_results['Total'] = total
    return counted_results
