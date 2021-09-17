"""
The part that deals with splitting PDF files.
(Extracting specific pages from a PDF and saving them to a separate file)
"""

import logging
from os import listdir

from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import bot, dp, input_path, output_path
from PyPDF2 import PdfFileReader, PdfFileWriter
from states.all_states import SplittingStates
from utils.clean_up import reset


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentType.DOCUMENT,
    state=SplittingStates.waiting_for_files_to_split,
)
async def extract_file_received(message: types.Message):
    """
    This handler will be called when user provides a file to split.
    Checks if a file is a PDF and asks to input the desired pages
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

        # the next state is waiting for desired pages
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

    files = listdir(f"{input_path}/{message.chat.id}")

    input_file = f"{input_path}/{message.chat.id}/{files[0]}"
    output_file = f"{output_path}/{message.chat.id}/Split_{files[0]}"

    with open(input_file, "rb") as file:
        reader = PdfFileReader(file)
        writer = PdfFileWriter()

        page_count = reader.getNumPages()

        # since we ask the users to provide the desired pages in a format like:
        # 3-5, 7, 10-11 (pages 3, 4, 5, 7, 10 and 11)
        # first we split on the comma and space to get ["3-5", "7", "10-11"]
        pages = message.text.split(", ")
        # then we split on the dash if it's there, to get:
        # [["3", "5"], "7", ["10", "11"]]
        pages = [page.split("-") if "-" in page else page for page in pages]

        try:
            # converting all of the numbers to integers type
            pages = [
                list(map(int, page)) if type(page) == list else int(page)
                for page in pages
            ]
        except ValueError:
            # await SplittingStates.waiting_for_pages.set()
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

        for page in pages:
            # user typed in a range
            if type(page) == list:
                start = page[0]
                end = page[1]

                # checking for invalid input
                if start > end:
                    await message.reply("Invalid pages indicated. Try again.")
                    return
                elif start == 0 or end == 0:
                    await message.reply("Zero is not a valid page number. Try again.")
                    return
                elif start > page_count or end > page_count:
                    await message.reply(
                        "Your PDF doesn't have that many pages. Try again."
                    )
                    return

                # page numbers start from zero in pypdf2, so we subtract 1
                for i in range(start - 1, end):
                    writer.addPage(reader.getPage(i))
            # user typed in a number
            else:
                # checking for invalid input
                if page == 0:
                    await message.reply("Zero is not a valid page number. Try again.")
                    return
                elif page > page_count:
                    await message.reply(
                        "Your PDF doesn't have that many pages. Try again."
                    )
                    return

                # page numbers start from zero in pypdf2, so we subtract 1
                writer.addPage(reader.getPage(page - 1))

        with open(output_file, "wb") as result:
            writer.write(result)

        with open(output_file, "rb") as result:
            await message.answer_chat_action(action="upload_document")
            await message.reply_document(result, caption="Here you go")

    await reset(message, state)
