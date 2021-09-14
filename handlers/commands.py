from PyPDF2.merger import PdfFileMerger, PdfFileReader, PdfFileWriter
import img2pdf
from PIL import Image
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from loader import dp, path, bot

from states.all_states import *

from typing import List
import logging
from os import mkdir, listdir, unlink, rename
from os.path import getsize
import subprocess

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
        "text": "Sure, first send me the PDF that you want to split." 
    },
    "Word to PDF": {
        "state": ConvertingStates.waiting_for_word_docs,
        "text": "Ok, send me the Word document you'd like to convert to a PDF"
    },
    "Image(s) to PDF": {
        "state": ConvertingStates.waiting_for_images,
        "text": "Ok, send me the images that you'd like to convert to a PDF"
    }
}


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
        "file at a time).\n"
        "<i>/encrypt</i> - Encrypt PDF file with PDF standard encryption handler.\n" 
        "<i>/decrypt</i> - Decrypt PDF file if it was encrypted with the "
        "PDF standard encryption handler.\n" 
        "<i>/split</i> - Split PDF (extract certain pages from your PDF, "
        "saving those pages into a separate file).\n\n"
        "Type /help for more information."
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
        "<i>/encrypt</i> - Encrypt PDF file with PDF standard encryption handler.\n"
        "<i>/decrypt</i> - Decrypt PDF file if it was encrypted with the "
        "PDF standard encryption handler.\n"
        "<i>/split</i> - Split PDF (extract certain pages from your PDF, "
        "saving those pages into a separate file).\n"
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


@dp.message_handler(commands="cancel", state="*")
@dp.message_handler(Text(equals="cancel", ignore_case=True), state="*")
async def cancel(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends `/cancel` command.
    Resets the state and deletes all the PDF files.
    """
    logging.info("Cancelling operation")

    await reset(message, state)

    await message.reply(
        "Operation cancelled",
        reply_markup=types.ReplyKeyboardRemove()
        )


@dp.message_handler(
    commands=["merge", "compress", "encrypt", "decrypt", "split", "make"],
    state="*"
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
        reply_markup=types.ReplyKeyboardRemove()
        )


@dp.message_handler(commands="convert", state="*")
async def ask_which_convert(message: types.Message, state: FSMContext):
    """
    This handler will be called when user chooses the `convert` operation.
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
        reply_markup=keyboard
    )


@dp.message_handler(Text(equals=["Word to PDF", "Image(s) to PDF"]))
async def start_word_conversion(message: types.Message):
    """
    This handler will be called when user chooses the Word to PDF conversion.
    Asks to send a Word document.
    """
    await operations_dict[message.text]["state"].set()

    await message.answer(
        operations_dict[message.text]["text"],
        reply_markup=types.ReplyKeyboardRemove()
        )


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentType.DOCUMENT,
    state=SplittingStates.waiting_for_files_to_split
    )
async def extract_file_received(message: types.Message):
    """
    This handler will be called when user provides a file to split.
    """
    name = message.document.file_name
    if name.endswith(".pdf"):
        await message.answer("Downloading the file, please wait")

        if " " in name:
            name = name.replace(" ", "_")

        await bot.download_file_by_id(
            message.document.file_id,
            destination=f"{path}/input_pdfs/{message.chat.id}/{name}",
            timeout=90,
            )
        logging.info(f"File (to be extracted) downloaded")

        await message.reply(
            "Great, indicate the pages that you want your new PDF to have.\n\n"
            "<i><b>Examples of Usage:</b></i>\n"
            "<b>3-5</b> ➝ <i>pages 3, 4 and 5</i>\n"
            "<b>7</b> ➝ <i>just the 7th page</i>\n\n"
            "<b>Note:</b> You can also use combinations by just using "
            "<b>a comma and a space</b> like so:\n"
            "<b>3-5, 7</b> ➝ <i>pages 3, 4, 5 and 7</i>"
            )

        await SplittingStates.next()
    else:
        await message.reply(
            "That's not a PDF file.",
            )


