"""
The part that deals with merging PDF files into one.
(callback query handlers)
"""

import logging
from os import listdir, rename, unlink

from aiogram import types
from aiogram.dispatcher import FSMContext
from loader import bot, dp, input_path
from states.all_states import MergingStates


@dp.callback_query_handler(text="ask_for_name")
async def ask_for_name(call: types.CallbackQuery):
    """
    This handler wll be called when the user confirms the files that
    need to be merged.
    Will ask the user to provide a name for the output file.
    """
    await MergingStates.waiting_for_a_name.set()

    # delete the inline keyboard (the one that has Yes and No)
    await call.message.delete_reply_markup()

    await call.message.answer("What should the merged file be called?")

    await call.answer()


@dp.callback_query_handler(text="modify_files")
async def modification_options(call: types.CallbackQuery):
    """
    This handler will provide the user some options to choose from if they
    are not happy with the file list. Options include:

    1. change around the order of the files
    2. delete a file from the list
    3. insert a new file to some position in the list
    4. cancel merging altogether
    """
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton(
            text="No, I want to rearrange the order of the files",
            callback_data="move_file",
        ),
        types.InlineKeyboardButton(
            text="No, I want to delete a file", callback_data="delete_file"
        ),
        types.InlineKeyboardButton(
            text="No, I want to add another file", callback_data="add"
        ),
        types.InlineKeyboardButton(
            text="No, I changed my mind. I want to cancel merging.",
            callback_data="no_cancel",
        ),
    ]

    keyboard.add(*buttons)

    await call.message.edit_text(
        "<b><u>Choose one of the options below</u></b>\n\n"
        + call.message.text[call.message.text.index("1.") :],
        reply_markup=keyboard,
    )

    await call.answer()


@dp.callback_query_handler(text_endswith="_file")
async def choose_file(call: types.CallbackQuery):
    """
    This handler will be called when user indicates that they want to either:
    1. Rearrange the order of the files
    2. Delete a file from the list of files

    Asks the user to choose a file that they want to modify.
    """
    action = call.data.split("_")[0]

    # this will be used to specify the callback_data for the buttons
    prefix = "mv_" if action == "move" else "rm_"

    # sorted is called since the file names have corresponding file counts
    # this is done to maintain the order of the files
    # (the files will be merged in the order that the user sends the files in)
    files = sorted(listdir(f"{input_path}/{call.message.chat.id}"))

    keyboard = types.InlineKeyboardMarkup()

    for file in files:
        keyboard.add(
            types.InlineKeyboardButton(text=file[3:], callback_data=prefix + file)
        )

    await call.message.edit_text(
        f"<b><u>Choose the file that you want to {action}</u></b>\n\n"
        + call.message.text[call.message.text.index("1.") :],
        reply_markup=keyboard,
    )

    await call.answer()


@dp.callback_query_handler(text_startswith="mv_")
async def choose_position(call: types.CallbackQuery):
    """
    This handler will be called once the user chooses the file to move.
    """
    files_num = len(listdir(f"{input_path}/{call.message.chat.id}"))

    keyboard = types.InlineKeyboardMarkup()

    buttons = []

    for i in range(1, files_num + 1):
        buttons.append(
            types.InlineKeyboardButton(
                text=str(i),
                callback_data=f"pos_{i}",
            )
        )

    keyboard.add(*buttons)

    # because the call.data contains the "mv_" + the file name,
    # the file name starts from the third index location
    file_name = call.data[3:]

    # rename that chosen file so that it has the prefix "id_"
    # this is done so that we can later differentiate this file from others
    rename(
        f"{input_path}/{call.message.chat.id}/{file_name}",
        f"{input_path}/{call.message.chat.id}/id_{file_name}",
    )

    await call.message.edit_text(
        "<b><u>Choose where you want to move it</u></b>\n\n"
        + call.message.text[call.message.text.index("1.") :],
        reply_markup=keyboard,
    )

    await call.answer()


