"""
The part that deals with converting Word to PDF and images to PDF.
"""

import logging
import subprocess
from os import listdir
from typing import List

import img2pdf
from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import bot, dp, input_path, output_path
from PIL import Image
from states.all_states import ConvertingStates
from utils.clean_up import reset


@dp.message_handler(
    is_media_group=True,
    content_types=types.ContentType.DOCUMENT,
    state=ConvertingStates.waiting_for_word_docs,
)
async def convert_word_album(
    message: types.Message, album: List[types.Message], state: FSMContext
):
    """
    This handler will be called when user sends Word documents to convert to
    PDF as an album. Checks the file format, converts all the files and
    sends them back to the user as an album.
    """
    await message.answer("Downloading files, please wait")

    for obj in album:
        name = obj.document.file_name

        if not name.endswith((".doc", ".docx", ".dot")):
            return await message.answer(
                "I can only convert <i>.doc, .docx, .dot</i> formats."
            )

        # replacing empty spaces in the file name with underscores
        # if there are spaces in the file name, some of the code does not work
        # there definitely should be a better way of doing this, but i'm dumb
        if " " in name:
            name = name.replace(" ", "_")

        await bot.download_file_by_id(
            obj.document.file_id,
            destination=f"{input_path}/{message.chat.id}/{name}",
        )
        logging.info("File downloaded.")

    await message.answer("Converting in progress, please wait")

    # LibreOffice is used to convert the Word documents to PDF
    script = (
        "libreoffice --headless "
        f"--convert-to pdf --outdir {output_path}/{message.chat.id}/"
    )

    # the output PDFs will be sent also as a group of files
    media = types.MediaGroup()

    in_path = f"{input_path}/{message.chat.id}"
    for doc in listdir(in_path):
        convert_script = f"{script} {in_path}/{doc}"
        convert_script.split(" ")
        subprocess.run(convert_script, shell=True)

    docs = listdir(f"{output_path}/{message.chat.id}")

    for index, file in enumerate(docs):
        # the last word document in the group of files should have the caption
        if index == len(docs) - 1:
            media.attach_document(
                types.InputFile(f"{output_path}/{message.chat.id}/{file}"),
                caption="Here you go",
            )
        else:
            media.attach_document(
                types.InputFile(f"{output_path}/{message.chat.id}/{file}")
            )

    await message.answer_chat_action(action="upload_document")
    await message.reply_media_group(media=media)

    await reset(message, state)


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentType.DOCUMENT,
    state=ConvertingStates.waiting_for_word_docs,
)
async def convert_word_file(message: types.Message, state: FSMContext):
    """
    This handler will be called when user provided a Word document to convert
    to PDF. It's mostly the same as the previous function with some slight
    differences.
    """
    await message.answer("Downloading file, please wait")

    name = message.document.file_name

    if not name.endswith((".doc", ".docx", ".dot")):
        return await message.answer(
            "I can only convert <i>.doc, .docx, .dot</i> formats."
        )

    # replacing empty spaces in the file name with underscores
    # if there are spaces in the file name, some of the code does not work
    # there definitely should be a better way of doing this, but i'm dumb
    if " " in name:
        name = name.replace(" ", "_")

    await bot.download_file_by_id(
        message.document.file_id,
        destination=f"{input_path}/{message.chat.id}/{name}",
    )

    logging.info("File downloaded.")

    await message.answer("Converting in progress, please wait")

    in_path = f"{input_path}/{message.chat.id}"

    # LibreOffice is used to convert the Word documents to PDF
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
    state=ConvertingStates.waiting_for_images,
)
async def name_pdf_img_album(message: types.Message, album: List[types.Message]):
    """
    This handler will be called when user sends an album of photos to
    convert to PDF. Downloads the photos and asks to name the output PDF.
    """
    await message.answer("Downloading images, please wait")

    for obj in album:
        file_id = obj.photo[-1].file_id

        # since we cannot obtain the file name of a photo which was sent
        # as part of an album, we will be using the image count to name
        # each file.
        img_count = len(listdir(f"{input_path}/{message.chat.id}"))

        # all the files are saved as jpg since the photo names cannot be
        # obtained. i could not come up with anything else cause im retarded.
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
    state=ConvertingStates.waiting_for_images,
)
async def name_pdf_img(message: types.Message):
    """
    This handler will be called when user sends a single photo to
    convert to PDF.
    """
    await message.answer("Downloading image, please wait")

    file_id = message.photo[-1].file_id

    # since we cannot obtain the file name of a photo which was sent
    # as part of an album, we will be using the image count to name
    # each file.
    img_count = len(listdir(f"{input_path}/{message.chat.id}"))

    # all the files are saved as jpg since the photo names cannot be
    # obtained. i could not come up with anything else cause im retarded.
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
    state=ConvertingStates.waiting_for_images,
)
async def name_pdf_img_album(message: types.Message, album: List[types.Message]):
    """
    This handler will be called when user sends an album of photos (as files)
    to convert to PDF. Downloads the files, checks if they're images and
    asks to name the output PDF.
    """
    await message.answer("Downloading images, please wait")

    for obj in album:
        name = obj.document.file_name

        if not name.endswith(
            (".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".eps", ".bmp")
        ):
            return await message.answer(
                "Sorry, I cannot convert from this image format."
            )

        # here this variable is used to keep track of the order in which
        # images are sent
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
    state=ConvertingStates.waiting_for_images,
)
async def name_pdf_img(message: types.Message):
    """
    This handler will be called when user sends a single photo (as a file) to
    convert to PDF.
    """
    await message.answer("Downloading image, please wait")

    name = message.document.file_name

    if not name.endswith(
        (".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".eps", ".bmp")
    ):
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

    # replacing empty spaces in the file name with underscores
    # if there are spaces in the file name, some of the code does not work
    # there definitely should be a better way of doing this, but i'm dumb
    if " " in output_name:
        output_name = output_name.replace(" ", "_")

    if not message.text.lower().endswith(".pdf"):
        output_name = output_name + ".pdf"

    out_path = f"{output_path}/{message.chat.id}/{output_name}"
    img_path = f"{input_path}/{message.chat.id}"

    imgs = [img_path + "/" + name for name in sorted(listdir(img_path))]

    for index, img in enumerate(sorted(listdir(img_path))):
        # removing the alpha channel
        if img.endswith(".png"):
            png = Image.open(f"{img_path}/{img}").convert("RGBA")
            background = Image.new("RGBA", png.size, (255, 255, 255))

            alpha_composite = Image.alpha_composite(background, png)
            alpha_composite.convert("RGB").save(
                f"{img_path}/{index}.jpg", "JPEG", quality=80
            )

    imgs = [
        img_path + "/" + name
        for name in sorted(listdir(img_path))
        if not name.endswith(".png")
    ]

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