@dp.message_handler(state=SplittingStates.waiting_for_pages)
async def extract_pages(message: types.Message, state: FSMContext):
    """
    This handler will be called when user provides the pages that they want
    to extract. Extracts those pages from the PDF, saves it a a separate PDF
    and sends it back to the user.
    """
    logging.info("Extracting pages started")

    await message.answer("I'm on it, please wait")

    files = listdir(f"{path}/input_pdfs/{message.chat.id}")

    input_file = f"{path}/input_pdfs/{message.chat.id}/{files[0]}"
    output_file = f"{path}/output_pdfs/{message.chat.id}/Split_{files[0]}"

    with open(input_file, "rb") as file:
        reader = PdfFileReader(file)
        writer = PdfFileWriter()

        page_count = reader.getNumPages()

        pages = message.text.split(", ")
        pages = [page.split("-") if "-" in page else page for page in pages]

        try:
            # converting all of the numbers to integers type
            pages = [list(map(int, page)) if type(page) == list else int(page) for page in pages]
        except ValueError:
            await SplittingStates.waiting_for_pages.set()
            await message.reply(
                "You typed in the wrong format. Try again.\n\n"
                "<i><b>Examples of Usage:</b></i>\n"
                "<b>3-5</b> ➝ <i>pages 3, 4 and 5</i>\n"
                "<b>7</b> ➝ <i>just the 7th page</i>\n\n"
                "<b>Note:</b> You can also use combinations by just using "
                "<b>a comma and a space</b> like so:\n"
                "<b>3-5, 7</b> ➝ <i>pages 3, 4, 5 and 7</i>"
                )
            return
        else:

            for page in pages:
                if type(page) == list:
                    # user typed in a range
                    start = page[0]
                    end = page[1]

                    # checking for invalid input
                    if start > end:
                        await SplittingStates.waiting_for_pages.set()
                        await message.reply("Invalid pages indicated. Try again.")
                        return
                    elif start <= 0 or end <= 0:
                        await SplittingStates.waiting_for_pages.set()
                        await message.reply(
                            "Only positive page numbers are allowed. Try again."
                            )
                        return
                    elif start > page_count or end > page_count:
                        await SplittingStates.waiting_for_pages.set()
                        await message.reply(
                            "Your PDF doesn't have that many pages. Try again."
                            )
                        return

                    for i in range(start-1, end):
                        writer.addPage(reader.getPage(i))
                else:
                    # user typed in a number

                    # checking for invalid input
                    if page <= 0:
                        await SplittingStates.waiting_for_pages.set()
                        await message.reply(
                            "Only positive page numbers are allowed. Try again."
                            )
                        return
                    elif page > page_count:
                        await SplittingStates.waiting_for_pages.set()
                        await message.reply(
                            "Your PDF doesn't have that many pages. Try again."
                            )
                        return

                    writer.addPage(reader.getPage(page-1))

            with open(output_file, 'wb') as result:
                writer.write(result)

            with open(output_file, 'rb') as result:
                await message.answer_chat_action(action="upload_document")
                await message.reply_document(result, caption="Here you go")

    await reset(message, state)


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentType.DOCUMENT,
    state=[
        CryptingStates.waiting_for_files_to_encrypt,
        CryptingStates.waiting_for_files_to_decrypt,
    ]
)
async def en_de_file_received(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends a file of type `Document`
    (Encrypting/Decrypting)
    """
    current_state = await state.get_state()
    action = current_state.split("_")[-1]

    name = message.document.file_name
    if name.endswith(".pdf"):
        await message.answer("Downloading the file, please wait")

        if " " in name:
            name = name.replace(" ", "_")

        await bot.download_file_by_id(
            message.document.file_id,
            destination=f"{path}/input_pdfs/{message.chat.id}/{name}",
            timeout=90,
            )
        logging.info(f"File (to be {action}ed) downloaded")

        await message.reply(
            f"Great, type the password you want to {action} with.",
            )

        await CryptingStates.next()
    else:
        await message.reply(
            "That's not a PDF file.",
            )


@dp.message_handler(state=CryptingStates.waiting_for_en_password)
async def encrypt_file(message: types.Message, state: FSMContext):
    """
    This handler will be called when user types in a password for encryption.
    Encrypts the file with that password.
    """
    logging.info("Encrypting started")

    await message.answer("Working on it, please wait")

    files = listdir(f"{path}/input_pdfs/{message.chat.id}")

    if files[0].startswith("Decrypted_"):
        new_name = "".join(files[0].split("Decrypted_")[1:])
    else:
        new_name = files[0]

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

    await reset(message, state)


@dp.message_handler(state=CryptingStates.waiting_for_de_password)
async def decrypt_file(message: types.Message, state: FSMContext):
    """
    This handler will be called when user types in a password for encryption.
    Encrypts the file with that password.
    """
    logging.info("Decrypting started")

    await message.answer("Working on it, please wait")

    files = listdir(f"{path}/input_pdfs/{message.chat.id}")

    if files[0].startswith("Encrypted_"):
        new_name = "".join(files[0].split("Encrypted_")[1:])
    else:
        new_name = files[0]

    rename(
        f"{path}/input_pdfs/{message.chat.id}/{files[0]}",
        f"{path}/input_pdfs/{message.chat.id}/{new_name}"
    )

    input_file = f"{path}/input_pdfs/{message.chat.id}/{new_name}"
    output_file = f"{path}/output_pdfs/{message.chat.id}/Decrypted_{new_name}"

    file = open(input_file, "rb")

    input_pdf = PdfFileReader(file)

    password = message.text

    if input_pdf.isEncrypted:
        try:
            response = input_pdf.decrypt(password)
        except NotImplementedError:
            await message.reply(
                "Sorry, your file is encrypted with a method that I am not "
                "familiar with :(\n\nTry decrypting it here:\n"
                "https://smallpdf.com/unlock-pdf \n(not sponsored, just want to help)"
            )
        else:
            if response == 0:
                await message.reply(
                    "Are you sure you typed the password correctly?\n"
                    "Try again."
                )
                await CryptingStates.waiting_for_de_password.set()
                return

            output_pdf = PdfFileWriter()
            output_pdf.appendPagesFromReader(input_pdf)

            with open(output_file, "wb") as result:
                output_pdf.write(result)

            with open(output_file, "rb") as result:
                await message.answer_chat_action(action="upload_document")
                await message.reply_document(result, caption="Here you go")

            await reset(message, state)
        finally:
            file.close()
    else:
        await message.reply("PDF is not encrypted.")


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

        if " " in name:
            name = name.replace(" ", "_")

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

    files = listdir(f"{path}/input_pdfs/{message.chat.id}")

    file = f"{path}/input_pdfs/{message.chat.id}/{files[0]}"

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

    await reset(message, state)


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

        if " " in name:
            name = name.replace(" ", "_")

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
    is_media_group=False,
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

        if " " in name:
            name = name.replace(" ", "_")

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

        if " " in name:
            name = name.replace(" ", "_")

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

    await reset(message, state)


@dp.message_handler(
    is_media_group=True,
    content_types=types.ContentType.DOCUMENT,
    state=ConvertingStates.waiting_for_word_docs
    )
async def convert_word_album(
    message: types.Message,
    album: List[types.Message],
    state: FSMContext
    ):
    """This handler will receive a complete album of any type. (Converting)"""
    await message.answer("Downloading files, please wait")

    for obj in album:
        name = obj.document.file_name

        if name[-4:].lower() != ".doc" and name[-5:].lower() != ".docx" and name[-4:].lower() != ".dot":
            return await message.answer("I can only convert <i>.doc, .docx, .dot</i> formats.")

        if " " in name:
            name = name.replace(" ", "_")

        await bot.download_file_by_id(
            obj.document.file_id,
            destination=f"{path}/input_pdfs/{message.chat.id}/{name}",
            )
        logging.info("File downloaded.")

    await message.answer("Converting in progress, please wait")

    script = (
        "/Applications/LibreOffice.app/Contents/MacOS/soffice --headless "
        f"--convert-to pdf --outdir {path}/output_pdfs/{message.chat.id}/"
    )

    media = types.MediaGroup()

    input_path = f"{path}/input_pdfs/{message.chat.id}"
    for doc in listdir(input_path):
        convert_script = f"{script} {input_path}/{doc}"
        convert_script.split(" ")
        subprocess.run(convert_script, shell=True)

    docs = listdir(f"{path}/output_pdfs/{message.chat.id}")

    for index, file in enumerate(docs):
        if index == len(docs) - 1:
            media.attach_document(
                types.InputFile(f"{path}/output_pdfs/{message.chat.id}/{file}"),
                caption="Here you go"
                )
        else:
            media.attach_document(types.InputFile(f"{path}/output_pdfs/{message.chat.id}/{file}"))

    await message.answer_chat_action(action="upload_document")
    await message.reply_media_group(media=media)

    await reset(message, state)


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentType.DOCUMENT,
    state=ConvertingStates.waiting_for_word_docs
    )
async def convert_word_file(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends a file of type `Document`
    (Converting)
    """
    await message.answer("Downloading file, please wait")

    name = message.document.file_name

    # if name[-4:].lower() != ".doc" and name[-5:].lower() != ".docx" and name[-4:].lower() != ".dot":
    if not name.endswith((".doc", ".docx", ".dot")):
        return await message.answer("I can only convert <i>.doc, .docx, .dot</i> formats.")

    if " " in name:
        name = name.replace(" ", "_")

    await bot.download_file_by_id(
        message.document.file_id,
        destination=f"{path}/input_pdfs/{message.chat.id}/{name}",
        )

    logging.info("File downloaded.")

    await message.answer("Converting in progress, please wait")

    input_path = f"{path}/input_pdfs/{message.chat.id}"

    script = (
        "/Applications/LibreOffice.app/Contents/MacOS/soffice --headless "
        f"--convert-to pdf --outdir {path}/output_pdfs/{message.chat.id}/ "
        f"{input_path}/{name}"
    )

    script.split(" ")
    subprocess.run(script, shell=True)

    output = listdir(f"{path}/output_pdfs/{message.chat.id}")[0]

    with open(f"{path}/output_pdfs/{message.chat.id}/{output}", "rb") as output:
        await message.answer_chat_action(action="upload_document")
        await message.reply_document(output, caption="Here you go")
        logging.info("Sent the document")

    await reset(message, state)


@dp.message_handler(
    is_media_group=True,
    content_types=types.message.ContentTypes.PHOTO,
    state=ConvertingStates.waiting_for_images
)
async def name_pdf_img_album(message: types.Message, album: List[types.Message]):
    """
    This handler will be called when user sends an album of photos to 
    convert to PDF.
    """
    await message.answer("Downloading images, please wait")

    for obj in album:
        file_id = obj.photo[-1].file_id

        img_count = len(listdir(f"{path}/input_pdfs/{message.chat.id}"))

        await bot.download_file_by_id(
            file_id,
            destination=f"{path}/input_pdfs/{message.chat.id}/{img_count}.jpg",
            )
        logging.info("Image downloaded.")

    await ConvertingStates.waiting_for_name.set()

    await message.reply("What should the PDF be called?")


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentTypes.PHOTO,
    state=ConvertingStates.waiting_for_images
)
async def name_pdf_img(message: types.Message):
    """
    This handler will be called when user sends a photo to 
    convert to PDF.
    """
    await message.answer("Downloading image, please wait")

    file_id = message.photo[-1].file_id

    img_count = len(listdir(f"{path}/input_pdfs/{message.chat.id}"))

    await bot.download_file_by_id(
        file_id,
        destination=f"{path}/input_pdfs/{message.chat.id}/{img_count}.jpg",
        )
    logging.info("Image downloaded.")

    await ConvertingStates.waiting_for_name.set()

    await message.reply("What should the PDF be called?")


