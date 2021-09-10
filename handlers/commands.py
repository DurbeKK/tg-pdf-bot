from PyPDF2.merger import PdfFileMerger, PdfFileReader, PdfFileWriter
from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import dp, path, bot

from states.all_states import MergingStates, CompressingStates, EncryptingStates

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
        "<i>/merge</i> - Merge multiple PDF files into one PDF file.\n"
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
        "<i>/start</i> - Brief info about me.\n"
        "<i>/help</i> - Instructions on how to interact with me.\n"
        "<i>/merge</i> - Merge multiple PDF files into one PDF file.\n"
        "<i>/compress</i> - Compress a PDF file (can only compress one "
        "file at a time).\n"
        "<i>/cancel</i> - Cancel the current operation.\n"
    )


async def reset(message: types.Message, state: FSMContext):
    """
    Resets that state and deletes all the files.
    """
    logging.info("Resetting the state and deleting all the files")

    await state.finish()

    files = listdir(f'{path}/input_pdfs/{message.chat.id}')

    for file in files:
        unlink(f"{path}/input_pdfs/{message.chat.id}/{file}")
        logging.info(f"Deleted input PDF")

    output_files = listdir(f'{path}/output_pdfs/{message.chat.id}')

    for file in output_files:
        unlink(f"{path}/output_pdfs/{message.chat.id}/{file}")
        logging.info(f"Deleted output PDF")


@dp.message_handler(commands="encrypt", state="*")
async def start_encrypting(message: types.Message, state: FSMContext):
    """
    This handler will be called when user chooses the encrypt operation.
    This will basically just ask the user to start sending the PDF file.
    """
    await reset(message, state)

    await EncryptingStates.waiting_for_files_to_encrypt.set()

    await message.reply(
        "Okay, send the me PDF that you want to encrypt."
    )


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentType.DOCUMENT,
    state=EncryptingStates.waiting_for_files_to_encrypt,
)
async def encrypt_file_received(message: types.Message):
    """
    This handler will be called when user sends a file of type `Document`
    (Encrypting)
    """
    name = message.document.file_name
    if name.endswith(".pdf"):
        await message.answer("Downloading the file, please wait")

        await bot.download_file_by_id(
            message.document.file_id,
            destination=f"{path}/input_pdfs/{message.chat.id}/{name}",
            timeout=90,
            )
        logging.info("File (to be encrypted) downloaded")

        await message.reply(
            "<b>Great, type the password you want to encrypt with.</b>",
            )

        await EncryptingStates.next()
    else:
        await message.reply(
            "That's not a PDF file.",
            )


@dp.message_handler(state=EncryptingStates.waiting_for_password)
async def encrypt_file(message: types.Message, state: FSMContext):
    """
    This handler will be called when user types in a password for encryption.
    Encrypts the file with that password.
    """
    await state.finish()

    logging.info("Encrypting started")

    await message.reply("Working on it, please wait")

    files = listdir(f"{path}/input_pdfs/{message.chat.id}")

    new_name = files[0].replace(" ", "_")
    rename(
        f"{path}/input_pdfs/{message.chat.id}/{files[0]}",
        f"{path}/input_pdfs/{message.chat.id}/{new_name}"
    )

    input_file = f"{path}/input_pdfs/{message.chat.id}/{new_name}"
    output_file = f"{path}/output_pdfs/{message.chat.id}/Encrypted_{new_name}"

    file = open(input_file, "rb")

    input_pdf = PdfFileReader(file)

    output_pdf = PdfFileWriter()
    output_pdf.appendPagesFromReader(input_pdf)
    output_pdf.encrypt(message.text)

    with open(output_file, "wb") as result:
        output_pdf.write(result)
    
    file.close()

    with open(output_file, "rb") as result:
        await message.answer_chat_action(action="upload_document")
        await message.reply_document(result, caption="Here you go")

    unlink(input_file)
    logging.info("Deleted input PDF (to be encrypted)")

    unlink(output_file)
    logging.info("Deleted output PDF (encrypted)")


