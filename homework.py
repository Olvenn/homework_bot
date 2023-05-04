import logging
import os
import time
import requests
import json
import sys

from http import HTTPStatus

import telegram

from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s'
)


def check_tokens():
    """Проверяем, наличе всех токенов.
    Если нет хотя бы одного, то останавливаем бота.
    """
    # environment_variables = [
    #     PRACTICUM_TOKEN,
    #     TELEGRAM_TOKEN,
    #     TELEGRAM_CHAT_ID
    # ]
    # logging.info('Проверка наличия токенов')
    # return all(environment_variables)
    logging.info('Проверка наличия всех токенов')
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.info(f'Сообщение {message} отправлено в чат %s')
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
    homeworks = response['homeworks']
    current_date = response['current_date']

    if len(response['homeworks']) == 0:
        return []

    if type(response['homeworks']) != dict:
        message = 'Не верный формат ответа.'
        logging.error(message)
        raise TypeError(message)

    if 'homeworks' not in response:
        message = 'Отсутствует ключ homeworks.'
        logging.error(message)
        raise KeyError(message)

    if 'current_date' not in response:
        message = 'Отсутствует ключ current_date.'
        logging.error(message)
        raise KeyError(message)

    if type(homeworks) != list:
        message = 'Не верный формат значения "homeworks".'
        logging.error(message)
        raise TypeError(message)

    if type(current_date) != list:
        message = 'Не верный формат значения "current_date".'
        logging.error(message)
        raise TypeError(message)

    return homeworks


def parse_status(homework):
    """Возвращает статут домашней работы."""
    if 'homework_name' not in homework:
        message = 'Отсутствует значение по ключу homework_name'        
        logging.error(message)
        raise KeyError(message)

    if 'status' not in homework:
        message = 'Отсутствует значение по ключу status'      
        logging.error(message)
        raise KeyError(message)

    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Полученный статус отсутствует в списке HOMEWORK_VERDICTS.'  
        logging.error(message)
        raise KeyError(message)

    verdict = HOMEWORK_VERDICTS[homework_status]
    logging.debug('Изменился статус проверки.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'

# def parse_status(homework):
#     """Возвращает статут домашней работы."""
#     homework_name = homework['homework_name']

#     if 'homework_name' not in homework:
#         message = 'Отсутствует значение по ключу homework_name'
#         logging.error(message)
#         raise KeyError(message)

#     if 'status' not in homework:
#         message = 'Отсутствует значение по ключу statu'
#         logging.error(message)
#         raise KeyError(message)
#     homework_status = homework['status']
#     verdict = HOMEWORK_VERDICTS[homework_status]
    
#     if homework_status not in HOMEWORK_VERDICTS:
#         message = 'Полученный статус отсутствует в списке HOMEWORK_VERDICTS.'
#         logging.error(message)
#         raise KeyError(message)

#     return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствуют переменные окружения. Бот не работает!'
        logging.critical(message)
        sys.exit(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    prev_message = ''
    # prev_status = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if homeworks:
                message = parse_status(homeworks[0])
                if prev_message != message:
                    send_message(bot, message)
                    prev_message = message
                    logging.debug(message)
            else:
                message = 'Нет новых статусов.'
                timestamp = response.get(
                    'current_date', int(time.time()))
                logging.debug(message)

            timestamp = int(time.time())

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