@dp.message_handler(
    is_media_group=True,
    content_types=types.message.ContentTypes.DOCUMENT,
    state=ConvertingStates.waiting_for_images
)
async def name_pdf_img_album(message: types.Message, album: List[types.Message]):
    """
    This handler will be called when user sends an album of photos (as files) 
    to convert to PDF.
    """
    await message.answer("Downloading images, please wait")

    for obj in album:
        name = obj.document.file_name

        if not name.endswith((".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".eps", ".bmp")):
            return await message.answer("Sorry, I cannot convert from this image format.")

        img_count = len(listdir(f"{path}/input_pdfs/{message.chat.id}"))

        await bot.download_file_by_id(
            obj.document.file_id,
            destination=f"{path}/input_pdfs/{message.chat.id}/{img_count}_{name}",
            )
        logging.info("Image downloaded.")

    await ConvertingStates.waiting_for_name.set()

    await message.reply("What should the PDF be called?")


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentTypes.DOCUMENT,
    state=ConvertingStates.waiting_for_images
)
async def name_pdf_img(message: types.Message):
    """
    This handler will be called when user sends a photo (as a file) to 
    convert to PDF.
    """
    await message.answer("Downloading image, please wait")

    name = message.document.file_name

    if not name.endswith((".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".eps", ".bmp")):
        return await message.answer("Sorry, I cannot convert from this image format.")

    img_count = len(listdir(f"{path}/input_pdfs/{message.chat.id}"))

    await bot.download_file_by_id(
        message.document.file_id,
        destination=f"{path}/input_pdfs/{message.chat.id}/{img_count}_{name}",
        )
    logging.info("Image downloaded.")

    await ConvertingStates.waiting_for_name.set()

    await message.reply("What should the PDF be called?")


@dp.message_handler(state=ConvertingStates.waiting_for_name)
async def convert_images(message: types.Message, state: FSMContext):
    """
    This handler will be called once user provides a name for the output PDF.
    (Converting Images)
    """
    await message.answer("Converting in progress, please wait")

    output_name = message.text

    if " " in output_name:
        output_name = output_name.replace(" ", "_")

    if message.text[-4:].lower() != ".pdf":
        output_name = output_name + ".pdf"

    output_path = f"{path}/output_pdfs/{message.chat.id}/{output_name}"
    img_path = f"{path}/input_pdfs/{message.chat.id}"

    imgs = [img_path + "/" + name for name in sorted(listdir(img_path))]

    for index, img in enumerate(sorted(listdir(img_path))):
        if img.endswith(".png"):
            png = Image.open(f"{img_path}/{img}").convert("RGBA")
            background = Image.new("RGBA", png.size, (255,255,255))

            alpha_composite = Image.alpha_composite(background, png)
            alpha_composite.convert("RGB").save(f"{img_path}/{index}.jpg", "JPEG", quality=80)

    imgs = [img_path + "/" + name for name in sorted(listdir(img_path)) if not name.endswith(".png")]

    logging.info("Converting images started")
    
    try:
        with open(output_path, "wb") as result:
            result.write(img2pdf.convert(imgs))
    except:
        return await message.reply("Sorry, the conversion failed.")

    with open(output_path, "rb") as result:
        await message.answer_chat_action(action="upload_document")
        await message.reply_document(result, caption="Here you go")
        logging.info("Sent the document")

    await reset(message, state)


@dp.message_handler(
    is_media_group=True,
    content_types=types.message.ContentType.DOCUMENT,
    state=[
        MergingStates.waiting_for_specific_file,
        CompressingStates.waiting_for_files_to_compress,
        CryptingStates.waiting_for_files_to_encrypt,
        CryptingStates.waiting_for_files_to_decrypt,
        SplittingStates.waiting_for_files_to_split,
        ]
    )
async def inform_limitations(message: types.Message):
    await message.reply(
        "I cannot handle multiple files at the same time.\n"
        "Please send a single file."
        )


@dp.message_handler(regexp=("pdf"), state=None)
async def vivy_torreto(message: types.Message):
    await message.reply("https://ibb.co/9yCkBc1")


@dp.message_handler(regexp=("sing"), state=None)
async def vivy_sing(message: types.Message):
    await message.reply("https://youtu.be/2p8ig-TrYPY")


@dp.message_handler(
    state=None,
    content_types=types.message.ContentType.ANY)
async def send_instructions(message: types.Message):
    await message.reply("Please choose a command or type /help for instructions.")
