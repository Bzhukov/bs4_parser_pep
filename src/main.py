import logging
import re
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, MAIN_DOC_URL, PEPS_URL, EXPECTED_STATUS
from outputs import control_output
from utils import get_response, find_tag, find_tags, counter


def whats_new():
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    session = requests_cache.CachedSession()
    response = get_response(session, whats_new_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all('li',
                                              attrs={'class': 'toctree-l1'})
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python, desc='Парсинг релизов'):
        version_a_tag = section.find('a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, features='lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append(
            (version_link, h1.text, dl_text)
        )
    return results


def latest_versions():
    session = requests_cache.CachedSession()
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = find_tag(sidebar, 'ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Не найден список c версиями Python')
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (link, version, status)
        )
    return results


def download():
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    session = requests_cache.CachedSession()
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_table = find_tag(soup, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tags(main_table, 'a',
                           {'href': re.compile(r'.+pdf-a4\.zip$')})
    for link in tqdm(pdf_a4_tag, desc='Идет скачивание'):
        pdf_a4_link = link['href']
        archive_url = urljoin(downloads_url, pdf_a4_link)
        filename = archive_url.split('/')[-1]
        archive_path = downloads_dir / filename
        response = session.get(archive_url)
        with open(archive_path, 'wb') as file:
            file.write(response.content)
        logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep():
    pep_url = PEPS_URL
    session = requests_cache.CachedSession()
    response = get_response(session, pep_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    section = find_tag(soup, 'section', attrs={'id': 'index-by-category'})
    tables = find_tags(section, 'table')
    counted_results = {}
    for table in tables:
        trs = find_tags(table.tbody, 'tr')
        for tr in tqdm(trs):
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
            status_field = find_tag(pep_soup, string='Status')
            status_value = status_field.parent.next_sibling.next_sibling.text
            counted_results = counter(status_value, counted_results)
            if status_value not in EXPECTED_STATUS[status_on_main_page]:
                logging.info(
                    f'Несовпадающие статусы: \n{pep_link} \n'
                    f'Статус в карточке:{status_value} \n'
                    f'Ожидаемые статусы:{EXPECTED_STATUS[status_on_main_page]}')
    header = [('Статус', 'Количество')]
    new = header + list(counted_results.items())
    return new


MODE_TO_FUNCTION = {
    'pep': pep,
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode]()
    if results is not None:
        control_output(results, args)


if __name__ == '__main__':
    main()