@dp.callback_query_handler(text_startswith="pos_")
async def rearrange(call: types.CallbackQuery):
    """
    This handler will be called once the user chooses the position to move
    the file. Moves the file to that position in the list.
    Gets the confirmation on the file list.
    """
    logging.info("Rearranging in progress")

    # sorted is called since the file names have corresponding file counts
    # this is done to maintain the order of the files
    # (the files will be merged in the order that the user sends the files in)
    files = sorted(listdir(f"{input_path}/{call.message.chat.id}"))

    for file in files:
        if file.startswith("id_"):
            chosen_file = file
            # the chosen file at this point should have a name like:
            # id_03_coolname.pdf
            # so the original position of where that file lied is 03
            from_position = int(file[3:5])
            break

    # getting the position by slicing out and removing the "pos_"
    to_position = int(call.data[4:])

    # example: user chose to move file at position 03 to position 03
    if from_position == to_position:
        rename(
            f"{input_path}/{call.message.chat.id}/{chosen_file}",
            f"{input_path}/{call.message.chat.id}/{chosen_file[3:]}",
        )

        await call.message.answer(
            "I don't see any point in doing that.\n"
            "But hey, since that's what you want to do..."
        )
    # example: user chose to move file at position at 5 to position 2
    elif from_position > to_position:
        for file in files[to_position - 1 : from_position - 1]:
            file_num = int(file[:2]) + 1

            file_num = f"0{file_num}" if file_num < 10 else str(file_num)
            rename(
                f"{input_path}/{call.message.chat.id}/{file}",
                f"{input_path}/{call.message.chat.id}/{file_num}{file[2:]}",
            )

        position = f"0{to_position}" if to_position < 10 else str(to_position)
        rename(
            f"{input_path}/{call.message.chat.id}/{chosen_file}",
            f"{input_path}/{call.message.chat.id}/{position}{chosen_file[5:]}",
        )
    # example: user chose to move file at position 2 to position 5
    else:
        for file in files[from_position - 1 : to_position - 1]:
            file_num = int(file[:2]) - 1

            file_num = f"0{file_num}" if file_num < 10 else str(file_num)
            rename(
                f"{input_path}/{call.message.chat.id}/{file}",
                f"{input_path}/{call.message.chat.id}/{file_num}{file[2:]}",
            )

        position = f"0{to_position}" if to_position < 10 else str(to_position)
        rename(
            f"{input_path}/{call.message.chat.id}/{chosen_file}",
            f"{input_path}/{call.message.chat.id}/{position}{chosen_file[5:]}",
        )

    # once the arrangement is over, get the confirmation again
    files = sorted(listdir(f"{input_path}/{call.message.chat.id}"))

    file_list = [f"{index}. {value[3:]}" for index, value in enumerate(files, start=1)]
    file_list = "\n".join(file_list)

    keyboard = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(text="Yes", callback_data="ask_for_name"),
        types.InlineKeyboardButton(text="No", callback_data="modify_files"),
    ]
    keyboard.add(*buttons)

    await call.message.edit_text(
        ("<b><u>Are these the files that you want to merge?</u></b>\n\n" + file_list),
        reply_markup=keyboard,
    )

    await call.answer()


@dp.callback_query_handler(text_startswith="rm_")
async def delete_file(call: types.CallbackQuery):
    """
    This handler will be called once user chooses the file they want to delete
    from the list of files. Deletes that file from the list and gets
    confirmation on the file list.
    """
    # sorted is called since the file names have corresponding file counts
    # this is done to maintain the order of the files
    # (the files will be merged in the order that the user sends the files in)
    files = sorted(listdir(f"{input_path}/{call.message.chat.id}"))

    if len(files) == 1:
        await call.message.answer(
            "Can't let you do that. There will be nothing left for me to work with."
        )
    else:
        # the call.data should look like "rm_" + file name
        # so the file name starts right after rm_ (at 3rd index location)
        file_name = call.data[3:]

        unlink(f"{input_path}/{call.message.chat.id}/{file_name}")
        logging.info("Removed a specific PDF")

        # once that file is deleted, we fix up the file counts
        del_file_num = int(file_name[:2])

        if del_file_num < len(files):
            for file in files[del_file_num:]:
                file_num = int(file[:2]) - 1

                file_num = f"0{file_num}" if file_num < 10 else str(file_num)
                rename(
                    f"{input_path}/{call.message.chat.id}/{file}",
                    f"{input_path}/{call.message.chat.id}/{file_num}{file[2:]}",
                )

    # once the deletion is over, get the confirmation again
    files = sorted(listdir(f"{input_path}/{call.message.chat.id}"))

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


@dp.callback_query_handler(text="add")
async def ask_position(call: types.CallbackQuery):
    """
    This handler will be called when user indicates that they want to
    add a file.
    Asks the user where they want to add the new file.
    """

    files_num = len(listdir(f"{input_path}/{call.message.chat.id}"))

    keyboard = types.InlineKeyboardMarkup()

    buttons = []

    for i in range(1, files_num + 2):
        buttons.append(
            types.InlineKeyboardButton(
                text=str(i),
                callback_data=f"loc_{i}",
            )
        )

    keyboard.add(*buttons)

    await call.message.edit_text(
        "<b><u>Choose where you want to add the new file</u></b>\n\n"
        + call.message.text[call.message.text.index("1.") :],
        reply_markup=keyboard,
    )

    await call.answer()


@dp.callback_query_handler(text_startswith="loc_")
async def prepare_for_addition(call: types.CallbackQuery, state: FSMContext):
    """
    This handler will be called when user indicates where they want to
    add the new file.
    """
    await MergingStates.waiting_for_specific_file.set()

    # location number is indicated right after the loc_ prefix (at index 4)
    location = int(call.data[4:])

    files = sorted(listdir(f"{input_path}/{call.message.chat.id}"))

    if location <= len(files):
        for file in files[location - 1 :]:
            file_num = int(file[:2]) + 1

            file_num = f"0{file_num}" if file_num < 10 else str(file_num)
            rename(
                f"{input_path}/{call.message.chat.id}/{file}",
                f"{input_path}/{call.message.chat.id}/{file_num}{file[2:]}",
            )

    # storing the desired position in the state
    await state.update_data(num=location)

    await call.message.edit_text(
        "<b>Alright, just send me the file and I'll add it there.</b>",
        reply_markup="",
    )

    await call.answer()


@dp.callback_query_handler(text="no_cancel")
async def just_cancel(call: types.CallbackQuery):
    """
    This handler will be called when user aborts merging
    from the inline keyboard.
    """
    logging.info("Cancelling merging")

    # delete the inline keyboard
    await call.message.delete_reply_markup()

    files = listdir(f"{input_path}/{call.message.chat.id}/")

    if files:
        for file in files:
            unlink(f"{input_path}/{call.message.chat.id}/{file}")
            logging.info(f"Deleted input PDF")

    await call.message.answer("Merging cancelled.")

    await call.answer()
