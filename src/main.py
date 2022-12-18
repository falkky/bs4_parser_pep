import logging
import re
from typing import NoReturn, Optional
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, EXPECTED_STATUS, MAIN_DOC_URL, PEP_URL
from outputs import control_output
from utils import find_tag, get_response


def whats_new(session) -> Optional[list[tuple]]:
    """
    Собирает ссылки на статьи о нововведениях в Python, переходит по ним
     и забирать информацию об авторах и редакторах статей.
    """
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = main_div.find(
        'div',
        attrs={'class': 'toctree-wrapper compound'}
    )
    sections_by_python = div_with_ul.find_all(
        'li',
        attrs={'class': 'toctree-l1'}
    )
    result = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    for section in tqdm(sections_by_python, desc='progress bar'):
        version_a_tag = find_tag(section, 'a')
        url = version_a_tag['href']
        full_url = urljoin(whats_new_url, url)
        response = get_response(session, full_url)
        if response is None:
            return
        soup = BeautifulSoup(response.text, features='lxml')
        tag_h1 = find_tag(soup, 'h1')
        tag_dl = find_tag(soup, 'dl')
        dl_text = tag_dl.text.replace('\n', ' ')
        result.append((full_url, tag_h1.text, dl_text))
    return result


def latest_versions(session) -> Optional[list[tuple]]:
    """Собирает информацию о статусах версий Python."""
    print(type(session))
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
        else:
            raise Exception('Ничего не нашлось')
    result = [('Ссылка на документацию', 'Версия', 'Статус')]
    for a_tag in a_tags:
        link = a_tag['href']
        pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
        text_match = re.search(pattern, a_tag.text)
        if text_match:
            version, status = text_match.group(1, 2)
        else:
            empty_str = ''
            version, status = a_tag.text, empty_str
        result.append((link, version, status))
    return result


def download(session) -> Optional[NoReturn]:
    """Скачивает архив с актуальной документацией."""
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    table = find_tag(soup, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        table,
        'a',
        attrs={'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    archive_url = urljoin(downloads_url, pdf_a4_tag['href'])
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session) -> Optional[list[tuple]]:
    """Парсит документы PEP."""
    response = get_response(session, PEP_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    numerical_indexes = find_tag(
        soup,
        'section',
        attrs={'id': 'numerical-index'}
    )
    tbody = find_tag(numerical_indexes, 'tbody')
    tr_rows = tbody.find_all('tr')
    count_status = {}
    for tr_row in tr_rows:
        td_rows = tr_row.find_all('td')
        type_and_status = td_rows[0].text
        if len(type_and_status) == 2:
            preview_status = EXPECTED_STATUS[type_and_status[1]]
        else:
            preview_status = 'unknow status'
        full_pep_url = urljoin(PEP_URL, td_rows[1].find('a')['href'])
        response = get_response(session, full_pep_url)
        if response is None:
            return
        pep_card = BeautifulSoup(response.text, features='lxml')
        pep_content = find_tag(
            pep_card,
            'section',
            attrs={'id': 'pep-content'}
        )
        dt_status = pep_content.find(string='Status').parent
        actual_status = dt_status.find_next_sibling('dd').string
        if actual_status not in preview_status:
            logging.info(
                'Diffrent status:\n'
                f'PEP {full_pep_url} \n'
                f'Status in the table {preview_status} \n'
                f'Status in the card {actual_status}'
            )
        if actual_status in count_status:
            count_status[actual_status] += 1
        else:
            count_status[actual_status] = 1
    result = [('Status', 'Amount')]
    for status in count_status.items():
        result.append(status)
    total_count = sum(count_status.values())
    result.append(('TOTAL', total_count))
    return result


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main() -> NoReturn:
    """Главная функция - точка входа."""
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
