import logging
import os
import time
import requests
import json
import sys

from http import HTTPStatus

import telegram

from dotenv import load_dotenv

from endpoints import ENDPOINT

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем, наличе всех токенов.
    Если нет хотя бы одного, то останавливаем бота.
    """
    logging.info('Проверка наличия всех токенов')
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(f'Сообщение {message} отправлено в чат %s')
    except Exception as error:
        logging.error((f'Ошибка отправки сообщения {error}'))


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    current_timestamp = timestamp or int(time.time())
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        status = response.status_code
    except Exception:
        message = 'Нет доступа к API Практикум.'
        raise Exception(message)

    if status != HTTPStatus.OK:
        raise requests.RequestException(
            f'Эндпоинт - {ENDPOINT} недоступен. Код ответа - {status}'
        )
    try:
        return response.json()
    except json.JSONDecodeError as error:
        message = f'Ошибка {error} при форматировании данных.'
        logging.error(message)
        raise requests.RequestException(message)


def check_response(response):
    """Проверяет ответ API на корректность."""
    logging.info('Проверка ответа API на корректность')
    if not isinstance(response, dict):
        message = 'Ответ API не является dict.'
        raise TypeError(message)
    if 'homeworks' not in response or 'current_date' not in response:
        message = 'Нет ключа homeworks в ответе API.'
        raise KeyError(message)
    homeworks = response.get('homeworks')
    if type(homeworks) != list:
        message = 'Не верный формат значения "homeworks".'
        logging.error(message)
        raise TypeError(message)

    if not isinstance(homeworks, list):
        raise KeyError('homeworks не является list')
    return homeworks


def parse_status(homework):
    """Возвращает статут домашней работы."""
    if 'homework_name' not in homework or 'status' not in homework:
        message = 'Отсутствует значение по ключу homework_name или current_date.'
        logging.error(message)
        raise KeyError(message)

    homework_name = homework.get('homework_name')
    homework_status = homework['status']

    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Полученный статус отсутствует в списке HOMEWORK_VERDICTS.'
        logging.error(message)
        raise KeyError(message)

    verdict = HOMEWORK_VERDICTS[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
    )
    if not check_tokens():
        message = 'Отсутствуют переменные окружения. Бот не работает!'
        logging.critical(message)
        sys.exit(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    prev_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if homeworks:
                message = parse_status(homeworks[0])
                if prev_message != message:
                    send_message(bot, message)
                    prev_message = message
                else:
                    message = 'Нет новых статусов.'
                    timestamp = response.get(
                        'current_date', int(time.time()))
                    logging.debug(message)
            logging.debug(message)

            timestamp = int(time.time())
            logging.debug(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
