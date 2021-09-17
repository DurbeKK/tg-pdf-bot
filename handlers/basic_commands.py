"""
The part that has basic commands like start, help, cancel, etc.
"""

import logging
from os import listdir, mkdir

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from loader import dp, input_path, output_path
from states.all_states import *
from utils.clean_up import reset

# this dictionary contains some text and states for each operation
operations_dict = {
    "merge": {
        "state": MergingStates.waiting_for_files_to_merge,
        "text": "Alright, just send me the files that you want merged.",
    },
    "compress": {
        "state": CompressingStates.waiting_for_files_to_compress,
        "text": "Cool, send me the PDF that you want compressed and I'll "
        "start working on it right away.",
    },
    "encrypt": {
        "state": CryptingStates.waiting_for_files_to_encrypt,
        "text": "Okay, send me the PDF that you want to encrypt.",
    },
    "decrypt": {
        "state": CryptingStates.waiting_for_files_to_decrypt,
        "text": "Okay, send me the PDF that you want to decrypt",
    },
    "split": {
        "state": SplittingStates.waiting_for_files_to_split,
        "text": "Sure, first send me the PDF that you want to split.",
    },
    "Word to PDF": {
        "state": ConvertingStates.waiting_for_word_docs,
        "text": "Ok, send me the Word document(s) you'd like to convert to PDF",
    },
    "Image(s) to PDF": {
        "state": ConvertingStates.waiting_for_images,
        "text": "Ok, send me the images that you'd like to convert to a PDF",
    },
}


@dp.message_handler(commands="start", state="*")
async def welcome(message: types.Message):
    """
    This handler will be called when user sends '/start' command.
    Creates directories for new users where their files will be stored
    temporarily until an operation is complete.
    """
    if str(message.chat.id) in listdir(input_path):
        pass
    else:
        mkdir(f"{input_path}/{message.chat.id}")
        mkdir(f"{output_path}/{message.chat.id}")
        logging.info("Directories for new user created")

    await message.reply(
        "Hello, I'm Vivy.\n"
        "My mission is to make people happy by helping them perform basic "
        "operations on their PDF files.\n\n"
        "<b>What I can do</b>\n"
        "<i>/merge</i> - Merge multiple PDF files into one PDF file.\n"
        "<i>/compress</i> - Compress a PDF file (can only compress one "
        "file at a time).\n"
        "<i>/encrypt</i> - Encrypt PDF file with PDF standard encryption "
        "handler.\n"
        "<i>/decrypt</i> - Decrypt PDF file if it was encrypted with the "
        "PDF standard encryption handler.\n"
        "<i>/split</i> - Split PDF (extract certain pages from your PDF, "
        "saving those pages into a separate file).\n"
        "<i>/convert</i> - Convert Word Documents/Images to PDF.\n\n"
        "Type /help for more information."
    )


@dp.message_handler(commands="help", state="*")
async def give_help(message: types.Message):
    """
    This handler will be called when user sends '/help' command
    Provides some simple instructions on how to use the bot.
    """
    await message.reply(
        "<b>Instructions:</b>\nGo to the special commands <b>☰ Menu</b> "
        "and choose the operation that you want me to perform.\n\n"
        "<b>Available commands:</b>\n"
        "<i>/start</i> - Brief info about me.\n"
        "<i>/help</i> - Instructions on how to interact with me.\n"
        "<i>/merge</i> - Merge multiple PDF files into one PDF file.\n"
        "<i>/compress</i> - Compress a PDF file (can only compress one "
        "file at a time).\n"
        "<i>/encrypt</i> - Encrypt PDF file with PDF standard encryption "
        "handler.\n"
        "<i>/decrypt</i> - Decrypt PDF file if it was encrypted with the "
        "PDF standard encryption handler.\n"
        "<i>/split</i> - Split PDF (extract certain pages from your PDF, "
        "saving those pages into a separate file).\n"
        "<i>/convert</i> - Convert Word Documents/Images to PDF.\n"
        "<i>/cancel</i> - Cancel the current operation.\n"
    )


@dp.message_handler(commands="cancel", state="*")
@dp.message_handler(Text(equals="cancel", ignore_case=True), state="*")
async def cancel(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends `/cancel` command.
    Triggers the reset function, which cleans up user input/output files and
    resets the state.
    """
    logging.info("Cancelling operation")

    await reset(message, state)

    await message.reply(
        "Operation cancelled",
        reply_markup=types.ReplyKeyboardRemove(),
    )


@dp.message_handler(
    commands=["merge", "compress", "encrypt", "decrypt", "split", "make"], state="*"
)
async def start_operation(message: types.Message, state: FSMContext):
    """
    This handler will be called when user chooses a PDF operation.
    This will basically just ask the user to start sending the PDF file.
    """
    await reset(message, state)

    command = message.get_command()[1:]

    await operations_dict[command]["state"].set()

    await message.reply(
        operations_dict[command]["text"],
        reply_markup=types.ReplyKeyboardRemove(),
    )


@dp.message_handler(commands="convert", state="*")
async def ask_which_convert(message: types.Message, state: FSMContext):
    """
    This handler will be called when user chooses the `convert` operation.
    This will ask the user to choose the type of conversion.
    """
    await reset(message, state)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Word to PDF", "Image(s) to PDF"]
    keyboard.add(*buttons)
    keyboard.add("Cancel")

    await message.answer(
        "<b>Please choose one of the options for conversion.</b>\n\n"
        "Great, currently I can only do 2 conversions:\n"
        "<i>Word to PDF, Image(s) to PDF</i>",
        reply_markup=keyboard,
    )


@dp.message_handler(Text(equals=["Word to PDF", "Image(s) to PDF"]))
async def start_conversion(message: types.Message):
    """
    This handler will be called when user chooses the type of conversion.
    Asks to send a corresponding file(s).
    """
    await operations_dict[message.text]["state"].set()

    await message.answer(
        operations_dict[message.text]["text"],
        reply_markup=types.ReplyKeyboardRemove(),
    )


@dp.message_handler(
    is_media_group=True,
    content_types=types.message.ContentType.DOCUMENT,
    state=[
        MergingStates.waiting_for_specific_file,
        CompressingStates.waiting_for_files_to_compress,
        CryptingStates.waiting_for_files_to_encrypt,
        CryptingStates.waiting_for_files_to_decrypt,
        SplittingStates.waiting_for_files_to_split,
    ],
)
async def inform_limitations(message: types.Message):
    """
    Some file operations cannot handle multiple files at the same time.
    This will let the user know that.
    """
    await message.reply(
        "I cannot handle multiple files at the same time.\n"
        "Please send a single file."
    )


@dp.message_handler(regexp=("pdf"), state=None)
async def vivy_torreto(message: types.Message):
    """
    An easter egg, I guess.
    This is just a dead meme, but yeah whatever.
    """
    await message.reply("https://ibb.co/9yCkBc1")


@dp.message_handler(regexp=("sing"), state=None)
async def vivy_sing(message: types.Message):
    """
    Another easter egg.
    The anime opening song.
    """
    await message.reply("https://youtu.be/2p8ig-TrYPY")


@dp.message_handler(state=None, content_types=types.message.ContentType.ANY)
async def send_instructions(message: types.Message):
    """
    If a state is not specified, provide some help to the user in case they
    are not able to figure out what to do.
    It's not much, but it's honest work.
    """
    await message.reply("Please choose a command or type /help for instructions.")
