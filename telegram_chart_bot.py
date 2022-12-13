#!/usr/bin/env python

import logging
from typing import Optional
import telegram
import asyncio
from sys import stderr
from pathlib import Path

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


BOT: Optional[telegram.Bot] = None


def get_bot() -> telegram.Bot:
    global BOT
    if BOT is None:
        BOT = telegram.Bot("5871989633:AAH4z1-ho9yGz1x7RXCg9hQ6fitwj1bAYp8")
    return BOT


async def main():
    async with get_bot() as bot:
        await bot.send_message(text="Ao so er rebblancer!", chat_id=31088519)


async def send_latest_chart():
    async with get_bot() as bot:
        print("telegram: sending latest charts...", file=stderr)
        await bot.send_media_group(chat_id=31088519, media = [
            telegram.InputMediaPhoto(Path("latest_chart.jpg").open('rb')),
            telegram.InputMediaPhoto(Path("latest_value_chart.jpg").open('rb')),
            telegram.InputMediaPhoto(Path("latest_pie_chart.jpg").open('rb')),
        ])
        await bot.send_media_group(chat_id=31088519, media = [
            telegram.InputMediaDocument(Path("balance_log.csv").open('rb')),
            telegram.InputMediaDocument(Path("log.stderr").open('rb')),
        ])
    print("telegram: done.", file=stderr)


async def telegram_notify_action(action):
    async with get_bot() as bot:
        print("telegram: sending action notification...", file=stderr)
        action_description = "\n".join([f"{k}: {v}" for k, v in action.items()])
        await bot.send_message(text=action_description, chat_id=31088519),
    print("telegram: done.", file=stderr)
