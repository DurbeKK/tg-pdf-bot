from PyPDF2.merger import PdfFileMerger
from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import dp, path, bot

from states.all_states import MergingStates, CompressingStates

from typing import List
import logging
from os import mkdir, listdir, unlink, rename
from os.path import getsize
import subprocess

def convert_bytes(num):
    """
    This function will convert bytes to KB, MB.
    """
    for x in ['bytes', 'KB', 'MB']:
        if num < 1024.0:
            return f"{num:3.1f} {x}"
        num /= 1024.0


@dp.message_handler(commands="start", state="*")
async def welcome_message(message: types.Message):
    """
    This handler will be called when user sends '/start' command
    """
    try:
        mkdir(f"{path}/input_pdfs/{message.chat.id}")
        mkdir(f"{path}/output_pdfs/{message.chat.id}")
    except FileExistsError:
        pass
    else:
        logging.info("Directories for new user created")

    await message.reply(
        "Hello, I'm Vivy.\nMy mission is to make people happy by "
        "helping them perform basic operations on their PDF files.\n\n"
        "<b>What I can do</b>\n"
        "<i>/merge</i> - Merge mutltiple PDF files into one PDF file.\n"
        "<i>/compress</i> - Compress a PDF file (can only compress one "
        "file at a time).\n\n"
        "Type <b>/help</b> for more information."
    )


@dp.message_handler(commands="help", state="*")
async def give_help(message: types.Message):
    """
    This handler will be called when user sends '/help' command
    """
    await message.reply(
        "<b>Instructions:</b>\nGo to the special commands <b>☰ Menu</b> "
        "and choose the operation that you want me to perform.\n\n"
        "<b>Available commands:</b>\n"
        "<i>/start</i> - Brief info about the bot.\n"
        "<i>/help</i> - Help on how to use the bot.\n"
        "<i>/merge</i> - Merge mutltiple PDF files into one PDF file.\n"
        "<i>/compress</i> - Compress a PDF file (can only compress one "
        "file at a time).\n"
        "<i>/cancel</i> - This will cancel the current operation.\n"
    )


@dp.message_handler(commands="compress")
async def start_compressing(message: types.Message):
    """
    This handler will be called when user indicates that they want to
    compress files.
    This will basically just ask the user to start sending the PDF files.
    """
    await CompressingStates.waiting_for_files_to_compress.set()

    await message.reply(
        "Cool, send me the PDF that you want compressed and I'll start "
        "working on it right away."
        )


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentType.DOCUMENT,
    state=CompressingStates.waiting_for_files_to_compress,
    )