@dp.message_handler(commands="compress", state="*")
async def start_compressing(message: types.Message, state: FSMContext):
    """
    This handler will be called when user chooses the compress operation.
    This will basically just ask the user to start sending the PDF file.
    """
    await reset(message, state)

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
async def compress_file_received(message: types.Message):
    """
    This handler will be called when user sends a file of type `Document`
    (Compressing)
    """
    name = message.document.file_name
    if name.endswith(".pdf"):
        await message.answer("Downloading the file, please wait")

        await bot.download_file_by_id(
            message.document.file_id,
            destination=f"{path}/input_pdfs/{message.chat.id}/{name}",
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

        await CompressingStates.next()
    else:
        await message.reply(
            "That's not a PDF file.",
            )


@dp.message_handler(state=CompressingStates.waiting_for_a_name)
async def compress_file(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends a name for 
    the compressed file.
    Compresses the file and sends it back to the user.
    """
    # if the user chooses the 'use the original file name' option,
    # the default name will be stored in the state
    data = await state.get_data()

    if data.get("name"):
        output_name = data.get("name")
    else:
        # this else block will initiate if the user has typed out a file name
        # (didn't choose the default file name option)
        output_name = message.text

    await state.finish()

    files = listdir(f"{path}/input_pdfs/{message.chat.id}")

    new_name = files[0].replace(" ", "_")
    rename(
        f"{path}/input_pdfs/{message.chat.id}/{files[0]}",
        f"{path}/input_pdfs/{message.chat.id}/{new_name}"
    )
    file = f"{path}/input_pdfs/{message.chat.id}/{new_name}"

    logging.info("Compressing started")

    await message.answer("Compressing the file, please wait")

    if " " in output_name:
        compressed_name = output_name.replace(" ", "_")
    else:
        compressed_name = output_name

    if message.text[-4:].lower() == ".pdf":
        compressed_pdf = f"{path}/output_pdfs/{message.chat.id}/{compressed_name}"
    else:
        compressed_pdf = f"{path}/output_pdfs/{message.chat.id}/{compressed_name}.pdf"

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


@dp.message_handler(commands="merge", state="*")
async def start_merging(message: types.Message, state: FSMContext):
    """
    This handler will be called when user chooses the merge operation
    This will basically just ask the user to start sending the PDF files.
    """
    await reset(message, state)

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
async def cancel(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends `/cancel` command.
    Resets the state and deletes all the PDF files.
    """
    logging.info("Cancelling operation")

    await reset(message, state)

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
async def merge_file_received(message: types.Message):
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
 
        await get_confirmation(message, state)
    else:
        await message.reply(
            "That's not a PDF file.",
            )


@dp.message_handler(state=MergingStates.waiting_for_a_name)
async def merge_files(message: types.Message, state: FSMContext):
    await state.finish()

    await message.answer("Working on it")

    files = sorted(listdir(f"{path}/input_pdfs/{message.chat.id}"))

    logging.info("Merging started")

    merger = PdfFileMerger(strict=False)

    for file in files:
        merger.append(f"{path}/input_pdfs/{message.chat.id}/{file}")

    merged_pdf_name = message.text.replace(" ", "_")

    if message.text[-4:].lower() != ".pdf":
        merged_pdf_name = merged_pdf_name + ".pdf"

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
    state=[
        MergingStates.waiting_for_specific_file,
        CompressingStates.waiting_for_files_to_compress,
        EncryptingStates.waiting_for_files_to_encrypt,
        ]
    )
async def inform_limitations(message: types.Message):
    await message.reply(
        "I cannot handle multiple files at the same time.\n"
        "Please send a single file."
        )


@dp.message_handler(regexp=("(s|S)ing"), state=None)
async def vivy_sing(message: types.Message):
    await message.reply("https://youtu.be/2p8ig-TrYPY")


@dp.message_handler(
    state=None,
    content_types=types.message.ContentType.ANY)
async def send_instructions(message: types.Message):
    await message.reply("Please choose a command or type /help for instructions.")
