"""
This module contains only one function that will be used to delete user
input/output files and reset the state prior to and after every operation.
Update: creates directories for users if they don't exist already.
(these directories will temporarily store users' input/output files)
"""
import logging
from os import listdir, unlink, mkdir

from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import input_path, output_path


async def reset(message: types.Message, state: FSMContext):
    """
    If the user doesn't have directories, creates them and resets the state.
    Else: Cleans up user's directories and resets the state.
    """
    logging.info("Resetting the state and deleting all the files")

    await state.finish()

    if str(message.chat.id) in listdir(input_path):
        files = listdir(f"{input_path}/{message.chat.id}")

        for file in files:
            unlink(f"{input_path}/{message.chat.id}/{file}")
            logging.info(f"Deleted input")

        output_files = listdir(f"{output_path}/{message.chat.id}")

        for file in output_files:
            unlink(f"{output_path}/{message.chat.id}/{file}")
            logging.info(f"Deleted output")
    else:
        # new directories are usually created when the user starts the bot
        # but sometimes the bot may crash and once it's launched again,
        # the directories may be gone
        mkdir(f"{input_path}/{message.chat.id}")
        mkdir(f"{output_path}/{message.chat.id}")
        logging.info("Directories for new user created")



