"""
This module contains only one function that will be used to delete user
input/output files and reset the state prior to and after every operation.
"""
from loader import input_path, output_path
from aiogram import types
from aiogram.dispatcher import FSMContext
from os import listdir, unlink
import logging


async def reset(message: types.Message, state: FSMContext):
    """
    Cleans up user's directories and resets the state.
    """
    logging.info("Resetting the state and deleting all the files")

    await state.finish()

    files = listdir(f"{input_path}/{message.chat.id}")

    for file in files:
        unlink(f"{input_path}/{message.chat.id}/{file}")
        logging.info(f"Deleted input")

    output_files = listdir(f"{output_path}/{message.chat.id}")

    for file in output_files:
        unlink(f"{output_path}/{message.chat.id}/{file}")
        logging.info(f"Deleted output")
