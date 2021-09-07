from PyPDF2.merger import PdfFileMerger
from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import dp, path, bot

from states.files_state import FilesState

from typing import List
import logging
from os import mkdir, listdir, unlink

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
        "merging their PDF files into one.\n"
        "Type /help for more information."
    )


@dp.message_handler(commands="help", state="*")
async def give_help(message: types.Message):
    """
    This handler will be called when user sends '/help' command
    """
    await message.reply(
        "<b>Instructions:</b>\n\nTo merge your PDF files, send them to me "
        "and send <i>/done</i>\nThat's it.\n\n<b>Available commands:</b>\n\n"
        "<i>/start</i> - Brief info about the bot.\n"
        "<i>/done</i> - I will start my mission and send you the merged file "
        "when it's ready. <u>Send this command only once you have sent all "
        "the PDFs you want to merge.</u>\n"
        "<i>/cancel</i> - This will cancel merging files that you sent.\n"
        "<i>/help</i> - Help on how to use the bot.\n"
    )


@dp.message_handler(commands="done")
async def get_confirmation(message: types.Message):
    """
    This handler will be called when user sends `/done` command.
    Gets confirmation on the files that need to be merged.
    """
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
    This handler will be called when user sends `/cancel` command
    """
    logging.info("Cancelling merging")

    await state.finish()

    files = listdir(f'{path}/input_pdfs/{message.chat.id}')

    if files:
        for file in files:
            unlink(f"{path}/input_pdfs/{message.chat.id}/{file}")
            logging.info(f"Deleted input PDF")

    await message.reply("Merging cancelled.")


@dp.message_handler(is_media_group=True, content_types=types.ContentType.DOCUMENT, state=None)
async def handle_albums(message: types.Message, album: List[types.Message]):
    """This handler will receive a complete album of any type."""
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


@dp.message_handler(content_types=types.message.ContentType.DOCUMENT, state=None)
async def file_received(message: types.Message):
    """
    This handler will be called when user sends a file of type `Document`
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
    state=FilesState.waiting_for_specific_file
    )
async def specific_file_received(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends a file of type `Document`
    that has to be added to a certain position in the list of files.
    """
    name = message.document.file_name
    if name.endswith(".pdf"):
        file_count = await state.get_data()
        print(file_count)
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


@dp.message_handler(state=FilesState.waiting_for_a_name)
async def name_file(message: types.Message, state: FSMContext):
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
    state=FilesState.waiting_for_specific_file
    )
async def inform_limitations(message: types.Message):
    await message.reply(
        "I cannot add multiple files at the same time.\n"
        "Please send a single file."
        )


@dp.message_handler(state=None)
async def send_instructions(message: types.Message):
    await message.reply("Type /help to see more information.")
