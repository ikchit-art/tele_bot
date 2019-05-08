import argparse
import sys
from logging import getLogger

from telegram import Bot

from apis.bittrex import BittrexClient
from apis.bittrex import BittrexError
from echo.config import load_config
from echo.draw import drawer
from echo.utils import save_image


logger = getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    # Оба аргумента опциональные, поэтому они начинаются с --
    parser.add_argument("--image", help="Отправить сообщение с картинкой", action="store_true")
    parser.add_argument("--text", help="Отправить сообщение с текстом", action="store_true")
    args = parser.parse_args()

    # Нельзя указать оба сразу
    if args.image and args.text:
        logger.error("Нельзя указать одновременно `--image` и `--text`")
        sys.exit(1)

    # Если ничего не указано, то считаем что это --text
    if not any([args.image, args.text]):
        args.text = True

    config = load_config()

    client = BittrexClient()

    try:
        current_price = client.get_last_price(pair=config.NOTIFY_PAIR)
        message = "{} = {}".format(config.NOTIFY_PAIR, current_price)
    except BittrexError:
        logger.error("BittrexError")
        current_price = None
        message = "Произошла ошибка"

    bot = Bot(
        token=config.TG_TOKEN,
        base_url=config.TG_API_URL,
    )
    if args.text:
        bot.send_message(
            chat_id=config.NOTIFY_USER_ID,
            text=message,
        )
        logger.info("текстовое сообщение отправлено")
    if args.image:
        if current_price:
            text = [config.NOTIFY_PAIR, current_price]
        else:
            text = [config.NOTIFY_PAIR, message]

        img = drawer(text=text)
        photo = save_image(img=img)
        bot.send_photo(
            chat_id=config.NOTIFY_USER_ID,
            photo=photo,
            caption='Подпись под фото',
        )
        logger.info("картинка отправлена")


if __name__ == '__main__':
    main()
