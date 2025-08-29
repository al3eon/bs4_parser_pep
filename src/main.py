import logging
import re
from collections import defaultdict
from urllib.parse import urljoin

import requests_cache
from requests import RequestException
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (BASE_DIR, EMPTY_RESULT, EXPECTED_STATUS,
                       MAIN_DOC_URL, PEP, PEP_LOGGING)
from exceptions import ParserFindTagException
from outputs import control_output
from utils import find_tag, get_soup


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = get_soup(session, whats_new_url)
    section_by_python = soup.select(
        '#what-s-new-in-python div.toctree-wrapper li.toctree-l1')
    if section_by_python is None:
        raise ParserFindTagException('Не найден тег для ')

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(section_by_python):
        version_a_tag = section.find('a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        soup = get_soup(session, version_link)
        results.append((
            version_link,
            find_tag(soup, 'h1'),
            find_tag(soup, 'dl').text.replace('\n', ' ')
        ))
    return results


def latest_versions(session):
    soup = get_soup(session, MAIN_DOC_URL)
    div = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = div.find_all('ul')

    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise ParserFindTagException('Не найден список версий на странице')

    results = []
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        text_match = re.search(pattern, a_tag.text)

        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''

        results.append(
            (a_tag['href'], version, status)
        )
    return results


def download(session):
    download_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = get_soup(session, download_url)

    archive_tag = soup.select_one(
        'table.docutils a[href$="pdf-a4.zip"]')['href']
    if archive_tag is None:
        raise ParserFindTagException('Не найден тег для PDF A4 на странице')
    archive_url = urljoin(download_url, archive_tag)

    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename

    response = session.get(archive_url)
    with archive_path.open('wb') as f:
        f.write(response.content)

    logging.info(logging.info(PEP_LOGGING['ARCHIVE_PATH'].format(
        archive_path))
    )


def _log_pep_errors(request_errors, tag_errors, unknown_abbr, dif_statuses):
    if request_errors:
        logging.error(PEP_LOGGING['REQUEST_ERRORS_HEADER'])
        for error in request_errors:
            logging.error(error, exc_info=True)

    if tag_errors:
        logging.error(PEP_LOGGING['TAG_ERRORS_HEADER'])
        for error in tag_errors:
            logging.error(error, exc_info=True)

    logging.info(PEP_LOGGING['UNKNOWN_ABBR_HEADER'])
    for abbr in unknown_abbr:
        logging.info(abbr)

    logging.info(PEP_LOGGING['DIF_STATUSES_HEADER'])
    for status in dif_statuses:
        logging.info(status)


def _process_pep_row(
        row, session, status_counts, dif_statuses,
        unknown_abbr, request_errors, tag_errors):
    try:
        cells = row.find_all('td')
        pep_status = (find_tag(cells[0], 'abbr').text
                      if find_tag(cells[0], 'abbr') else '')
        pep_href = find_tag(cells[1], 'a')['href']

        specific = urljoin(PEP, pep_href)
        soup = get_soup(session, specific)
        if soup is None:
            request_errors.append(PEP_LOGGING['EMPTY_RESPONSE'].format(
                specific)
            )
            return

        section = find_tag(soup, 'section',
                           attrs={'id': 'pep-content'})
        dl = find_tag(section, 'dl')
        pattern = r'Status'
        for dt in dl.find_all('dt'):
            if re.search(pattern, dt.get_text()):
                status_dd = dt.find_next_sibling('dd').get_text()

        status_counts[status_dd] += 1

        letter = pep_status[-1] if pep_status else ''
        if letter in EXPECTED_STATUS.keys():
            if status_dd not in EXPECTED_STATUS[letter]:
                dif_statuses.append(
                    PEP_LOGGING['DIF_STATUSES'].format(
                        specific, status_dd, EXPECTED_STATUS[letter]
                    )
                )
        else:
            unknown_abbr.append(
                PEP_LOGGING['UNKNOWN_ABBR'].format(
                    f'{letter} (PEP: {specific})'
                )
            )

    except RequestException as e:
        request_errors.append(PEP_LOGGING['REQUEST_ERROR'].format(
            specific, str(e))
        )
    except ParserFindTagException as e:
        tag_errors.append(PEP_LOGGING['TAG_ERROR'].format(
            specific, str(e))
        )


# Правильно ли понял замечание насчет логирования?
# Разбил на несколько функций из-за жалоб линтера - с901
def pep(session):
    request_errors = []
    tag_errors = []

    try:
        soup = get_soup(session, PEP)
        if soup is None:
            logging.error(PEP_LOGGING['EMPTY_RESPONSE'].format(PEP))
            return EMPTY_RESULT

        section = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
        tbody = find_tag(section, 'tbody')
    except ParserFindTagException as e:
        logging.error(PEP_LOGGING['MAIN_PAGE_ERROR'].format(
            PEP, str(e)), exc_info=True
        )
        return EMPTY_RESULT

    status_counts = defaultdict(int)
    dif_statuses = []
    unknown_abbr = []

    for row in tqdm(tbody.find_all('tr'), desc='Парсим данные...'):
        _process_pep_row(
            row, session, status_counts, dif_statuses,
            unknown_abbr, request_errors, tag_errors
        )

    _log_pep_errors(request_errors, tag_errors, unknown_abbr, dif_statuses)

    return [
        ('Статус', 'Количество'),
        *sorted(status_counts.items()),
        ('Всего', sum(status_counts.values()))
    ]


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info(PEP_LOGGING['PARSER_START'])

    try:
        arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
        args = arg_parser.parse_args()
        logging.info(PEP_LOGGING['PARSER_ARGS'].format(args))

        session = requests_cache.CachedSession()
        if args.clear_cache:
            session.cache.clear()

        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)

        if results is not None:
            control_output(results, args)

    except Exception as e:
        logging.error(PEP_LOGGING['PARSER_ERROR'].format(str(e)),
                      exc_info=True)

    logging.info(PEP_LOGGING['PARSER_FINISH'])


if __name__ == '__main__':
    main()
