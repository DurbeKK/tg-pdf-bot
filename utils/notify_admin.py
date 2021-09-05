import logging
from aiogram import Dispatcher
from data.config import ADMIN

async def notify_on_startup(dp: Dispatcher):
    try:
        await dp.bot.send_message(ADMIN, "Bot launched!")
    except Exception as err:
        logging.exception(err)