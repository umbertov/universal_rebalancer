#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
from typing import Optional
import telegram
import asyncio

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# from telegram import __version__ as TG_VER
#
# try:
#     from telegram import __version_info__
# except ImportError:
#     __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]
#
# if __version_info__ < (20, 0, 0, "alpha", 1):
#     raise RuntimeError(
#         f"This example is not compatible with your current PTB version {TG_VER}. To view the "
#         f"{TG_VER} version of this example, "
#         f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
#     )
# from telegram import ForceReply, Update
# from telegram.ext import (
#     Application,
#     CommandHandler,
#     ContextTypes,
#     MessageHandler,
#     filters,
# )
#
#
#
# # Define a few command handlers. These usually take the two arguments update and
# # context.
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Send a message when the command /start is issued."""
#     user = update.effective_user
#     import ipdb
#
#     ipdb.set_trace()
#     await update.message.reply_html(
#         rf"Hi {user.mention_html()}!",
#         reply_markup=ForceReply(selective=True),
#     )
#
#
# async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Send a message when the command /help is issued."""
#     await update.message.reply_text("Help!")
#
#
# async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Echo the user message."""
#     await update.message.reply_text(update.message.text)
#
#
# def main() -> None:
#     """Start the bot."""
#     # Create the Application and pass it your bot's token.
#     application = (
#         Application.builder()
#         .token("5871989633:AAH4z1-ho9yGz1x7RXCg9hQ6fitwj1bAYp8")
#         .build()
#     )
#
#     # on different commands - answer in Telegram
#     application.add_handler(CommandHandler("start", start))
#     application.add_handler(CommandHandler("help", help_command))
#
#     # on non command i.e message - echo the message on Telegram
#     application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
#
#     # Run the bot until the user presses Ctrl-C
#     application.run_polling()

BOT: Optional[telegram.Bot] = None


def get_bot() -> telegram.Bot:
    global BOT
    if BOT is None:
        BOT = telegram.Bot("5871989633:AAH4z1-ho9yGz1x7RXCg9hQ6fitwj1bAYp8")
    return BOT


async def main():
    bot = get_bot()
    async with bot:
        await bot.send_message(text="Ao so er rebblancer!", chat_id=31088519)


async def send_latest_chart():
    await asyncio.gather(
        get_bot().send_photo(photo="latest_chart.png", chat_id=31088519),
        get_bot().send_photo(photo="latest_value_chart.png", chat_id=31088519),
    )

async def telegram_notify_action(action):
    action_description = '\n'.join([
        f'{k}: {v}' for k, v in action.items()
    ])
    await get_bot().send_message(text=action_description, chat_id=31088519),

if __name__ == "__main__":
    asyncio.run(main())
