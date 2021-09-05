from aiogram import types

async def set_default_commands(dp):
    await dp.bot.set_my_commands(
        [
            types.BotCommand("start", "about info"),
            types.BotCommand("done", "start merging files"),
            types.BotCommand("cancel", "cancel merging files"),
            types.BotCommand("help", "how to use the bot"),
        ]
    )