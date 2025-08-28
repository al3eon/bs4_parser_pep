import logging
import re
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, EXPECTED_STATUS, MAIN_DOC_URL, PEP
from outputs import control_output
from utils import find_tag, get_response


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, 'lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_url = find_tag(
        main_div, 'div', attrs={'class': 'toctree-wrapper'}
    )
    section_by_python = div_with_url.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(section_by_python):
        version_a_tag = section.find('a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')

        results.append(
            (version_link, h1, dl_text)
        )
    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return

    soup = BeautifulSoup(response.text, 'lxml')
    div = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = div.find_all('ul')

    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Ничего не нашлось')

    results = []
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


def download(session):
    download_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, download_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, 'lxml')
    table = find_tag(soup, 'table', {'class': 'docutils'})

    pdf_a4_tag = find_tag(table, 'a', {'href': re.compile(r'.+pdf-a4\.zip')})
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(download_url, pdf_a4_link)

    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename

    response = session.get(archive_url)
    with archive_path.open('wb') as f:
        f.write(response.content)

    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    response = get_response(session, PEP)
    if response is None:
        return

    soup = BeautifulSoup(response.text, 'lxml')
    section = find_tag(soup, 'section', attrs={'id': 'index-by-category'})
    statuses = []
    dif_statuses = []
    for table in tqdm(section.find_all('table'), desc='Парсим данные...'):
        tbody = find_tag(table, 'tbody')
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            pep_status = (find_tag(cells[0], 'abbr').text
                          if find_tag(cells[0], 'abbr') else '')
            pep_href = find_tag(cells[1], 'a')['href']

            specific = urljoin(PEP, pep_href)
            response = session.get(specific)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            section = find_tag(soup, 'section',
                               attrs={'id': 'pep-content'})
            dl = find_tag(section, 'dl')
            pattern = r'Status'
            for dt in dl.find_all('dt'):
                if re.search(pattern, dt.get_text()):
                    status_dd = dt.find_next_sibling('dd').get_text()

            statuses.append(status_dd)

            letter = pep_status[-1] if pep_status else ''
            if letter in EXPECTED_STATUS.keys():
                if status_dd not in EXPECTED_STATUS[letter]:
                    dif_statuses.append(
                        f'\n{specific}\n'
                        f'Статус в карточке: {status_dd}\n'
                        f'Ожидаемые статусы: {EXPECTED_STATUS[letter]}\n'
                    )
            else:
                logging.error(f'Неизвестная аббревиатура: {letter}! '
                              f'(PEP: {specific})')

    logging.info('Несовпадающие статусы:')
    for status in dif_statuses:
        logging.info(status)

    csv_data = [('Статус', 'Количество')]
    unique_statuses = set(statuses)
    for status in sorted(unique_statuses):
        csv_data.append((status, statuses.count(status)))
    csv_data.append(('Total', len(statuses)))

    return csv_data


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
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
    results = MODE_TO_FUNCTION[parser_mode](session)

    if results is not None:
        control_output(results, args)

    logging.info('Парсер завершил работу')


if __name__ == '__main__':
    main()
