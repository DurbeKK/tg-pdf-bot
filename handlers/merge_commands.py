"""
The part that deals with merging PDF files into one.
(message handlers)
"""

import logging
from os import listdir
from typing import List

from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import bot, dp, input_path, output_path
from PyPDF2 import PdfFileMerger
from states.all_states import MergingStates
from utils.clean_up import reset


@dp.message_handler(commands="done", state=MergingStates.waiting_for_files_to_merge)
async def get_confirmation(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends `/done` command.
    Gets confirmation on the files that need to be merged.
    """
    await state.finish()

    # sorted is called since the file names have corresponding file counts
    # this is done to maintain the order of the files
    # (the files will be merged in the order that the user sends the files in)
    files = sorted(listdir(f"{input_path}/{message.chat.id}"))

    if not files:
        await message.reply("You didn't send any PDF files.")
    elif len(files) == 1:
        await message.reply(
            "You sent only one file. What am I supposed to merge it with?"
        )
    else:
        # since file names are in this format: number_name ("01_cool.pdf")
        # to provide a list of pdfs for the user, we make the list with a
        # list comprehension, not displaing the number part of the file
        # ("01_" in case of "01_cool.pdf")
        file_list = [
            f"{index}. {value[3:]}" for index, value in enumerate(files, start=1)
        ]
        file_list = "\n".join(file_list)

        keyboard = types.InlineKeyboardMarkup()
        buttons = [
            types.InlineKeyboardButton(text="Yes", callback_data="ask_for_name"),
            types.InlineKeyboardButton(text="No", callback_data="modify_files"),
        ]
        keyboard.add(*buttons)

        await message.reply(
            (
                "<b><u>Are these the files that you want to merge?</u></b>\n\n"
                + file_list
            ),
            reply_markup=keyboard,
        )


@dp.message_handler(
    is_media_group=True,
    content_types=types.ContentType.DOCUMENT,
    state=MergingStates.waiting_for_files_to_merge,
)
async def handle_albums(message: types.Message, album: List[types.Message]):
    """
    This handler will be called when user sends a group of files
    as an album for merging. Checks if the files are PDF files and asks
    if there are any more files that need to be merged.
    """
    await message.answer("Downloading files, please wait")

    for obj in album:
        name = obj.document.file_name

        # replacing empty spaces in the file name with underscores
        # if there are spaces in the file name, some of the code does not work
        # there definitely should be a better way of doing this, but i'm dumb
        if " " in name:
            name = name.replace(" ", "_")

        if not name.lower().endswith(".pdf"):
            return await message.answer("That's not a PDF file.")

        # initially there should be no files in this directory,
        # so to start with "1" for the first file, we add 1
        # the whole reason why we have the file count is so that the order
        # of files is maintained and can be changed around later.
        file_count = len(listdir(f"{input_path}/{message.chat.id}")) + 1

        # to have file counts like "01", "02", etc so that the order is still
        # maintained if the user sends more than 9 files
        if file_count < 10:
            file_count = "0" + str(file_count)

        await bot.download_file_by_id(
            obj.document.file_id,
            destination=f"{input_path}/{message.chat.id}/{file_count}_{name}",
        )
        logging.info("File downloaded.")

    await message.answer(
        "Great, if you have any more PDF files you want to merge, "
        "send them now. Once you are done, send /done"
    )


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentType.DOCUMENT,
    state=MergingStates.waiting_for_files_to_merge,
)
async def merge_file_received(message: types.Message):
    """
    This handler will be called when user provides a file for merging.
    Checks if the file is a PDF and asks if there are any more files
    that need to be merged.
    """
    name = message.document.file_name
    if name.endswith(".pdf"):
        # replacing empty spaces in the file name with underscores
        # if there are spaces in the file name, some of the code does not work
        # there definitely should be a better way of doing this, but i'm dumb
        if " " in name:
            name = name.replace(" ", "_")

        # initially there should be no files in this directory,
        # so to start with "1" for the first file, we add 1
        # the whole reason why we have the file count is so that the order
        # of files is maintained and can be changed around later.
        file_count = len(listdir(f"{input_path}/{message.chat.id}")) + 1

        # to have file counts like "01", "02", etc so that the order is still
        # maintained if the user sends more than 9 files
        if file_count < 10:
            file_count = "0" + str(file_count)

        await message.answer("Downloading the file, please wait")

        await bot.download_file_by_id(
            message.document.file_id,
            destination=f"{input_path}/{message.chat.id}/{file_count}_{name}",
        )
        logging.info("File downloaded")

        await message.reply(
            "Great, if you have any more PDF files you want to merge, "
            "send them now. Once you are done, send /done"
        )
    else:
        await message.reply(
            "That's not a PDF file.",
        )


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentType.DOCUMENT,
    state=MergingStates.waiting_for_specific_file,
)
async def specific_file_received(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends a file of type `Document`
    that has to be added to a certain position in the list of files (Merging).
    Checks if the file is a PDF and adds it to the desired position in the
    list of files. This is done by naming the file with the appropriate
    file count number.
    After the file is added, triggers the get confirmation function to
    confirm the new list of files.
    """
    name = message.document.file_name
    if name.endswith(".pdf"):
        logging.info("Adding a file")

        # replacing empty spaces in the file name with underscores
        # if there are spaces in the file name, some of the code does not work
        # there definitely should be a better way of doing this, but i'm dumb
        if " " in name:
            name = name.replace(" ", "_")

        # the desired position of the file will be stored in the state
        file_count = await state.get_data()
        file_count = file_count["num"]

        # to have file counts like "01", "02", etc so that the order is still
        # maintained if the user sends more than 9 files
        if file_count < 10:
            file_count = "0" + str(file_count)

        await message.answer("Downloading the file, please wait")

        await bot.download_file_by_id(
            message.document.file_id,
            destination=f"{input_path}/{message.chat.id}/{file_count}_{name}",
        )
        logging.info("File downloaded")

        await state.finish()

        # getting confirmation on the new list of files
        await get_confirmation(message, state)
    else:
        await message.reply(
            "That's not a PDF file.",
        )


@dp.message_handler(state=MergingStates.waiting_for_a_name)
async def merge_files(message: types.Message, state: FSMContext):
    """
    This handler will be called when user provides a name for the merged PDF.
    Merges all the input files into one output PDF and sends it to the user.
    """
    await message.answer("Working on it")

    # sorted is called since the file names have corresponding file counts
    # this is done to maintain the order of the files
    # (the files will be merged in the order that the user sends the files in)
    files = sorted(listdir(f"{input_path}/{message.chat.id}"))

    logging.info("Merging started")

    merger = PdfFileMerger(strict=False)

    for file in files:
        merger.append(f"{input_path}/{message.chat.id}/{file}")

    # replace the white space with underscores if there are spaces
    # otherwise some stuff doesn't work, im too dumb to figure out why for now
    merged_pdf_name = message.text.replace(" ", "_")

    if not message.text.lower().endswith(".pdf"):
        merged_pdf_name = merged_pdf_name + ".pdf"

    output = f"{output_path}/{message.chat.id}/{merged_pdf_name}"

    merger.write(output)
    merger.close()

    with open(output, "rb") as result:
        await message.answer_chat_action(action="upload_document")
        await message.reply_document(result, caption="Here you go")
        logging.info("Sent the document")

    await reset(message, state)
