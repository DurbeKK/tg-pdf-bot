from aiogram import types

async def set_default_commands(dp):
    await dp.bot.set_my_commands(
        [
            types.BotCommand("start", "about info"),
            types.BotCommand("help", "how to use the bot"),
            types.BotCommand("merge", "merge PDF files"),
            types.BotCommand("compress", "compress PDF file"),
            types.BotCommand("encrypt", "encrypt PDF file"),
            types.BotCommand("decrypt", "decrypt PDF file"),
            types.BotCommand("cancel", "cancel current operation"),
        ]
    )