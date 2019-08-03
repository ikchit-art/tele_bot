import datetime
from logging import getLogger
from subprocess import Popen
from subprocess import PIPE
from uuid import uuid4

from telegram import Bot
from telegram import Update
from telegram import ParseMode
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import InlineQueryResultArticle
from telegram import InputTextMessageContent
from telegram import ReplyKeyboardRemove
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram.ext import CallbackQueryHandler
from telegram.ext import InlineQueryHandler
from telegram.utils.helpers import escape_markdown

from apis.bittrex import BittrexClient
from apis.bittrex import BittrexError
from echo.config import load_config
from echo.buttons import BUTTON1_HELP
from echo.buttons import BUTTON2_TIME
from echo.buttons import get_base_reply_keyboard


config = load_config()

logger = getLogger(__name__)


def debug_requests(f):
    """ Декоратор для отладки событий от телеграма
    """
    def inner(*args, **kwargs):
        try:
            logger.info("Обращение в функцию {}".format(f.__name__))
            return f(*args, **kwargs)
        except Exception:
            logger.exception("Ошибка в обработчике {}".format(f.__name__))
            if len(args) == 2:
                update = args[1]
                logger.error("Сообщение: %s", update.effective_message)
            raise

    return inner


# `callback_data` -- это то, что будет присылать TG при нажатии на каждую кнопку.
# Поэтому каждый идентификатор должен быть уникальным
CALLBACK_BUTTON1_LEFT = "callback_button1_left"
CALLBACK_BUTTON2_RIGHT = "callback_button2_right"
CALLBACK_BUTTON3_MORE = "callback_button3_more"
CALLBACK_BUTTON4_BACK = "callback_button4_back"
CALLBACK_BUTTON5_TIME = "callback_button5_time"
CALLBACK_BUTTON6_PRICE = "callback_button6_price"
CALLBACK_BUTTON7_PRICE = "callback_button7_price"
CALLBACK_BUTTON8_PRICE = "callback_button8_price"
CALLBACK_BUTTON_HIDE_KEYBOARD = "callback_button9_hide"


TITLES = {
    CALLBACK_BUTTON1_LEFT: "Новое сообщение ⚡️",
    CALLBACK_BUTTON2_RIGHT: "Отредактировать ✏️",
    CALLBACK_BUTTON3_MORE: "Ещё ➡️",
    CALLBACK_BUTTON4_BACK: "Назад ⬅️",
    CALLBACK_BUTTON5_TIME: "Время ⏰",
    CALLBACK_BUTTON6_PRICE: "BTC 💰",
    CALLBACK_BUTTON7_PRICE: "LTC 💰",
    CALLBACK_BUTTON8_PRICE: "ETH 💰",
    CALLBACK_BUTTON_HIDE_KEYBOARD: "Спрять клавиатуру",
}

# Глобально инициализируем клиент API Bittrex
client = BittrexClient()


def get_base_inline_keyboard():
    """ Получить клавиатуру для сообщения
        Эта клавиатура будет видна под каждым сообщением, где её прикрепили
    """
    # Каждый список внутри `keyboard` -- это один горизонтальный ряд кнопок
    keyboard = [
        # Каждый элемент внутри списка -- это один вертикальный столбец.
        # Сколько кнопок -- столько столбцов
        [
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON1_LEFT], callback_data=CALLBACK_BUTTON1_LEFT),
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON2_RIGHT], callback_data=CALLBACK_BUTTON2_RIGHT),
        ],
        [
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON_HIDE_KEYBOARD], callback_data=CALLBACK_BUTTON_HIDE_KEYBOARD),
        ],
        [
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON3_MORE], callback_data=CALLBACK_BUTTON3_MORE),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_keyboard2():
    """ Получить вторую страницу клавиатуры для сообщений
        Возможно получить только при нажатии кнопки на первой клавиатуре
    """
    keyboard = [
        [
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON5_TIME], callback_data=CALLBACK_BUTTON5_TIME),
        ],
        [
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON6_PRICE], callback_data=CALLBACK_BUTTON6_PRICE),
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON7_PRICE], callback_data=CALLBACK_BUTTON7_PRICE),
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON8_PRICE], callback_data=CALLBACK_BUTTON8_PRICE),
        ],
        [
            InlineKeyboardButton(TITLES[CALLBACK_BUTTON4_BACK], callback_data=CALLBACK_BUTTON4_BACK),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


@debug_requests
def keyboard_callback_handler(bot: Bot, update: Update, **kwargs):
    """ Обработчик ВСЕХ кнопок со ВСЕХ клавиатур
    """
    query = update.callback_query
    data = query.data
    now = datetime.datetime.now()

    # Обратите внимание: используется `effective_message`
    chat_id = update.effective_message.chat_id
    current_text = update.effective_message.text

    if data == CALLBACK_BUTTON1_LEFT:
        # "Удалим" клавиатуру у прошлого сообщения
        # (на самом деле отредактируем его так, что текст останется тот же, а клавиатура пропадёт)
        query.edit_message_text(
            text=current_text,
            parse_mode=ParseMode.MARKDOWN,
        )
        # Отправим новое сообщение при нажатии на кнопку
        bot.send_message(
            chat_id=chat_id,
            text="Новое сообщение\n\ncallback_query.data={}".format(data),
            reply_markup=get_base_inline_keyboard(),
        )
    elif data == CALLBACK_BUTTON2_RIGHT:
        # Отредактируем текст сообщения, но оставим клавиатуру
        query.edit_message_text(
            text="Успешно отредактировано в {}".format(now),
            reply_markup=get_base_inline_keyboard(),
        )
    elif data == CALLBACK_BUTTON3_MORE:
        # Показать следующий экран клавиатуры
        # (оставить тот же текст, но указать другой массив кнопок)
        query.edit_message_text(
            text=current_text,
            reply_markup=get_keyboard2(),
        )
    elif data == CALLBACK_BUTTON4_BACK:
        # Показать предыдущий экран клавиатуры
        # (оставить тот же текст, но указать другой массив кнопок)
        query.edit_message_text(
            text=current_text,
            reply_markup=get_base_inline_keyboard(),
        )
    elif data == CALLBACK_BUTTON5_TIME:
        # Покажем новый текст и оставим ту же клавиатуру
        text = "*Точное время*\n\n{}".format(now)
        query.edit_message_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_keyboard2(),
        )
    elif data in (CALLBACK_BUTTON6_PRICE, CALLBACK_BUTTON7_PRICE, CALLBACK_BUTTON8_PRICE):
        pair = {
            CALLBACK_BUTTON6_PRICE: "USD-BTC",
            CALLBACK_BUTTON7_PRICE: "USD-LTC",
            CALLBACK_BUTTON8_PRICE: "USD-ETH",
        }[data]

        try:
            current_price = client.get_last_price(pair=pair)
            text = "*Курс валюты:*\n\n*{}* = {}$".format(pair, current_price)
        except BittrexError:
            text = "Произошла ошибка :(\n\nПопробуйте ещё раз"
        query.edit_message_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_keyboard2(),
        )
    elif data == CALLBACK_BUTTON_HIDE_KEYBOARD:
        # Спрятать клавиатуру
        # Работает только при отправке нового сообщение
        # Можно было бы отредактировать, но тогда нужно точно знать что у сообщения не было кнопок
        bot.send_message(
            chat_id=chat_id,
            text="Спрятали клавиатуру\n\nНажмите /start чтобы вернуть её обратно",
            reply_markup=ReplyKeyboardRemove(),
        )