async def file_received(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends a file of type `Document`
    (Compressing)
    """
    name = message.document.file_name
    if name.endswith(".pdf"):
        await CompressingStates.next()

        await message.answer("Downloading the file, please wait")

        await bot.download_file_by_id(
            message.document.file_id,
            destination=f"{path}/input_pdfs/{message.chat.id}/{name}",
            timeout=90,
            )
        logging.info("File (to be compressed) downloaded")
 
        await message.reply(
            "What should the compressed file be called?"
            )
    else:
        await message.reply(
            "That's not a PDF file.",
            )


@dp.message_handler(state=CompressingStates.waiting_for_a_name)
async def compress_files(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends a name for 
    the compressed file.
    Compresses the file and sends it back to the user.
    """
    await state.finish()

    files = listdir(f"{path}/input_pdfs/{message.chat.id}")
    
    if " " in files[0]:
        new_name = files[0].replace(" ", "_")
        rename(
            f"{path}/input_pdfs/{message.chat.id}/{files[0]}",
            f"{path}/input_pdfs/{message.chat.id}/{new_name}"
        )
        file = f"{path}/input_pdfs/{message.chat.id}/{new_name}"
    else:
        file = f"{path}/input_pdfs/{message.chat.id}/{files[0]}"

    logging.info("Compressing started")

    await message.answer("Compressing the file, please wait")

    if message.text[-4:].lower() == ".pdf":
        compressed_pdf = f"{path}/output_pdfs/{message.chat.id}/{message.text}"
    else:
        compressed_pdf = f"{path}/output_pdfs/{message.chat.id}/{message.text}.pdf"

    script = (
        "gs -sDEVICE=pdfwrite -dNOPAUSE -dQUIET -dBATCH -dPDFSETTINGS=/screen"
        f" -dCompatibilityLevel=1.4 -sOutputFile={compressed_pdf} {file}"
    )
    command = script.split(" ")

    subprocess.run(command)

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

    unlink(file)
    logging.info(f"Deleted input PDF (to be compressed)")

    unlink(compressed_pdf)
    logging.info(f"Deleted output PDF (compressed)")


@dp.message_handler(commands="merge")
async def start_merging(message: types.Message):
    """
    This handler will be called when user indicates that they want to 
    merge files.
    This will basically just ask the user to start sending the PDF files.
    """
    await MergingStates.waiting_for_files_to_merge.set()

    await message.reply("Alright, just send the me the files that you want merged.")


@dp.message_handler(commands="done", state=MergingStates.waiting_for_files_to_merge)
async def get_confirmation(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends `/done` command.
    Gets confirmation on the files that need to be merged.
    """
    await state.finish()

    files = sorted(listdir(f"{path}/input_pdfs/{message.chat.id}"))

    if not files:
        await message.reply("You didn't send any PDF files.")
    elif len(files) == 1:
        await message.reply(
            "You sent only one file. What am I supposed to merge it with?"
        )
    else:
        file_list = [f"{index}. {value[3:]}" for index, value in enumerate(files, start=1)] 
        file_list = "\n".join(file_list)

        keyboard = types.InlineKeyboardMarkup()
        buttons = [
            types.InlineKeyboardButton(text="Yes", callback_data="ask_for_name"),
            types.InlineKeyboardButton(text="No", callback_data="modify_files"),
        ]
        keyboard.add(*buttons)

        await message.reply(
            f"<b><u>Are these the files that you want to merge?</u></b>\n\n{file_list}",
            reply_markup=keyboard
        )


@dp.message_handler(commands="cancel", state="*")
async def cancel_merging(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends `/cancel` command.
    Resets the state and deletes all the PDF files.
    """
    logging.info("Cancelling operation")

    await state.finish()

    files = listdir(f'{path}/input_pdfs/{message.chat.id}')

    for file in files:
        unlink(f"{path}/input_pdfs/{message.chat.id}/{file}")
        logging.info(f"Deleted input PDF")

    output_files = listdir(f'{path}/output_pdfs/{message.chat.id}')

    for file in output_files:
        unlink(f"{path}/output_pdfs/{message.chat.id}/{file}")
        logging.info(f"Deleted output PDF")

    await message.reply("Operation cancelled")


@dp.message_handler(
    is_media_group=True,
    content_types=types.ContentType.DOCUMENT,
    state=MergingStates.waiting_for_files_to_merge
    )
async def handle_albums(message: types.Message, album: List[types.Message]):
    """This handler will receive a complete album of any type. (Merging)"""
    await message.answer("Downloading files, please wait")

    for obj in album:
        name = obj.document.file_name

        if name[-4:].lower() != ".pdf":
            return await message.answer("That's not a PDF file.")
        
        file_count = len(listdir(f'{path}/input_pdfs/{message.chat.id}')) + 1

        if file_count < 10:
            file_count = "0" + str(file_count)

        await bot.download_file_by_id(
            obj.document.file_id,
            destination=f"{path}/input_pdfs/{message.chat.id}/{file_count}_{name}",
            )
        logging.info("File downloaded.")

    await message.answer(
        "Great, if you have any more PDF files you want to merge, "
        "send them now. Once you are done, send /done"
    )


@dp.message_handler(
    content_types=types.message.ContentType.DOCUMENT,
    state=MergingStates.waiting_for_files_to_merge
    )
async def file_received(message: types.Message):
    """
    This handler will be called when user sends a file of type `Document`
    (Merging)
    """
    name = message.document.file_name
    if name.endswith(".pdf"):
        file_count = len(listdir(f'{path}/input_pdfs/{message.chat.id}')) + 1

        if file_count < 10:
            file_count = "0" + str(file_count)

        await message.answer("Downloading the file, please wait")

        await bot.download_file_by_id(
            message.document.file_id,
            destination=f"{path}/input_pdfs/{message.chat.id}/{file_count}_{name}",
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
    state=MergingStates.waiting_for_specific_file
    )
async def specific_file_received(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends a file of type `Document`
    that has to be added to a certain position in the list of files.
    (Merging)
    """
    name = message.document.file_name
    if name.endswith(".pdf"):
        logging.info("Adding a file")

        file_count = await state.get_data()
        file_count = file_count["num"]

        if file_count < 10:
            file_count = "0" + str(file_count)

        await message.answer("Downloading the file, please wait")

        await bot.download_file_by_id(
            message.document.file_id,
            destination=f"{path}/input_pdfs/{message.chat.id}/{file_count}_{name}",
            )
        logging.info("File downloaded")

        await state.finish()
 
        await get_confirmation(message)
    else:
        await message.reply(
            "That's not a PDF file.",
            )


@dp.message_handler(state=MergingStates.waiting_for_a_name)
async def merge_files(message: types.Message, state: FSMContext):
    await state.finish()

    files = sorted(listdir(f"{path}/input_pdfs/{message.chat.id}"))

    logging.info("Merging started")

    merger = PdfFileMerger(strict=False)

    for file in files:
        merger.append(f"{path}/input_pdfs/{message.chat.id}/{file}")

    if message.text[-4:].lower() == ".pdf":
        merged_pdf_name = message.text
    else:
        merged_pdf_name = message.text + ".pdf"

    merger.write(f"{path}/output_pdfs/{message.chat.id}/{merged_pdf_name}")
    merger.close()

    with open(f"{path}/output_pdfs/{message.chat.id}/{merged_pdf_name}", "rb") as result:
        await message.answer_chat_action(action="upload_document")
        await message.reply_document(result, caption="Here you go")
        logging.info("Sent the document")

    for file in files:
        unlink(f"{path}/input_pdfs/{message.chat.id}/{file}")
        logging.info(f"Deleted input PDF")

    unlink(f"{path}/output_pdfs/{message.chat.id}/{merged_pdf_name}")
    logging.info(f"Deleted output PDF")


@dp.message_handler(
    is_media_group=True,
    content_types=types.message.ContentType.DOCUMENT,
    state=MergingStates.waiting_for_specific_file
    )
async def inform_limitations(message: types.Message):
    await message.reply(
        "I cannot add multiple files at the same time.\n"
        "Please send a single file."
        )


@dp.message_handler(state=None)
async def send_instructions(message: types.Message):
    await message.reply("Type /help to see more information.")
