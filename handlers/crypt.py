"""
The part that deals with encryption and decryption of PDF files.
"""

import logging
from os import listdir, rename

from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import bot, dp, input_path, output_path
from PyPDF2 import PdfFileReader, PdfFileWriter
from states.all_states import CryptingStates
from utils.clean_up import reset


@dp.message_handler(
    is_media_group=False,
    content_types=types.message.ContentType.DOCUMENT,
    state=[
        CryptingStates.waiting_for_files_to_encrypt,
        CryptingStates.waiting_for_files_to_decrypt,
    ],
)
async def crypt_file_received(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends a file of type `Document`
    (Encrypting/Decrypting)
    Checks if the file is a PDF and asks to input a password.
    """
    # to make this function work for both encrypting and decrypting,
    # the action is obtained through the state name
    # (the action is the last word in the state name)
    current_state = await state.get_state()
    action = current_state.split("_")[-1]

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
        logging.info(f"File (to be {action}ed) downloaded")

        await message.reply(
            f"Great, type the password you want to {action} with.",
        )

        # the next state is waiting for a password
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

    files = listdir(f"{input_path}/{message.chat.id}")

    # if the file name for some reason has the prefix "Decrypted_",
    # drop the prefix
    if files[0].startswith("Decrypted_"):
        file_name = "".join(files[0].split("Decrypted_")[1:])

        rename(
            f"{input_path}/{message.chat.id}/{files[0]}",
            f"{input_path}/{message.chat.id}/{file_name}",
        )
    else:
        file_name = files[0]

    input_file = f"{input_path}/{message.chat.id}/{file_name}"
    output_file = f"{output_path}/{message.chat.id}/Encrypted_{file_name}"

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

    files = listdir(f"{input_path}/{message.chat.id}")

    if files[0].startswith("Encrypted_"):
        file_name = "".join(files[0].split("Encrypted_")[1:])

        rename(
            f"{input_path}/{message.chat.id}/{files[0]}",
            f"{input_path}/{message.chat.id}/{file_name}",
        )
    else:
        file_name = files[0]

    input_file = f"{input_path}/{message.chat.id}/{file_name}"
    output_file = f"{output_path}/{message.chat.id}/Decrypted_{file_name}"

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
                "https://smallpdf.com/unlock-pdf \n"
                "(not sponsored, just want to help)"
            )
        else:
            if response == 0:
                await message.reply(
                    "Are you sure you typed the password correctly?\nTry again."
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
