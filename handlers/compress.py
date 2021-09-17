"""
The part that deals with compressing PDF files.
"""

import logging
import subprocess
from os import listdir
from os.path import getsize

from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import bot, dp, input_path, output_path
from states.all_states import CompressingStates
from utils.clean_up import reset
from utils.convert_file_size import convert_bytes


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentType.DOCUMENT,
    state=CompressingStates.waiting_for_files_to_compress,
    )
async def compress_file_received(message: types.Message):
    """
    This handler will be called when user provides a file to compress.
    Checks if the file is a PDF and asks to name the output file.
    """
    name = message.document.file_name
    if name.endswith(".pdf"):
        await message.answer("Downloading the file, please wait")

        # replacing empty spaces in the file name with underscores
        # if there are spaces in the file name, some of the code does not work
        # there definitely should be a better way of doing this, but i'm dumb
        if " " in name:
            name = name.replace(" ", "_")

        await bot.download_file_by_id(
            message.document.file_id,
            destination=f"{input_path}/{message.chat.id}/{name}",
            timeout=90,
            )
        logging.info("File (to be compressed) downloaded")
 
        keyboard = types.InlineKeyboardMarkup()

        keyboard.add(
            types.InlineKeyboardButton(
                text="or use the original file name",
                callback_data="Compressed_" + name
            )
        )

        await message.reply(
            "<b>What should the compressed file be called?</b>",
            reply_markup=keyboard,
            )

        # the next state is waiting for a name
        await CompressingStates.next()
    else:
        await message.reply(
            "That's not a PDF file.",
            )


@dp.callback_query_handler(
    text_startswith="Compressed_",
    state=CompressingStates.waiting_for_a_name
    )
async def give_default_name(call: types.CallbackQuery, state: FSMContext):
    """
    This handler will be called when user doesn't want to type in a
    name for the compressed file and wants to use the default name.
    """
    await call.message.delete_reply_markup()

    # storing the default name in the state
    # default name is just "Compressed_" + file name
    await state.update_data(name=call.data)

    await call.answer()

    # calling the compress file function
    await compress_file(message=call.message, state=state)



@dp.message_handler(state=CompressingStates.waiting_for_a_name)
async def compress_file(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends a name for 
    the compressed file.
    Compresses the file and sends it back to the user.
    """
    # if the user chooses the 'use the original file name' option,
    # the default name ("Compressed_" + name) will be stored in the state
    data = await state.get_data()

    if data.get("name"):
        output_name = data.get("name")
    else:
        # this else block will initiate if the user has typed out a file name
        # (didn't choose the default file name option)
        output_name = message.text

    files = listdir(f"{input_path}/{message.chat.id}")

    file = f"{input_path}/{message.chat.id}/{files[0]}"

    logging.info("Compressing started")

    await message.answer("Compressing the file, please wait")

    if " " in output_name:
        output_name = output_name.replace(" ", "_")

    if message.text.lower().endswith(".pdf"):
        compressed_pdf = f"{output_path}/{message.chat.id}/{output_name}"
    else:
        compressed_pdf = f"{output_path}/{message.chat.id}/{output_name}.pdf"

    # using ghostscript to compress the file
    script = (
        "gs -sDEVICE=pdfwrite -dNOPAUSE -dQUIET -dBATCH -dPDFSETTINGS=/screen"
        f" -dCompatibilityLevel=1.4 -sOutputFile={compressed_pdf} {file}"
    )
    command = script.split(" ")

    subprocess.run(command)

    # getting the original file and compressed file size and calculating the
    # reduction in size. using convert_bytes to display the bytes in a
    # readable format
    original_size = convert_bytes(getsize(file))
    compressed_size = convert_bytes(getsize(compressed_pdf))
    reduction = round((1 - (getsize(compressed_pdf) / getsize(file))) * 100)

    await message.answer(
        f"Original file size: <b>{original_size}</b>\n"
        f"Compressed file size: <b>{compressed_size}</b>\n\n"
        f"PDF size reduced by: <b>{reduction}%</b>"
        )

    with open(compressed_pdf, "rb") as result:
        await message.answer_chat_action(action="upload_document")
        await message.reply_document(result, caption="Here you go")
        logging.info("Sent the compressed document")

    await reset(message, state)
