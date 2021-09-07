from states.files_state import FilesState
from aiogram import types

from loader import dp, bot
from loader import path

import logging
from os import listdir, rename, unlink

@dp.callback_query_handler(text="ask_for_name")
async def ask_for_name(call: types.CallbackQuery):
    """
    This handler will ask the user to provide a name for the output file.
    """
    await FilesState.waiting_for_a_name.set()

    await bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup="",
    )

    await call.message.answer("What should the merged file be called?")

    await call.answer()


@dp.callback_query_handler(text="modify_files")
async def modification_options(call: types.CallbackQuery):
    """
    This handler will provide the user some options.
    (change around the order of the files, delete some of them, insert new files, etc)
    """
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton(
            text="No, I want to rearrange the order of the files",
            callback_data="rearrange"
            ),
        types.InlineKeyboardButton(
            text="No, I want to delete some file(s)",
            callback_data="delete_files"
            ),
        types.InlineKeyboardButton(
            text="No, I want to add another file(s)",
            callback_data="add_files"
        ),
        types.InlineKeyboardButton(
            text="No, I changed my mind. I want to cancel merging.",
            callback_data="no_cancel"
        )
    ]

    keyboard.add(*buttons)

    await call.message.edit_text(
        "<b><u>Choose one of the options below</u></b>\n\n" +
        call.message.text[call.message.text.index("1."):],
        reply_markup=keyboard,
    )

    await call.answer()


@dp.callback_query_handler(text="rearrange")
async def choose_file(call: types.CallbackQuery):
    """
    This handler will be called when user indicates that they want to
    rearrange the order of the files.
    """
    files = sorted(listdir(f"{path}/input_pdfs/{call.message.chat.id}"))

    keyboard = types.InlineKeyboardMarkup()
    
    for file in files:
        keyboard.add(types.InlineKeyboardButton(
            text=file[3:],
            callback_data="file_" + file
        ))

    await call.message.edit_text(
        "<b><u>Choose the file that you want to move</u></b>\n\n" + 
        call.message.text[call.message.text.index("1."):],
        reply_markup=keyboard,
    )

    await call.answer()


@dp.callback_query_handler(text_startswith="file_")
async def choose_position(call: types.CallbackQuery):
    """
    This handler will be called once the user chooses the file to move.
    """
    files_num = len(listdir(f"{path}/input_pdfs/{call.message.chat.id}"))

    keyboard = types.InlineKeyboardMarkup()

    buttons = []

    for i in range(1, files_num+1):
        buttons.append(
            types.InlineKeyboardButton(
                text=str(i), callback_data=f"pos_{i}",
            )
        )

    keyboard.add(*buttons)

    file_name = call.data[5:]

    rename(
        f"{path}/input_pdfs/{call.message.chat.id}/{file_name}",
        f"{path}/input_pdfs/{call.message.chat.id}/id_{file_name}"
        )

    await call.message.edit_text(
        "<b><u>Choose where you want to move it</u></b>\n\n" +
        call.message.text[call.message.text.index("1."):],
        reply_markup=keyboard,
    )

    await call.answer()


@dp.callback_query_handler(text_startswith="pos_")
async def rearrange(call: types.CallbackQuery):
    """
    This handler will be called once the user chooses the position to move the file.
    """
    files = sorted(listdir(f"{path}/input_pdfs/{call.message.chat.id}"))

    for file in files:
        if file.startswith("id_"):
            chosen_file = file
            from_position = int(file[3:5])
            break

    to_position = int(call.data[4:])

    if from_position == to_position:
        rename(
            f"{path}/input_pdfs/{call.message.chat.id}/{chosen_file}",
            f"{path}/input_pdfs/{call.message.chat.id}/{chosen_file[3:]}"
        )

        await call.message.answer(
            "I don't see any point in doing that.\n"
            "But hey, since that's what you want to do..."
            )
    elif from_position > to_position:
        for file in files[to_position-1:from_position-1]:
            file_num = int(file[:2]) + 1

            file_num = f"0{file_num}" if file_num < 10 else str(file_num)
            rename(
                f"{path}/input_pdfs/{call.message.chat.id}/{file}",
                f"{path}/input_pdfs/{call.message.chat.id}/{file_num}{file[2:]}"
            )

        position = f"0{to_position}" if to_position < 10 else str(to_position)
        rename(
            f"{path}/input_pdfs/{call.message.chat.id}/{chosen_file}",
            f"{path}/input_pdfs/{call.message.chat.id}/{position}{chosen_file[5:]}"
        )
    else:
        for file in files[from_position-1:to_position-1]:
            file_num = int(file[:2]) - 1

            file_num = f"0{file_num}" if file_num < 10 else str(file_num)
            rename(
                f"{path}/input_pdfs/{call.message.chat.id}/{file}",
                f"{path}/input_pdfs/{call.message.chat.id}/{file_num}{file[2:]}"
            )

        position = f"0{to_position}" if to_position < 10 else str(to_position)
        rename(
            f"{path}/input_pdfs/{call.message.chat.id}/{chosen_file}",
            f"{path}/input_pdfs/{call.message.chat.id}/{position}{chosen_file[5:]}"
        )

    files = sorted(listdir(f"{path}/input_pdfs/{call.message.chat.id}"))

    file_list = [f"{index}. {value[3:]}" for index, value in enumerate(files, start=1)]
    file_list = "\n".join(file_list)

    keyboard = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(text="Yes", callback_data="ask_for_name"),
        types.InlineKeyboardButton(text="No", callback_data="modify_files"),
    ]
    keyboard.add(*buttons)

    await call.message.edit_text(
        f"<b><u>Are these the files that you want to merge?</u></b>\n\n{file_list}",
        reply_markup=keyboard,
        )

    await call.answer()
