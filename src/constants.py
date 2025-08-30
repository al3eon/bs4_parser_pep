from pathlib import Path

PEP = 'https://peps.python.org/numerical/'
MAIN_DOC_URL = 'https://docs.python.org/3/'

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'parser.log'

LOG_FORMAT = '"%(asctime)s - [%(levelname)s] - %(message)s"'
DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
DT_FORMAT = '%d.%m.%Y %H:%M:%S'

EMPTY_RESULT = [
    ('Статус', 'Количество'),
    ('Всего', 0)
]
EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}


PRETTY_OUTPUT = 'pretty'
FILE_OUTPUT = 'file'

PEP_LOGGING = {
    'EMPTY_RESPONSE': 'Пустой ответ от страницы: {}',
    'MAIN_PAGE_ERROR': 'Ошибка парсинга главной страницы {}: {}',
    'ERRORS_HEADER': 'Ошибки при парсинге страниц: ',
    'REQUEST_ERRORS_HEADER': 'Ошибки при загрузке страниц: ',
    'REQUEST_ERROR': 'Ошибка загрузки {}: {}',
    'TAG_ERRORS_HEADER': 'Ошибки при поиске тегов: ',
    'TAG_ERROR': 'Ошибка парсинга {}: {}',
    'UNKNOWN_ABBR_HEADER': 'Неизвестная аббревиатура: ',
    'UNKNOWN_ABBR': '{}',
    'DIF_STATUSES_HEADER': 'Несовпадающие статусы: ',
    'DIF_STATUSES': '\n{}\nСтатус в карточке: {}\nОжидаемые статусы: {}\n',
    'FILE_SAVE': 'Файл с результатом был сохранен: {}',
    'ARCHIVE_PATH': 'Архив был загружен и сохранён: {}',
    'PARSER_START': 'Парсер запущен!',
    'PARSER_ARGS': 'Аргументы командной строки: {}',
    'PARSER_ERROR': 'Произошла ошибка: {}',
    'PARSER_FINISH': 'Парсер завершил работу',
}
