import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from data import config

# these paths will be used in the handlers files
cwd = os.getcwd()
input_path = os.path.join(cwd, "user_files", "input")
output_path = os.path.join(cwd, "user_files", "output")

bot = Bot(token=config.BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

logging.basicConfig(
    level=logging.INFO,
    format=u'%(filename)s [LINE:%(lineno)d] #%(levelname)-8s [%(asctime)s]  %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    )