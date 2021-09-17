import logging
import subprocess
from os import listdir, mkdir
from os.path import getsize
from typing import List

import img2pdf
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from loader import bot, dp, input_path, output_path
from PIL import Image
from PyPDF2 import PdfFileMerger
from states.all_states import *
from utils.clean_up import reset
from utils.convert_file_size import convert_bytes

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

    files = listdir(f"{input_path}/{message.chat.id}")

    file = f"{input_path}/{message.chat.id}/{files[0]}"

    logging.info("Compressing started")

    await message.answer("Compressing the file, please wait")

    if " " in output_name:
        compressed_name = output_name.replace(" ", "_")
    else:
        compressed_name = output_name

    if message.text[-4:].lower() == ".pdf":
        compressed_pdf = f"{output_path}/{message.chat.id}/{compressed_name}"
    else:
        compressed_pdf = f"{output_path}/{message.chat.id}/{compressed_name}.pdf"

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

    files = sorted(listdir(f"{input_path}/{message.chat.id}"))

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
        
        file_count = len(listdir(f'{input_path}/{message.chat.id}')) + 1

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

        file_count = len(listdir(f'{input_path}/{message.chat.id}')) + 1

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
            destination=f"{input_path}/{message.chat.id}/{file_count}_{name}",
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

    files = sorted(listdir(f"{input_path}/{message.chat.id}"))

    logging.info("Merging started")

    merger = PdfFileMerger(strict=False)

    for file in files:
        merger.append(f"{input_path}/{message.chat.id}/{file}")

    merged_pdf_name = message.text.replace(" ", "_")

    if message.text[-4:].lower() != ".pdf":
        merged_pdf_name = merged_pdf_name + ".pdf"

    merger.write(f"{output_path}/{message.chat.id}/{merged_pdf_name}")
    merger.close()

    with open(f"{output_path}/{message.chat.id}/{merged_pdf_name}", "rb") as result:
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

        if not name.endswith((".doc", ".docx", ".dot")):
            return await message.answer("I can only convert <i>.doc, .docx, .dot</i> formats.")

        if " " in name:
            name = name.replace(" ", "_")

        await bot.download_file_by_id(
            obj.document.file_id,
            destination=f"{input_path}/{message.chat.id}/{name}",
            )
        logging.info("File downloaded.")

    await message.answer("Converting in progress, please wait")

    script = (
        "/Applications/LibreOffice.app/Contents/MacOS/soffice --headless "
        f"--convert-to pdf --outdir {output_path}/{message.chat.id}/"
    )

    media = types.MediaGroup()

    in_path = f"{input_path}/{message.chat.id}"
    for doc in listdir(in_path):
        convert_script = f"{script} {in_path}/{doc}"
        convert_script.split(" ")
        subprocess.run(convert_script, shell=True)

    docs = listdir(f"{output_path}/{message.chat.id}")

    for index, file in enumerate(docs):
        if index == len(docs) - 1:
            media.attach_document(
                types.InputFile(f"{output_path}/{message.chat.id}/{file}"),
                caption="Here you go"
                )
        else:
            media.attach_document(types.InputFile(f"{output_path}/{message.chat.id}/{file}"))

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

    if not name.endswith((".doc", ".docx", ".dot")):
        return await message.answer("I can only convert <i>.doc, .docx, .dot</i> formats.")

    if " " in name:
        name = name.replace(" ", "_")

    await bot.download_file_by_id(
        message.document.file_id,
        destination=f"{input_path}/{message.chat.id}/{name}",
        )

    logging.info("File downloaded.")

    await message.answer("Converting in progress, please wait")

    in_path = f"{input_path}/{message.chat.id}"

    script = (
        "/Applications/LibreOffice.app/Contents/MacOS/soffice --headless "
        f"--convert-to pdf --outdir {output_path}/{message.chat.id}/ "
        f"{in_path}/{name}"
    )

    script.split(" ")
    subprocess.run(script, shell=True)

    output = listdir(f"{output_path}/{message.chat.id}")[0]

    with open(f"{output_path}/{message.chat.id}/{output}", "rb") as output:
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

        img_count = len(listdir(f"{input_path}/{message.chat.id}"))

        await bot.download_file_by_id(
            file_id,
            destination=f"{input_path}/{message.chat.id}/{img_count}.jpg",
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

    img_count = len(listdir(f"{input_path}/{message.chat.id}"))

    await bot.download_file_by_id(
        file_id,
        destination=f"{input_path}/{message.chat.id}/{img_count}.jpg",
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

        img_count = len(listdir(f"{input_path}/{message.chat.id}"))

        await bot.download_file_by_id(
            obj.document.file_id,
            destination=f"{input_path}/{message.chat.id}/{img_count}_{name}",
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

    img_count = len(listdir(f"{input_path}/{message.chat.id}"))

    await bot.download_file_by_id(
        message.document.file_id,
        destination=f"{input_path}/{message.chat.id}/{img_count}_{name}",
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

    out_path = f"{output_path}/{message.chat.id}/{output_name}"
    img_path = f"{input_path}/{message.chat.id}"

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
        with open(out_path, "wb") as result:
            result.write(img2pdf.convert(imgs))
    except:
        return await message.reply("Sorry, the conversion failed.")

    with open(out_path, "rb") as result:
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