@debug_requests
def do_start(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text="Привет! Отправь мне что-нибудь",
        reply_markup=get_base_reply_keyboard(),
    )


@debug_requests
def do_help(bot: Bot, update: Update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text="Это учебный бот\n\n"
             "Список доступных команд есть в меню\n\n"
             "Так же я отвечую на любое сообщение",
        reply_markup=get_base_inline_keyboard(),
    )


@debug_requests
def do_time(bot: Bot, update: Update):
    """ Узнать серверное время
    """
    process = Popen(["date"], stdout=PIPE)
    text, error = process.communicate()
    # Может произойти ошибка вызова процесса (код возврата не 0)
    if error:
        text = "Произошла ошибка, время неизвестно"
    else:
        # Декодировать ответ команды из процесса
        text = text.decode("utf-8")
    bot.send_message(
        chat_id=update.message.chat_id,
        text=text,
        reply_markup=get_base_inline_keyboard(),
    )


@debug_requests
def do_echo(bot: Bot, update: Update):
    chat_id = update.message.chat_id
    text = update.message.text
    if text == BUTTON1_HELP:
        return do_help(bot=bot, update=update)
    elif text == BUTTON2_TIME:
        return do_time(bot=bot, update=update)
    else:
        reply_text = "Ваш ID = {}\n\n{}".format(chat_id, text)
        bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_markup=get_base_inline_keyboard(),
        )


@debug_requests
def inline_query_handler(bot: Bot, update: Update):
    query = update.inline_query.query
    results = [
        InlineQueryResultArticle(
            id=uuid4(),
            title="Caps",
            input_message_content=InputTextMessageContent(query.upper()),
        ),
        InlineQueryResultArticle(
            id=uuid4(),
            title="Bold",
            input_message_content=InputTextMessageContent(
                "*{}*".format(escape_markdown(query)),
                parse_mode=ParseMode.MARKDOWN,
            ),
        ),
        InlineQueryResultArticle(
            id=uuid4(),
            title="Italic",
            input_message_content=InputTextMessageContent(
                "_{}_".format(escape_markdown(query)),
                parse_mode=ParseMode.MARKDOWN,
            ),
        ),
    ]
    update.inline_query.answer(results)


def main():
    bot = Bot(
        token=config.TG_TOKEN,
        base_url=config.TG_API_URL,
    )
    updater = Updater(
        bot=bot,
    )
    logger.info("Запускаем бота %s", updater.bot.username)

    start_handler = CommandHandler("start", do_start)
    help_handler = CommandHandler("help", do_help)
    time_handler = CommandHandler("time", do_time)
    message_handler = MessageHandler(Filters.text, do_echo)
    buttons_handler = CallbackQueryHandler(callback=keyboard_callback_handler)
    inline_handler = InlineQueryHandler(callback=inline_query_handler)

    updater.dispatcher.add_handler(start_handler)
    updater.dispatcher.add_handler(help_handler)
    updater.dispatcher.add_handler(time_handler)
    updater.dispatcher.add_handler(message_handler)
    updater.dispatcher.add_handler(buttons_handler)
    # updater.dispatcher.add_handler(inline_handler)

    # Начать обработку входящих сообщений
    updater.start_polling()
    # Не прерывать скрипт до обработки всех сообщений
    updater.idle()

    logger.info("Закончили...")


if __name__ == '__main__':
    main()
